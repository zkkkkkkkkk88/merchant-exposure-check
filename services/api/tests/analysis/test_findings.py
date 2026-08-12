from uuid import uuid4

from app.analysis.findings import EvidenceRef, FindingContext, build_findings


def test_price_gap_requires_competitor_evidence_and_missing_target_fact() -> None:
    evidence = EvidenceRef(
        query_result_id=uuid4(),
        citation_id=uuid4(),
        confidence=0.92,
    )
    context = FindingContext(
        target_confirmed_fields={"address"},
        competitor_field_counts={"price": 3},
        evidence_by_field={"price": [evidence]},
    )

    findings = build_findings(context)

    assert len(findings) == 1
    assert findings[0].finding_type == "missing_price"
    assert findings[0].severity == "high"
    assert findings[0].certainty == "confirmed"
    assert findings[0].evidence == [evidence]


def test_confirmed_target_fact_suppresses_gap() -> None:
    context = FindingContext(
        target_confirmed_fields={"price"},
        competitor_field_counts={"price": 4},
        evidence_by_field={
            "price": [EvidenceRef(query_result_id=uuid4(), confidence=0.9)]
        },
    )

    assert build_findings(context) == []


def test_low_confidence_evidence_is_marked_uncertain() -> None:
    context = FindingContext(
        target_confirmed_fields=set(),
        competitor_field_counts={"opening_hours": 2},
        evidence_by_field={
            "opening_hours": [EvidenceRef(query_result_id=uuid4(), confidence=0.4)]
        },
    )

    finding = build_findings(context)[0]

    assert finding.certainty == "uncertain"
    assert finding.confidence == 0.4
    assert "可能" in finding.explanation
