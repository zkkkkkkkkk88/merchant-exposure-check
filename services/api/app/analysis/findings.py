from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_result_id: UUID
    citation_id: UUID | None = None
    confidence: float = Field(ge=0, le=1)


class FindingContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_confirmed_fields: set[str]
    competitor_field_counts: dict[str, int]
    evidence_by_field: dict[str, list[EvidenceRef]]


class GapFindingDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    finding_type: str
    field: str
    severity: Literal["high", "medium"]
    certainty: Literal["confirmed", "uncertain"]
    confidence: float
    explanation: str
    recommended_action: str
    evidence: list[EvidenceRef]


FIELD_RULES = {
    "address": (
        "missing_address",
        "地址信息",
        "补充并统一门店地址、商场楼层和交通方式。",
    ),
    "opening_hours": (
        "missing_opening_hours",
        "营业时间",
        "在可公开检索的商家页面补充并统一营业时间。",
    ),
    "price": (
        "missing_price",
        "价格信息",
        "补充人均区间、代表产品价格和价格更新时间。",
    ),
    "product_detail": (
        "missing_product_detail",
        "产品细节",
        "补充代表产品、实际特点、供应时间和可核验图片。",
    ),
    "occasion": (
        "missing_occasion_association",
        "消费场景",
        "用真实信息说明适合的消费场景、人数和预订条件。",
    ),
    "third_party_sources": (
        "missing_third_party_sources",
        "独立第三方信源",
        "争取真实顾客、本地媒体或垂直创作者形成独立公开证据。",
    ),
}


def build_findings(context: FindingContext) -> list[GapFindingDraft]:
    findings: list[GapFindingDraft] = []
    for field, competitor_count in sorted(context.competitor_field_counts.items()):
        evidence = context.evidence_by_field.get(field, [])
        if field in context.target_confirmed_fields or competitor_count <= 0 or not evidence:
            continue
        rule = FIELD_RULES.get(field)
        if rule is None:
            continue

        finding_type, label, action = rule
        confidence = round(sum(item.confidence for item in evidence) / len(evidence), 4)
        certainty = "confirmed" if confidence >= 0.65 else "uncertain"
        prefix = "现有证据显示" if certainty == "confirmed" else "现有低置信度证据可能表明"
        findings.append(
            GapFindingDraft(
                finding_type=finding_type,
                field=field,
                severity="high" if competitor_count >= 3 else "medium",
                certainty=certainty,
                confidence=confidence,
                explanation=(
                    f"{prefix}：竞争商家在{competitor_count}条结果中具备{label}，"
                    "目标商家尚无已确认的对应公开信息。"
                ),
                recommended_action=action,
                evidence=evidence,
            )
        )
    return findings
