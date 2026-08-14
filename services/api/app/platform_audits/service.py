from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.merchants.models import Merchant
from app.platform_audits.models import PlatformAuditResult, PlatformAuditRun


FIELD_LABELS = {
    "name": "名称",
    "address": "地址",
    "phone": "电话",
    "opening_hours": "营业时间",
    "products": "服务项目",
    "credentials": "医生与资质",
}


def _normalized(value):
    if isinstance(value, str):
        return "".join(value.casefold().split())
    if isinstance(value, list):
        return sorted(_normalized(item) for item in value)
    return value


def _same_field(key: str, baseline, observed) -> bool:
    baseline_normalized = _normalized(baseline)
    observed_normalized = _normalized(observed)
    if key == "address" and isinstance(baseline_normalized, str) and isinstance(observed_normalized, str):
        return (
            baseline_normalized in observed_normalized
            or observed_normalized in baseline_normalized
        )
    return baseline_normalized == observed_normalized


def classify_platform(
    baseline: dict, observed: dict, found: bool
) -> tuple[str, list[str]]:
    if not found:
        return "not_found", ["公开检索未找到可确认页面"]

    conflicts = [
        label
        for key, label in FIELD_LABELS.items()
        if baseline.get(key) not in (None, "", [])
        and observed.get(key) not in (None, "", [])
        and not _same_field(key, baseline[key], observed[key])
    ]
    discoveries = [
        f"发现可补录{label}：{observed[key]}"
        for key, label in FIELD_LABELS.items()
        if observed.get(key) not in (None, "", [])
        and baseline.get(key) in (None, "", [])
    ]
    if conflicts:
        return "conflict", [f"信息冲突：{label}" for label in conflicts] + discoveries

    missing = [
        label
        for key, label in FIELD_LABELS.items()
        if baseline.get(key) not in (None, "", [])
        and observed.get(key) in (None, "", [])
    ]
    if missing:
        return "incomplete", [f"信息不完整：{label}" for label in missing] + discoveries
    return "complete", discoveries


class PlatformAuditService:
    def __init__(self, session: Session):
        self.session = session

    def create_run(self, merchant_id: UUID) -> PlatformAuditRun:
        if self.session.get(Merchant, merchant_id) is None:
            raise LookupError("merchant not found")
        active = self.session.scalar(
            select(PlatformAuditRun)
            .where(
                PlatformAuditRun.merchant_id == merchant_id,
                PlatformAuditRun.status.in_(("queued", "running")),
            )
            .order_by(PlatformAuditRun.created_at.desc())
        )
        if active is not None:
            return active
        run = PlatformAuditRun(merchant_id=merchant_id)
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)
        return run

    def get_latest(self, merchant_id: UUID) -> PlatformAuditRun | None:
        return self.session.scalar(
            select(PlatformAuditRun)
            .where(PlatformAuditRun.merchant_id == merchant_id)
            .order_by(PlatformAuditRun.created_at.desc(), PlatformAuditRun.id.desc())
            .options(selectinload(PlatformAuditRun.platforms))
        )

    def record_platform(
        self,
        run_id: UUID,
        platform_key: str,
        platform_name: str,
        *,
        found: bool,
        fields: dict,
        evidence: list[dict],
    ) -> PlatformAuditResult:
        run = self.session.get(PlatformAuditRun, run_id)
        if run is None:
            raise LookupError("audit run not found")
        merchant = self.session.get(Merchant, run.merchant_id)
        baseline = {
            "name": merchant.name,
            "address": merchant.address,
            "opening_hours": merchant.opening_hours,
            "products": merchant.products,
        }
        status, issues = classify_platform(baseline, fields, found)
        result = PlatformAuditResult(
            run=run,
            platform_key=platform_key,
            platform_name=platform_name,
            status=status,
            found=found,
            fields=fields,
            issues=issues,
            evidence=evidence,
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result

    def record_failure(
        self,
        run_id: UUID,
        platform_key: str,
        platform_name: str,
        message: str,
    ) -> PlatformAuditResult:
        run = self.session.get(PlatformAuditRun, run_id)
        if run is None:
            raise LookupError("audit run not found")
        result = PlatformAuditResult(
            run=run,
            platform_key=platform_key,
            platform_name=platform_name,
            status="needs_review",
            found=False,
            fields={},
            issues=[f"本次检索未完成：{message}"],
            evidence=[],
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result
