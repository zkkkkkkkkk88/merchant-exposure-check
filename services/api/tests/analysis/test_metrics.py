from decimal import Decimal
from uuid import uuid4

from app.analysis.contracts import AnalyzedQueryResult, MetricMention
from app.analysis.metrics import calculate_metrics


def result(
    *,
    target_id,
    intent_type: str,
    mentioned: bool = False,
    recommended: bool = False,
    domains: set[str] | None = None,
    fact_keys: list[str] | None = None,
) -> AnalyzedQueryResult:
    return AnalyzedQueryResult(
        query_id=uuid4(),
        category="need",
        intent_type=intent_type,
        fact_keys=fact_keys or [],
        is_valid=True,
        is_recommended=recommended,
        mentions=(
            [MetricMention(brand_id=target_id, normalized_name="target")]
            if mentioned
            else []
        ),
        target_source_domains=domains or set(),
    )


def test_metrics_show_relevant_stage_before_recommendation() -> None:
    target_id = uuid4()
    results = [
        result(
            target_id=target_id,
            intent_type="verification",
            mentioned=True,
            domains={"example.com"},
            fact_keys=["service.baby_chair"],
        ),
        result(target_id=target_id, intent_type="recommendation"),
    ]

    snapshot = calculate_metrics(
        results,
        target_id,
        confirmed_profile_fields={
            "location.city",
            "category.precise",
            "service.baby_chair",
        },
        required_profile_fields={
            "location.city",
            "category.precise",
            "price.display",
            "service.baby_chair",
        },
    )

    assert snapshot.visibility_stage == "relevant"
    assert snapshot.profile_completeness == Decimal("0.7500")
    assert snapshot.public_verifiability == Decimal("0.3333")
    assert snapshot.high_intent_hit_rate == Decimal("0.0000")
    assert snapshot.readiness_score == Decimal("30.42")
    assert not hasattr(snapshot, "first_position_rate")


def test_recommended_stage_and_weights_are_reproducible() -> None:
    target_id = uuid4()
    results = [
        result(
            target_id=target_id,
            intent_type="verification",
            mentioned=True,
            domains={"a.example"},
            fact_keys=["location.city", "category.precise"],
        ),
        result(
            target_id=target_id,
            intent_type="recommendation",
            mentioned=True,
            recommended=True,
            domains={"b.example"},
        ),
        result(target_id=target_id, intent_type="recommendation"),
    ]

    snapshot = calculate_metrics(
        results,
        target_id,
        confirmed_profile_fields={"location.city", "category.precise"},
        required_profile_fields={"location.city", "category.precise"},
    )

    assert snapshot.visibility_stage == "recommended"
    assert snapshot.profile_completeness == Decimal("1.0000")
    assert snapshot.public_verifiability == Decimal("1.0000")
    assert snapshot.high_intent_hit_rate == Decimal("0.5000")
    assert snapshot.competitor_gap_closure == Decimal("0.0000")
    assert snapshot.readiness_score == Decimal("72.50")
    assert snapshot.mention_rate == Decimal("0.5000")
