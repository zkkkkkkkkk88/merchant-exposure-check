from collections import Counter, defaultdict
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.analysis.contracts import AnalyzedQueryResult, MetricSnapshot

RATE_PRECISION = Decimal("0.0001")


def rate(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal("0.0000")
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        RATE_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def calculate_metrics(
    results: Sequence[AnalyzedQueryResult],
    target_brand_id: UUID,
) -> MetricSnapshot:
    valid_results = [result for result in results if result.is_valid]
    ranked_results = [result for result in valid_results if result.has_explicit_ranking]
    target_mentions = [
        result
        for result in valid_results
        if any(mention.brand_id == target_brand_id for mention in result.mentions)
    ]
    target_first = sum(
        any(
            mention.brand_id == target_brand_id and mention.position == 1
            for mention in result.mentions
        )
        for result in ranked_results
    )

    category_totals: Counter[str] = Counter()
    category_mentions: Counter[str] = Counter()
    competitor_queries: dict[str, set[UUID]] = defaultdict(set)
    source_domains: set[str] = set()
    confirmed_fields: set[str] = set()

    for result in valid_results:
        category_totals[result.category] += 1
        if result in target_mentions:
            category_mentions[result.category] += 1
        source_domains.update(result.target_source_domains)
        confirmed_fields.update(result.confirmed_target_fields)
        for mention in result.mentions:
            if mention.brand_id != target_brand_id:
                competitor_queries[mention.normalized_name].add(result.query_id)

    return MetricSnapshot(
        total_query_count=len(results),
        valid_query_count=len(valid_results),
        mention_rate=rate(len(target_mentions), len(valid_results)),
        first_position_rate=rate(target_first, len(ranked_results)),
        task_valid_rate=rate(len(valid_results), len(results)),
        source_coverage_rate=rate(
            sum(bool(result.target_source_domains) for result in valid_results),
            len(valid_results),
        ),
        independent_source_count=len(source_domains),
        category_coverage={
            category: rate(category_mentions[category], total)
            for category, total in sorted(category_totals.items())
        },
        competitor_counts={
            name: len(query_ids)
            for name, query_ids in sorted(competitor_queries.items())
        },
        confirmed_target_fields=confirmed_fields,
    )
