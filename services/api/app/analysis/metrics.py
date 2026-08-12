from collections import Counter, defaultdict
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.analysis.contracts import AnalyzedQueryResult, CompetitorDetail, MetricSnapshot

RATE_PRECISION = Decimal("0.0001")
SCORE_PRECISION = Decimal("0.01")


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
    *,
    confirmed_profile_fields: AbstractSet[str] = frozenset(),
    required_profile_fields: AbstractSet[str] = frozenset(),
) -> MetricSnapshot:
    valid_results = [item for item in results if item.is_valid]
    recommendation_results = [
        item for item in valid_results if item.intent_type == "recommendation"
    ]
    target_mentions = [
        item
        for item in recommendation_results
        if any(mention.brand_id == target_brand_id for mention in item.mentions)
    ]
    verified_fields = {
        field_key
        for item in valid_results
        if item.intent_type == "verification"
        and item.target_source_domains
        and any(mention.brand_id == target_brand_id for mention in item.mentions)
        for field_key in item.fact_keys
    }

    category_totals: Counter[str] = Counter()
    category_mentions: Counter[str] = Counter()
    competitor_queries: dict[str, set[UUID]] = defaultdict(set)
    competitor_display_names: dict[str, str] = {}
    competitor_categories: dict[str, set[str]] = defaultdict(set)
    competitor_questions: dict[str, dict[UUID, str]] = defaultdict(dict)
    competitor_sources: dict[str, set[str]] = defaultdict(set)
    competitor_reasons: dict[str, list[str]] = defaultdict(list)
    source_domains: set[str] = set()
    confirmed_fields: set[str] = set(verified_fields)
    for item in valid_results:
        source_domains.update(item.target_source_domains)
        confirmed_fields.update(item.confirmed_target_fields)
        if item.intent_type != "recommendation":
            continue
        category_totals[item.category] += 1
        if item in target_mentions:
            category_mentions[item.category] += 1
        for mention in item.mentions:
            if mention.brand_id != target_brand_id:
                competitor_queries[mention.normalized_name].add(item.query_id)
                competitor_display_names.setdefault(
                    mention.normalized_name, mention.display_name
                )
                competitor_categories[mention.normalized_name].add(item.category)
                competitor_questions[mention.normalized_name][item.query_id] = item.query_text
                competitor_sources[mention.normalized_name].update(
                    mention.source_domains
                )
                if (
                    mention.recommendation_reason
                    and mention.recommendation_reason
                    not in competitor_reasons[mention.normalized_name]
                ):
                    competitor_reasons[mention.normalized_name].append(
                        mention.recommendation_reason
                    )

    profile_completeness = rate(
        len(set(confirmed_profile_fields) & set(required_profile_fields)),
        len(required_profile_fields),
    )
    public_verifiability = rate(
        len(verified_fields & set(confirmed_profile_fields)),
        len(confirmed_profile_fields),
    )
    high_intent_hit_rate = rate(len(target_mentions), len(recommendation_results))
    competitor_counts = {
        competitor_display_names[name]: len(query_ids)
        for name, query_ids in sorted(competitor_queries.items())
    }
    competitor_gap_closure = (
        rate(
            max(0, len(recommendation_results) - max(competitor_counts.values())),
            len(recommendation_results),
        )
        if competitor_counts
        else Decimal("0.0000")
    )

    if any(item.is_recommended for item in target_mentions):
        visibility_stage = "recommended"
    elif target_mentions:
        visibility_stage = "mentioned"
    elif verified_fields:
        visibility_stage = "relevant"
    else:
        visibility_stage = "unrecognized"

    readiness_score = (
        profile_completeness * Decimal(25)
        + public_verifiability * Decimal(35)
        + high_intent_hit_rate * Decimal(25)
        + competitor_gap_closure * Decimal(15)
    ).quantize(SCORE_PRECISION, rounding=ROUND_HALF_UP)

    return MetricSnapshot(
        total_query_count=len(results),
        valid_query_count=len(valid_results),
        mention_rate=high_intent_hit_rate,
        visibility_stage=visibility_stage,
        profile_completeness=profile_completeness,
        public_verifiability=public_verifiability,
        high_intent_hit_rate=high_intent_hit_rate,
        competitor_gap_closure=competitor_gap_closure,
        readiness_score=readiness_score,
        task_valid_rate=rate(len(valid_results), len(results)),
        source_coverage_rate=rate(
            sum(bool(item.target_source_domains) for item in valid_results),
            len(valid_results),
        ),
        independent_source_count=len(source_domains),
        category_coverage={
            category: rate(category_mentions[category], total)
            for category, total in sorted(category_totals.items())
        },
        category_mentions=dict(sorted(category_mentions.items() | {
            category: 0 for category in category_totals if category not in category_mentions
        }.items())),
        category_totals=dict(sorted(category_totals.items())),
        competitor_counts=competitor_counts,
        competitor_details=[
            CompetitorDetail(
                name=competitor_display_names[name],
                query_count=len(competitor_queries[name]),
                categories=sorted(competitor_categories[name]),
                questions=list(competitor_questions[name].values()),
                reasons=competitor_reasons[name],
                source_count=len(competitor_sources[name]),
            )
            for name in sorted(competitor_queries)
        ],
        coverage_gaps={
            category: [
                item.query_text
                for item in recommendation_results
                if item.category == category and item not in target_mentions
            ]
            for category in sorted(category_totals)
            if category_mentions[category] < category_totals[category]
        },
        confirmed_target_fields=confirmed_fields,
    )
