import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.merchants.models import Merchant
from app.mobile_checks.channel_maintenance import build_channel_maintenance
from app.mobile_checks.models import (
    MobileCheckResult,
    MobileCheckRound,
    MobileRoundSource,
    MobileValidationItem,
    MobileValidationSet,
    utc_now,
)
from app.mobile_checks.schemas import MobileRoundCreate
from app.mobile_checks.playbook import LEVEL_LABELS, _target_position, build_recommendation_playbook, target_position_in_answer
from app.queries.models import Query, QuerySet


class NoApprovedQueriesError(ValueError):
    pass


class MobileCheckService:
    def __init__(self, session: Session):
        self.session = session

    def _approved_queries(self, merchant_id: UUID) -> list[Query]:
        latest_query_set_id = self.session.scalar(
            select(QuerySet.id)
            .where(QuerySet.merchant_id == merchant_id)
            .order_by(QuerySet.version.desc(), QuerySet.created_at.desc(), QuerySet.id.desc())
            .limit(1)
        )
        if latest_query_set_id is None:
            return []
        return list(
            self.session.scalars(
                select(Query)
                .where(
                    Query.query_set_id == latest_query_set_id,
                    Query.review_status == "approved",
                    Query.is_enabled.is_(True),
                    Query.intent_type == "recommendation",
                )
                .order_by(Query.priority, Query.created_at, Query.id)
            )
        )

    @staticmethod
    def _sample(queries: list[Query]) -> list[Query]:
        selected: list[Query] = []
        seen_categories: set[str] = set()
        for query in queries:
            if query.category not in seen_categories:
                selected.append(query)
                seen_categories.add(query.category)
        for query in queries:
            if query not in selected:
                selected.append(query)
            if len(selected) == 3:
                break
        return selected[:3]

    def create_validation_set(self, merchant_id: UUID, query_ids: list[UUID] | None = None) -> MobileValidationSet:
        queries = self._approved_queries(merchant_id)
        if len(queries) < 3:
            raise NoApprovedQueriesError("latest query set needs three approved enabled recommendation queries")
        if query_ids is not None:
            if len(query_ids) != 3 or len(set(query_ids)) != 3:
                raise NoApprovedQueriesError("mobile validation requires exactly three distinct questions")
            eligible = {query.id: query for query in queries}
            if any(query_id not in eligible for query_id in query_ids):
                raise NoApprovedQueriesError("selected question is not an eligible recommendation")
            selected = [eligible[query_id] for query_id in query_ids]
        else:
            selected = self._sample(queries)
        validation_set = MobileValidationSet(merchant_id=merchant_id)
        validation_set.items = [
            MobileValidationItem(query_id=query.id, position=index)
            for index, query in enumerate(selected, start=1)
        ]
        self.session.add(validation_set)
        self.session.commit()
        return self.get_validation_set(validation_set.id, merchant_id)  # type: ignore[return-value]

    def create_round(self, merchant_id: UUID, payload: MobileRoundCreate) -> MobileCheckRound | None:
        validation_set = self.get_validation_set(payload.validation_set_id, merchant_id)
        if validation_set is None:
            return None
        valid_item_ids = {item.id for item in validation_set.items}
        if any(item.validation_item_id not in valid_item_ids for item in payload.results):
            return None
        if payload.inherited_source_round_id is not None:
            inherited = self.session.scalar(
                select(MobileCheckRound).where(
                    MobileCheckRound.id == payload.inherited_source_round_id,
                    MobileCheckRound.merchant_id == merchant_id,
                    MobileCheckRound.status == "confirmed",
                )
            )
            if inherited is None:
                return None
        record = MobileCheckRound(
            merchant_id=merchant_id,
            validation_set_id=validation_set.id,
            location_text=payload.location_text,
            web_search_enabled=payload.web_search_enabled,
            raw_qa_text=payload.raw_qa_text,
            inherited_source_round_id=payload.inherited_source_round_id,
        )
        merchant = self.session.get(Merchant, merchant_id)
        oral_scope = merchant is not None and "口腔" in merchant.industry
        answers = self._split_answer_blocks(payload.raw_qa_text, len(validation_set.items))
        item_positions = {item.id: item.position for item in validation_set.items}
        result_values = []
        for item in payload.results:
            values = item.model_dump()
            position = item_positions[item.validation_item_id]
            full_answer = answers[position - 1]
            if full_answer:
                values["answer_excerpt"] = full_answer
            if merchant is not None:
                target_position = target_position_in_answer(values["answer_excerpt"], merchant.name)
                if target_position is not None:
                    values["mention_level"] = "primary" if target_position == 1 else "supplementary"
            if oral_scope:
                values["competitors"] = [name for name in values["competitors"] if not self._is_public_oral_entity(name)]
            result_values.append(values)
        record.results = [MobileCheckResult(**values) for values in result_values]
        record.sources = [MobileRoundSource(**item.model_dump()) for item in payload.sources]
        self.session.add(record)
        self.session.commit()
        return record

    @staticmethod
    def _split_answer_blocks(raw_text: str, count: int) -> list[str]:
        markers = list(re.finditer(
            r"(?:^|\n)\s*(?:Q|问题)\s*([1-9]\d*)\s*[：:.、-]?\s*",
            raw_text,
            flags=re.IGNORECASE,
        ))
        if not markers:
            separated = [part.strip() for part in re.split(
                r"\n\s*(?:-{3,}|={3,}|【?回答\s*[1-9]\d*】?)\s*\n",
                raw_text,
                flags=re.IGNORECASE,
            ) if part.strip()]
            return [separated[index] if index < len(separated) else "" for index in range(count)]
        blocks = [""] * count
        for index, marker in enumerate(markers):
            position = int(marker.group(1)) - 1
            if 0 <= position < count:
                end = markers[index + 1].start() if index + 1 < len(markers) else len(raw_text)
                blocks[position] = raw_text[marker.end():end].strip()
        return blocks

    def get_round(self, round_id: UUID, merchant_id: UUID) -> MobileCheckRound | None:
        return self.session.scalar(
            select(MobileCheckRound).where(
                MobileCheckRound.id == round_id,
                MobileCheckRound.merchant_id == merchant_id,
            )
        )

    def confirm_round(self, round_id: UUID, merchant_id: UUID) -> MobileCheckRound | None:
        record = self.get_round(round_id, merchant_id)
        if record is None:
            return None
        record.status = "confirmed"
        record.confirmed_at = utc_now()
        self.session.commit()
        return record

    def get_validation_set(self, validation_set_id: UUID, merchant_id: UUID) -> MobileValidationSet | None:
        return self.session.scalar(
            select(MobileValidationSet)
            .where(MobileValidationSet.id == validation_set_id, MobileValidationSet.merchant_id == merchant_id)
            .options(selectinload(MobileValidationSet.items).selectinload(MobileValidationItem.query))
        )

    def list_validation_sets(self, merchant_id: UUID) -> list[MobileValidationSet]:
        return list(self.session.scalars(
            select(MobileValidationSet)
            .where(MobileValidationSet.merchant_id == merchant_id)
            .order_by(MobileValidationSet.created_at, MobileValidationSet.id)
            .options(selectinload(MobileValidationSet.items).selectinload(MobileValidationItem.query))
        ))

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0

    @staticmethod
    def _is_public_oral_entity(name: str) -> bool:
        return any(marker in name for marker in ("人民医院", "中医医院", "妇幼保健院", "卫生院", "公立医院"))

    def _latest_confirmed_round(self, merchant_id: UUID) -> MobileCheckRound | None:
        return self.session.scalar(
            select(MobileCheckRound)
            .where(MobileCheckRound.merchant_id == merchant_id, MobileCheckRound.status == "confirmed")
            .order_by(MobileCheckRound.created_at.desc(), MobileCheckRound.id.desc())
            .options(
                selectinload(MobileCheckRound.results)
                .selectinload(MobileCheckResult.validation_item)
                .selectinload(MobileValidationItem.query),
                selectinload(MobileCheckRound.sources),
            )
        )

    def _source_round(self, latest: MobileCheckRound) -> MobileCheckRound:
        if latest.inherited_source_round_id is None:
            return latest
        inherited = self.session.scalar(
            select(MobileCheckRound)
            .where(
                MobileCheckRound.id == latest.inherited_source_round_id,
                MobileCheckRound.merchant_id == latest.merchant_id,
            )
            .options(selectinload(MobileCheckRound.sources))
        )
        return inherited or latest

    def _previous_confirmed_round(self, latest: MobileCheckRound) -> MobileCheckRound | None:
        return self.session.scalar(
            select(MobileCheckRound)
            .where(
                MobileCheckRound.merchant_id == latest.merchant_id,
                MobileCheckRound.status == "confirmed",
                MobileCheckRound.id != latest.id,
                MobileCheckRound.created_at <= latest.created_at,
            )
            .order_by(MobileCheckRound.created_at.desc(), MobileCheckRound.id.desc())
            .options(
                selectinload(MobileCheckRound.results)
                .selectinload(MobileCheckResult.validation_item)
                .selectinload(MobileValidationItem.query)
            )
        )

    @staticmethod
    def _source_rows(merchant_name: str, sources: list[MobileRoundSource], result_competitors: set[str]) -> tuple[list[str], list[dict]]:
        confirmed = [source for source in sources if source.is_confirmed]
        if not confirmed:
            return [merchant_name], []
        source_competitors = {source.entity_name for source in confirmed if source.entity_name != merchant_name}
        competitors = sorted(
            source_competitors,
            key=lambda name: (-sum(source.entity_name == name for source in confirmed), name),
        )[:3]
        entities = [merchant_name, *competitors]
        labels = {
            "profile": "官网/机构介绍页",
            "registry": "工商或登记信息",
            "recruitment": "招聘页面",
            "douyin": "抖音公开内容",
            "local_media": "本地媒体或目录",
            "government": "政府或医院",
            "industry": "行业内容",
            "other": "其他公开来源",
        }
        rows: list[dict] = []
        for key, label in labels.items():
            cells: dict[str, dict] = {}
            for entity in entities:
                matches = [source for source in confirmed if source.source_type == key and source.entity_name == entity]
                cells[entity] = {
                    "status": "present" if matches else "missing",
                    "evidence": [
                        f"{source.title}：{'、'.join(source.facts)}" if source.facts else source.title
                        for source in matches[:2]
                    ],
                }
            rows.append({
                "key": key,
                "label": label,
                "cells": cells,
                "highlight": cells[merchant_name]["status"] == "missing" and any(
                    cells[name]["status"] == "present" for name in competitors
                ),
            })
        fact_groups = {
            "address": ("地址可验证性", ("地址", "位置")),
            "hours": ("电话与营业时间", ("电话", "营业时间")),
            "credentials": ("医生或资质信息", ("医生", "资质", "执业")),
            "services": ("诊疗项目", ("项目", "诊疗", "矫正", "种植", "儿牙")),
            "equipment": ("设备信息", ("设备", "CT", "口扫", "诊室")),
        }
        for key, (label, needles) in fact_groups.items():
            cells: dict[str, dict] = {}
            for entity in entities:
                matches = [source for source in confirmed if source.entity_name == entity and any(any(needle.casefold() in fact.casefold() for needle in needles) for fact in source.facts)]
                cells[entity] = {"status": "present" if matches else "missing", "evidence": [f"{source.title}：{'、'.join(source.facts)}" for source in matches[:2]]}
            rows.append({"key": key, "label": label, "cells": cells, "highlight": cells[merchant_name]["status"] == "missing" and any(cells[name]["status"] == "present" for name in competitors)})
        informative = [row for row in rows if any(cell["status"] == "present" for cell in row["cells"].values())]
        informative.sort(key=lambda row: (not row["highlight"], row["key"]))
        return entities, informative[:5]

    def get_workspace(self, merchant_id: UUID) -> dict:
        merchant = self.session.get(Merchant, merchant_id)
        if merchant is None:
            raise LookupError("merchant not found")
        latest = self._latest_confirmed_round(merchant_id)
        if latest is None:
            return {
                "latestRoundId": None,
                "sourceRoundId": None,
                "metrics": None,
                "entities": [merchant.name],
                "sourceGaps": [],
                "latestRoundAnswers": [],
                "recommendationPlaybook": None,
                "channelMaintenance": {
                    "citedChannels": [],
                    "candidateChannels": [],
                },
            }
        confirmed_results = [result for result in latest.results if result.is_confirmed]
        mentioned = [result for result in confirmed_results if result.mention_level != "none"]
        primary = [result for result in confirmed_results if result.mention_level == "primary"]
        tested_categories = {result.validation_item.query.category for result in confirmed_results}
        mentioned_categories = {result.validation_item.query.category for result in mentioned}
        accurate = [result for result in mentioned if result.information_accurate is True]
        source_round = self._source_round(latest)
        confirmed_sources = [source for source in source_round.sources if source.is_confirmed]
        all_source_types = {source.source_type for source in confirmed_sources}
        target_source_types = {source.source_type for source in confirmed_sources if source.entity_name == merchant.name}
        oral_scope = "口腔" in merchant.industry
        result_competitors = {
            name for result in confirmed_results for name in result.competitors
            if name != merchant.name and (not oral_scope or not self._is_public_oral_entity(name))
        }
        peer_sources = [
            source for source in source_round.sources
            if not oral_scope or source.entity_name == merchant.name or not self._is_public_oral_entity(source.entity_name)
        ]
        entities, rows = self._source_rows(merchant.name, peer_sources, result_competitors)
        playbook = build_recommendation_playbook(
            merchant,
            latest,
            self._previous_confirmed_round(latest),
            [source for source in confirmed_sources if source in peer_sources],
        )
        channel_maintenance = build_channel_maintenance(
            confirmed_sources,
            playbook.get("actions", []),
        )
        latest_round_answers = [{
            "position": result.validation_item.position,
            "question": result.validation_item.query.text,
            "answer": result.answer_excerpt,
            "mentionLevel": result.mention_level,
            "mentionLabel": LEVEL_LABELS[result.mention_level],
            "targetPosition": _target_position(result, merchant.name),
        } for result in sorted(confirmed_results, key=lambda item: item.validation_item.position)]
        return {
            "latestRoundId": str(latest.id),
            "sourceRoundId": str(source_round.id),
            "metrics": {
                "confirmedCount": len(confirmed_results),
                "mentionCount": len(mentioned),
                "primaryCount": len(primary),
                "categoryCoveredCount": len(mentioned_categories),
                "categoryTotalCount": len(tested_categories),
                "informationAccurateCount": len(accurate),
                "informationEvaluatedCount": len(mentioned),
                "mentionRate": self._rate(len(mentioned), len(confirmed_results)),
                "primaryRate": self._rate(len(primary), len(confirmed_results)),
                "categoryCoverageRate": self._rate(len(mentioned_categories), len(tested_categories)),
                "informationAccuracyRate": self._rate(len(accurate), len(mentioned)),
                "sourceCoverageRate": self._rate(len(target_source_types), len(all_source_types)),
            },
            "entities": entities,
            "sourceGaps": rows,
            "latestRoundAnswers": latest_round_answers,
            "recommendationPlaybook": playbook,
            "channelMaintenance": channel_maintenance,
        }
