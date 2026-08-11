from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.contracts import AnalyzedQueryResult, MetricMention
from app.analysis.extractor import extract_target_mention, validate_extraction
from app.analysis.models import BrandMention, ResultAnalysis
from app.analysis.normalization import normalize_brand_name
from app.merchants.models import Merchant
from app.queries.models import Query
from app.scans.models import QueryResult


class AnalysisService:
    @staticmethod
    def ensure_result(
        session: Session, result: QueryResult, merchant: Merchant
    ) -> ResultAnalysis:
        existing = session.scalar(
            select(ResultAnalysis).where(ResultAnalysis.query_result_id == result.id)
        )
        if existing is not None:
            return existing

        target_names = [merchant.name]
        if merchant.branch_name:
            target_names.append(f"{merchant.name} {merchant.branch_name}")
        payload = extract_target_mention(result.raw_text or "", target_names)
        validate_extraction(payload, [citation.url for citation in result.citations])
        analysis = ResultAnalysis(
            query_result_id=result.id,
            is_valid=result.status == "success" and payload.is_valid,
            has_explicit_ranking=payload.has_explicit_ranking,
            confidence=payload.confidence,
        )
        for mention in payload.mentions:
            analysis.mentions.append(
                BrandMention(
                    brand_id=merchant.id,
                    raw_name=mention.raw_name,
                    normalized_name=normalize_brand_name(merchant.name),
                    is_target=True,
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
        has_target = any(mention.is_target for mention in analysis.mentions)
        return AnalyzedQueryResult(
            query_id=result.query_id,
            category=query.category,
            is_valid=analysis.is_valid,
            has_explicit_ranking=analysis.has_explicit_ranking,
            mentions=[
                MetricMention(
                    brand_id=mention.brand_id,
                    normalized_name=mention.normalized_name,
                    position=mention.position,
                )
                for mention in analysis.mentions
            ],
            target_source_domains=(
                {citation.domain for citation in result.citations} if has_target else set()
            ),
            confirmed_target_fields={
                fact.fact_type for fact in analysis.facts if fact.is_target
            },
        )
