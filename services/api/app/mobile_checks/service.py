from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.merchants.models import Merchant
from app.mobile_checks.models import (
    MobileCheckResult,
    MobileCheckRound,
    MobileRoundSource,
    MobileValidationItem,
    MobileValidationSet,
    utc_now,
)
from app.mobile_checks.schemas import MobileRoundCreate
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

    def create_validation_set(self, merchant_id: UUID) -> MobileValidationSet:
        queries = self._approved_queries(merchant_id)
        if len(queries) < 3:
            raise NoApprovedQueriesError("latest query set needs three approved enabled recommendation queries")
        validation_set = MobileValidationSet(merchant_id=merchant_id)
        validation_set.items = [
            MobileValidationItem(query_id=query.id, position=index)
            for index, query in enumerate(self._sample(queries), start=1)
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
        record.results = [MobileCheckResult(**item.model_dump()) for item in payload.results]
        record.sources = [MobileRoundSource(**item.model_dump()) for item in payload.sources]
        self.session.add(record)
        self.session.commit()
        return record

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
            return {"latestRoundId": None, "sourceRoundId": None, "metrics": None, "entities": [merchant.name], "sourceGaps": []}
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
        result_competitors = {name for result in confirmed_results for name in result.competitors if name != merchant.name}
        entities, rows = self._source_rows(merchant.name, source_round.sources, result_competitors)
        return {
            "latestRoundId": str(latest.id),
            "sourceRoundId": str(source_round.id),
            "metrics": {
                "confirmedCount": len(confirmed_results),
                "mentionRate": self._rate(len(mentioned), len(confirmed_results)),
                "primaryRate": self._rate(len(primary), len(confirmed_results)),
                "categoryCoverageRate": self._rate(len(mentioned_categories), len(tested_categories)),
                "informationAccuracyRate": self._rate(len(accurate), len(mentioned)),
                "sourceCoverageRate": self._rate(len(target_source_types), len(all_source_types)),
            },
            "entities": entities,
            "sourceGaps": rows,
        }
