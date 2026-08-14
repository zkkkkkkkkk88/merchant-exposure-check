from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.merchants.models import Merchant, MerchantProfileFact
from app.platform_audits.models import PlatformAuditResult, PlatformAuditRun


FIELD_LABELS = {
    "name": "名称",
    "address": "地址",
    "phone": "电话",
    "opening_hours": "营业时间",
    "products": "服务项目",
    "credentials": "医生与资质",
}

PROFILE_FIELD_KEYS = {
    "name": "identity.official_name",
    "address": "location.address",
    "phone": "contact.phone",
    "opening_hours": "hours.display",
    "products": "product.list",
    "credentials": "credential.list",
}


class PlatformAuditResultNotFound(LookupError):
    pass


class PlatformAuditAdoptionConflict(RuntimeError):
    pass


class PlatformAuditAdoptionInvalid(ValueError):
    pass


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


def _merchant_baseline(merchant: Merchant) -> dict:
    baseline = {
        "name": merchant.name,
        "address": merchant.address,
        "opening_hours": merchant.opening_hours,
        "products": merchant.products,
    }
    profile_values = {
        fact.field_key: fact.value
        for fact in merchant.profile_facts
        if fact.confirmation_status == "confirmed"
    }
    for platform_key, profile_key in PROFILE_FIELD_KEYS.items():
        if profile_key in profile_values:
            baseline[platform_key] = profile_values[profile_key]
    return baseline


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

    def adopt_field(
        self, merchant_id: UUID, result_id: UUID, field_key: str
    ) -> PlatformAuditResult:
        result = self.session.get(PlatformAuditResult, result_id)
        if result is None or result.run.merchant_id != merchant_id:
            raise PlatformAuditResultNotFound(str(result_id))
        if field_key not in PROFILE_FIELD_KEYS:
            raise PlatformAuditAdoptionInvalid("不支持采用这个字段")
        if result.run.status not in {"completed", "partial"}:
            raise PlatformAuditAdoptionInvalid("平台查缺任务尚未完成")
        if result.status not in {"complete", "incomplete"} or not result.found:
            raise PlatformAuditAdoptionConflict("当前结果需要先人工核实")
        value = result.fields.get(field_key)
        if value in (None, "", []):
            raise PlatformAuditAdoptionInvalid("平台结果没有这个字段")
        source_urls = [
            str(item["url"])
            for item in result.evidence
            if isinstance(item, dict) and item.get("url")
        ]
        if not source_urls:
            raise PlatformAuditAdoptionInvalid("缺少可核验的公开来源")

        merchant = self.session.get(Merchant, merchant_id)
        if merchant is None:
            raise PlatformAuditResultNotFound(str(merchant_id))
        profile_key = PROFILE_FIELD_KEYS[field_key]
        fact = self.session.scalar(
            select(MerchantProfileFact).where(
                MerchantProfileFact.merchant_id == merchant_id,
                MerchantProfileFact.field_key == profile_key,
            )
        )
        if fact is None:
            fact = MerchantProfileFact(field_key=profile_key)
            merchant.profile_facts.append(fact)
        fact.value = value
        fact.confirmation_status = "confirmed"
        fact.confidence = 1.0
        fact.source_urls = list(dict.fromkeys(source_urls))

        baseline = _merchant_baseline(merchant)
        baseline[field_key] = value
        result.baseline_fields = baseline
        result.status, result.issues = classify_platform(baseline, result.fields, result.found)
        self.session.commit()
        self.session.refresh(result)
        return result

    def record_platform(
        self,
        run_id: UUID,
        platform_key: str,
        platform_name: str,
        *,
        found: bool,
        fields: dict,
        evidence: list[dict],
        search_query: str | None = None,
    ) -> PlatformAuditResult:
        run = self.session.get(PlatformAuditRun, run_id)
        if run is None:
            raise LookupError("audit run not found")
        merchant = self.session.get(Merchant, run.merchant_id)
        baseline = _merchant_baseline(merchant)
        status, issues = classify_platform(baseline, fields, found)
        result = PlatformAuditResult(
            run=run,
            platform_key=platform_key,
            platform_name=platform_name,
            status=status,
            found=found,
            search_query=search_query,
            baseline_fields=baseline,
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
        search_query: str | None = None,
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
            search_query=search_query,
            baseline_fields={},
            fields={},
            issues=[f"本次检索未完成：{message}"],
            evidence=[],
        )
        self.session.add(result)
        self.session.commit()
        self.session.refresh(result)
        return result
