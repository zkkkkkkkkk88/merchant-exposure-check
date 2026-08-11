from decimal import Decimal
from uuid import uuid4

from app.analysis.contracts import AnalyzedQueryResult, MetricMention
from app.analysis.metrics import calculate_metrics


def test_metrics_use_valid_results_and_explicit_ranking_denominators() -> None:
    target_id = uuid4()
    competitor_id = uuid4()
    results = [
        AnalyzedQueryResult(
            query_id=uuid4(),
            category="geo",
            is_valid=True,
            has_explicit_ranking=True,
            mentions=[MetricMention(brand_id=target_id, normalized_name="target", position=1)],
            target_source_domains={"a.example", "b.example"},
        ),
        AnalyzedQueryResult(
            query_id=uuid4(),
            category="geo",
            is_valid=True,
            has_explicit_ranking=True,
            mentions=[MetricMention(brand_id=competitor_id, normalized_name="competitor", position=1)],
        ),
        AnalyzedQueryResult(
            query_id=uuid4(),
            category="product",
            is_valid=True,
            has_explicit_ranking=True,
            mentions=[MetricMention(brand_id=competitor_id, normalized_name="competitor", position=2)],
        ),
        AnalyzedQueryResult(
            query_id=uuid4(),
            category="product",
            is_valid=True,
            has_explicit_ranking=True,
            mentions=[],
        ),
        AnalyzedQueryResult(
            query_id=uuid4(),
            category="occasion",
            is_valid=True,
            has_explicit_ranking=False,
            mentions=[MetricMention(brand_id=target_id, normalized_name="target")],
            target_source_domains={"c.example"},
        ),
        AnalyzedQueryResult(
            query_id=uuid4(),
            category="occasion",
            is_valid=False,
            has_explicit_ranking=False,
            mentions=[],
        ),
    ]

    snapshot = calculate_metrics(results, target_id)

    assert snapshot.valid_query_count == 5
    assert snapshot.mention_rate == Decimal("0.4000")
    assert snapshot.first_position_rate == Decimal("0.2500")
    assert snapshot.task_valid_rate == Decimal("0.8333")
    assert snapshot.independent_source_count == 3
    assert snapshot.source_coverage_rate == Decimal("0.4000")
    assert snapshot.competitor_counts == {"competitor": 2}
