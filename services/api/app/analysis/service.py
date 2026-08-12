from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.contracts import AnalyzedQueryResult, MetricMention
from app.analysis.extractor import (
    extract_ranked_mentions,
    extract_target_mention,
    validate_extraction,
)
from app.analysis.models import BrandMention, ResultAnalysis
from app.analysis.normalization import normalize_brand_name
from app.merchants.models import Merchant
from app.queries.models import Query
from app.scans.models import QueryResult


class AnalysisService:
    extraction_version = "heuristic-v3"

    @staticmethod
    def _matching_citation_domains(name: str, result: QueryResult) -> set[str]:
        normalized_name = normalize_brand_name(name)
        if len(normalized_name) < 3:
            return set()
        return {
            citation.domain
            for citation in result.citations
            if normalized_name
            in normalize_brand_name(
                " ".join(filter(None, [citation.title, citation.snippet]))
            )
        }

    @staticmethod
    def ensure_result(
        session: Session, result: QueryResult, merchant: Merchant
    ) -> ResultAnalysis:
        existing = session.scalar(
            select(ResultAnalysis).where(ResultAnalysis.query_result_id == result.id)
        )
        if existing is not None and existing.extraction_version == AnalysisService.extraction_version:
            return existing

        target_names = [merchant.name]
        if merchant.branch_name:
            target_names.append(f"{merchant.name} {merchant.branch_name}")
        raw_text = result.raw_text or ""
        target_payload = extract_target_mention(raw_text, target_names)
        validate_extraction(target_payload, [citation.url for citation in result.citations])
        ranked_mentions = extract_ranked_mentions(raw_text)
        all_mentions = [*ranked_mentions, *target_payload.mentions]
        target_normalized = {
            normalize_brand_name(name) for name in target_names if name.strip()
        }

        analysis = existing or ResultAnalysis(query_result_id=result.id)
        analysis.is_valid = result.status == "success" and target_payload.is_valid
        analysis.has_explicit_ranking = bool(ranked_mentions) or target_payload.has_explicit_ranking
        analysis.is_recommended = target_payload.is_recommended
        analysis.confidence = target_payload.confidence
        analysis.extraction_version = AnalysisService.extraction_version
        analysis.mentions.clear()
        analysis.facts.clear()

        seen: set[tuple[str, bool]] = set()
        for mention in all_mentions:
            normalized = normalize_brand_name(mention.raw_name)
            is_target = any(
                alias == normalized or alias in normalized or normalized in alias
                for alias in target_normalized
            )
            key = (normalized, is_target)
            if not normalized or key in seen:
                continue
            seen.add(key)
            analysis.mentions.append(
                BrandMention(
                    brand_id=(
                        merchant.id
                        if is_target
                        else uuid5(NAMESPACE_URL, f"merchant-brand:{normalized}")
                    ),
                    raw_name=mention.raw_name,
                    normalized_name=(normalize_brand_name(merchant.name) if is_target else normalized),
                    is_target=is_target,
                    position=mention.position,
                    recommendation_reason=mention.recommendation_reason,
                    confidence=mention.confidence,
                )
            )
        session.add(analysis)
        session.flush()
        return analysis

    @staticmethod
    def to_metric_result(
        session: Session, result: QueryResult, analysis: ResultAnalysis
    ) -> AnalyzedQueryResult:
        query = session.get(Query, result.query_id)
        if query is None:
            raise ValueError("Query not found")
        metric_mentions = [
            MetricMention(
                brand_id=mention.brand_id,
                normalized_name=mention.normalized_name,
                display_name=mention.raw_name,
                position=mention.position,
                recommendation_reason=mention.recommendation_reason,
                source_domains=AnalysisService._matching_citation_domains(
                    mention.raw_name, result
                ),
            )
            for mention in analysis.mentions
        ]
        target_ids = {
            mention.brand_id for mention in analysis.mentions if mention.is_target
        }
        target_source_domains = {
            domain
            for mention in metric_mentions
            if mention.brand_id in target_ids
            for domain in mention.source_domains
        }
        return AnalyzedQueryResult(
            query_id=result.query_id,
            query_text=query.text,
            category=query.category,
            intent_type=query.intent_type,
            fact_keys=query.fact_keys,
            is_valid=analysis.is_valid,
            is_recommended=analysis.is_recommended,
            mentions=metric_mentions,
            target_source_domains=target_source_domains,
            confirmed_target_fields={
                fact.fact_type for fact in analysis.facts if fact.is_target
            },
        )
