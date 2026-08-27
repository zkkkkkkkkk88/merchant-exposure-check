from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.access import AdminAccessDep
from app.db.session import get_session
from app.merchants.models import Merchant, MerchantProfileFact
from app.mobile_checks.models import MobileCheckRound
from app.mobile_checks.playbook import rounds_are_comparable
from app.platform_audits.models import PlatformAuditRun
from app.queries.models import Query, QuerySet
from app.reports.schemas import (
    DashboardRead,
    HistoryRead,
    JourneyProgressRead,
    ManualCheckCreate,
    ManualCheckRead,
    ReportRead,
)
from app.reports.service import ReportService
from app.scans.models import ScanRun
from app.scans.models import Citation, QueryResult

router = APIRouter(tags=["reports"])
SessionDep = Annotated[Session, Depends(get_session)]

_CATEGORY_ACTIONS = {
    "geo": "核对并增强商圈与门店位置信息的公开可检索性",
    "category": "核对并统一精准品类信息的公开表述",
    "product": "核对并补强招牌产品信息的公开可检索性",
    "price": "核对并增强价格区间与套餐信息的公开可检索性",
    "occasion": "核对并补充真实消费场景信息",
    "need": "核对并补充服务设施与交通信息",
}
_CATEGORY_LABELS = {
    "geo": "地域商圈",
    "category": "精准品类",
    "product": "招牌产品",
    "price": "价格",
    "occasion": "消费场景",
    "need": "服务需求",
}
_CATEGORY_DESCRIPTIONS = {
    "geo": "请先核对公开页面中的门店地址、商圈和交通关联。",
    "category": "请先核对公开页面中的品类表述和城市关联。",
    "product": "请先核对公开页面中的招牌产品名称和门店关联。",
    "price": "请先核对公开页面中的价格区间、套餐内容和更新时间。",
    "occasion": "请先核对公开页面中是否有真实、可验证的消费场景信息。",
    "need": "请先核对公开页面中的服务设施和交通信息。",
}

_ACTION_PLANS = {
    "geo": {
        "steps": ["核对门店标准地址、商圈和附近地标", "在各公开页面统一门店名称与地址", "补充公交、停车或步行到店说明"],
        "channels": ["官网", "地图平台", "团购平台门店页"],
        "materials": ["标准地址", "门店定位", "交通与停车信息", "门头照片"],
        "example": "门店位于【商圈/地标】，地址为【标准地址】，可通过【交通方式】到达。",
        "completionCriteria": "至少两个可公开检索的页面使用一致的门店名称、地址和商圈表述。",
    },
    "category": {
        "steps": ["确认门店最精准且合规的经营品类", "统一官网、地图和平台门店页的品类名称", "在门店简介首段写明城市、品类和核心服务"],
        "channels": ["官网", "地图平台", "团购平台门店页"],
        "materials": ["营业执照或执业许可中的规范名称", "核心服务项目", "门店所在城市与区域"],
        "example": "【商家名】是位于【城市/区域】的【精准品类】，主要提供【已核实服务】。",
        "completionCriteria": "至少两个公开页面采用同一精准品类，并能同时检索到商家名、城市和品类。",
    },
    "product": {
        "steps": ["整理真实在售或在做的核心项目", "为每个项目补充适用对象与关键特点", "在公开页面建立清晰的项目列表"],
        "channels": ["官网", "团购平台门店页", "公众号"],
        "materials": ["项目名称", "适用对象", "项目说明", "真实图片"],
        "example": "目前提供【项目名称】，适用于【已核实对象】，具体以到店评估和公开说明为准。",
        "completionCriteria": "核心项目在至少两个公开页面可检索，名称与说明保持一致。",
    },
    "price": {
        "steps": ["核对当前有效的价格区间", "说明价格对应的项目或套餐内容", "标注更新时间和适用条件"],
        "channels": ["官网", "团购平台门店页", "公众号"],
        "materials": ["价目表", "套餐内容", "适用条件", "更新时间"],
        "example": "【项目】公开价格区间为【区间】，包含【内容】，更新于【日期】，实际以门店确认为准。",
        "completionCriteria": "价格、项目内容和更新时间在公开页面成套出现，且与当前门店信息一致。",
    },
    "occasion": {
        "steps": ["筛选与真实服务相符的消费或就诊场景", "为场景补充设施与服务依据", "发布带有真实图片的场景说明"],
        "channels": ["官网", "团购平台门店页", "公众号"],
        "materials": ["真实场景照片", "服务流程", "适用人群", "设施信息"],
        "example": "门店可满足【真实场景】，现场提供【已核实设施/服务】，预约方式为【方式】。",
        "completionCriteria": "每个场景都有可核验的设施或服务依据，不使用空泛宣传词。",
    },
    "need": {
        "steps": ["核对用户关心的设施和服务是否真实提供", "补充预约、停车、无障碍等细节", "在主要门店页面设置一致的服务标签"],
        "channels": ["官网", "地图平台", "团购平台门店页"],
        "materials": ["设施清单", "服务规则", "预约方式", "现场照片"],
        "example": "门店提供【已核实服务/设施】，使用条件为【条件】，可通过【方式】提前确认。",
        "completionCriteria": "服务信息在至少两个公开页面可查，并写明使用条件或确认方式。",
    },
}


def _coverage_findings(metrics) -> list[dict]:
    return [
        {
            "title": _CATEGORY_ACTIONS[category],
            "description": (
                f"本次{len(questions)}道{_CATEGORY_LABELS[category]}问题中均未识别到目标商家；"
                f"{_CATEGORY_DESCRIPTIONS[category]}"
            ),
            "priority": "high" if len(questions) >= 2 else "medium",
            "certainty": "confirmed",
            "evidenceCount": len(questions),
            "questions": questions,
        }
        for category, questions in metrics.coverage_gaps.items()
    ]


def _action_plan(category: str, merchant: Merchant) -> dict[str, object]:
    plan = dict(_ACTION_PLANS[category])
    context = merchant.local_context
    if category != "geo" or context is None or context.status != "completed":
        return plan
    region = context.county or context.city or context.province
    address = context.normalized_address or merchant.address
    steps = [f"核对{region or '所在地'}与门店标准地址"]
    if context.landmarks:
        steps.append(f"核对有来源支持的附近地标：{'、'.join(context.landmarks)}")
    if context.transport_options:
        steps.append(f"补充已核验的到店方式：{'、'.join(context.transport_options)}")
    steps.append("在公开页面统一门店名称、县级地域和标准地址")
    plan["steps"] = steps
    plan["materials"] = [item for item in [region, address, *context.landmarks, *context.transport_options, "门头照片"] if item]
    plan["example"] = f"【商家名】位于【{region or '县级地域'}】的【{address or '标准地址'}】，附近可核验地标与到店方式以公开来源为准。"
    plan["completionCriteria"] = f"至少两个公开页面使用一致的商家名、{region or '县级地域'}和标准地址，不填写未经来源确认的设施或片区。"
    return plan


@router.get(
    "/merchants/{merchant_id}/journey-progress",
    response_model=JourneyProgressRead,
)
def get_journey_progress(
    merchant_id: UUID,
    session: SessionDep,
) -> JourneyProgressRead:
    if session.get(Merchant, merchant_id) is None:
        raise HTTPException(status_code=404, detail="Merchant not found")

    confirmed_profile_count = session.scalar(
        select(func.count(MerchantProfileFact.id)).where(
            MerchantProfileFact.merchant_id == merchant_id,
            MerchantProfileFact.confirmation_status == "confirmed",
        )
    ) or 0
    latest_query_set = session.scalar(
        select(QuerySet)
        .where(
            QuerySet.merchant_id == merchant_id,
            QuerySet.is_archived.is_(False),
        )
        .order_by(QuerySet.version.desc(), QuerySet.created_at.desc())
        .limit(1)
    )
    approved_query_count = 0
    if latest_query_set is not None:
        approved_query_count = sum(
            1
            for query in latest_query_set.queries
            if query.review_status == "approved"
            and query.is_enabled
            and query.intent_type == "recommendation"
        )

    latest_audit_status = session.scalar(
        select(PlatformAuditRun.status)
        .where(PlatformAuditRun.merchant_id == merchant_id)
        .order_by(PlatformAuditRun.created_at.desc(), PlatformAuditRun.id.desc())
        .limit(1)
    )
    confirmed_rounds = list(
        session.scalars(
            select(MobileCheckRound)
            .where(
                MobileCheckRound.merchant_id == merchant_id,
                MobileCheckRound.status == "confirmed",
            )
            .order_by(MobileCheckRound.created_at, MobileCheckRound.id)
        )
    )

    profile_done = confirmed_profile_count > 0
    mobile_done = bool(confirmed_rounds)
    queries_done = approved_query_count >= 3 or mobile_done
    audit_done = latest_audit_status in {"completed", "partial"}
    retest_done = len(confirmed_rounds) >= 2 and rounds_are_comparable(
        confirmed_rounds[-1], confirmed_rounds[-2]
    )

    def dependent_status(done: bool, ready: bool) -> str:
        if done:
            return "completed"
        return "ready" if ready else "pending"

    merchant_query = f"?merchant={merchant_id}"
    steps = [
        {
            "key": "profile",
            "label": "商家画像",
            "status": "completed" if profile_done else "pending",
            "href": f"/merchants/{merchant_id}",
        },
        {
            "key": "queries",
            "label": "问题策略",
            "status": "completed" if queries_done else "pending",
            "href": f"/queries{merchant_query}",
        },
        {
            "key": "audit",
            "label": "平台查缺",
            "status": dependent_status(audit_done, queries_done),
            "href": f"/platform-audits{merchant_query}",
        },
        {
            "key": "mobile",
            "label": "手机实测",
            "status": dependent_status(mobile_done, queries_done),
            "href": f"/mobile-checks{merchant_query}",
        },
        {
            "key": "action",
            "label": "执行优化",
            "status": "ready" if mobile_done else "pending",
            "href": f"/mobile-checks{merchant_query}#improvement-playbook",
        },
        {
            "key": "retest",
            "label": "同题复测",
            "status": dependent_status(retest_done, mobile_done),
            "href": f"/mobile-checks{merchant_query}#retest-comparison",
        },
    ]
    current_step = next(
        (step["key"] for step in steps if step["status"] != "completed"),
        "report",
    )
    return JourneyProgressRead(
        merchant_id=merchant_id,
        completed_count=sum(step["status"] == "completed" for step in steps),
        current_step=current_step,
        steps=steps,
    )


@router.get("/merchants/{merchant_id}/dashboard", response_model=DashboardRead)
def get_dashboard(merchant_id: UUID, session: SessionDep) -> DashboardRead:
    merchant = session.get(Merchant, merchant_id)
    run = session.scalar(
        select(ScanRun)
        .where(ScanRun.merchant_id == merchant_id)
        .order_by(ScanRun.created_at.desc())
        .limit(1)
    )
    if merchant is None or run is None:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    metrics = ReportService.metrics(session, merchant_id, run.id)
    source_channels_by_category: dict[str, list[dict[str, object]]] = {}
    for category, domain, count in session.execute(
        select(Query.category, Citation.domain, func.count(Citation.id))
        .join(QueryResult, QueryResult.query_id == Query.id)
        .join(Citation, Citation.query_result_id == QueryResult.id)
        .where(QueryResult.scan_run_id == run.id)
        .group_by(Query.category, Citation.domain)
        .order_by(Query.category, func.count(Citation.id).desc(), Citation.domain)
    ).all():
        source_channels_by_category.setdefault(category, []).append(
            {"domain": domain, "citationCount": count, "access": "reference", "label": "仅作参照"}
        )
    comparable_runs = list(
        session.scalars(
            select(ScanRun)
            .where(
                ScanRun.merchant_id == merchant_id,
                ScanRun.query_set_id == run.query_set_id,
            )
            .order_by(ScanRun.created_at.desc())
            .limit(6)
        )
    )
    comparable_runs.reverse()
    categories = [
        {
            "name": _CATEGORY_LABELS[category],
            "rate": value,
            "mentioned": metrics.category_mentions[category],
            "total": metrics.category_totals[category],
        }
        for category, value in metrics.category_coverage.items()
    ]
    return DashboardRead(
        merchant={
            "id": str(merchant.id),
            "name": merchant.name,
            "branchName": merchant.branch_name,
        },
        lastRunAt=run.finished_at or run.created_at,
        metrics={
            "mentionRate": metrics.mention_rate,
            "visibilityStage": metrics.visibility_stage,
            "readinessScore": metrics.readiness_score,
            "profileCompleteness": metrics.profile_completeness,
            "publicVerifiability": metrics.public_verifiability,
            "highIntentHitRate": metrics.high_intent_hit_rate,
            "competitorGapClosure": metrics.competitor_gap_closure,
            "sourceCoverageRate": metrics.source_coverage_rate,
            "validQueryCount": metrics.valid_query_count,
            "totalQueryCount": metrics.total_query_count,
        },
        trend=[
            {
                "label": (item.finished_at or item.created_at).strftime("%m/%d %H:%M"),
                "target": (
                    metrics
                    if item.id == run.id
                    else ReportService.metrics(session, merchant_id, item.id)
                ).readiness_score
                / 100,
            }
            for item in comparable_runs
        ],
        categories=categories,
        competitors=[
            {
                "name": detail.name,
                "mentions": detail.query_count,
                "comparisonLevel": "core" if detail.query_count >= 2 else "candidate",
                "contexts": [_CATEGORY_LABELS[item] for item in detail.categories],
                "questions": detail.questions,
                "reasons": detail.reasons,
                "sourceCount": detail.source_count,
            }
            for detail in sorted(
                metrics.competitor_details,
                key=lambda item: (-item.query_count, item.name),
            )
        ],
        actions=[
            {
                "id": f"coverage-{category}",
                "title": finding["title"],
                "priority": finding["priority"],
                "evidenceCount": finding["evidenceCount"],
                "description": finding["description"],
                "questions": finding["questions"],
                "sourceChannels": source_channels_by_category.get(category, []),
                **_action_plan(category, merchant),
            }
            for category, finding in zip(
                metrics.coverage_gaps, _coverage_findings(metrics), strict=True
            )
        ],
    )


@router.get("/merchants/{merchant_id}/reports/{scan_run_id}", response_model=ReportRead)
def get_report(
    merchant_id: UUID,
    scan_run_id: UUID,
    session: SessionDep,
) -> ReportRead:
    try:
        metrics = ReportService.metrics(session, merchant_id, scan_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReportRead(
        merchant_id=merchant_id,
        scan_run_id=scan_run_id,
        metrics=metrics,
        findings=_coverage_findings(metrics),
    )


@router.get("/merchants/{merchant_id}/history", response_model=HistoryRead)
def get_history(
    merchant_id: UUID,
    left: UUID,
    right: UUID,
    session: SessionDep,
) -> HistoryRead:
    try:
        left_metrics, right_metrics, deltas = ReportService.compare(
            session, merchant_id, left, right
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HistoryRead(left=left_metrics, right=right_metrics, deltas=deltas)


@router.post(
    "/scan-runs/{scan_run_id}/manual-checks",
    response_model=ManualCheckRead,
    status_code=status.HTTP_201_CREATED,
)
def add_manual_check(
    scan_run_id: UUID,
    payload: ManualCheckCreate,
    session: SessionDep,
    _access: AdminAccessDep,
) -> ManualCheckRead:
    try:
        return ManualCheckRead.model_validate(
            ReportService.add_manual_check(session, scan_run_id, payload)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/scan-runs/{scan_run_id}/manual-checks",
    response_model=list[ManualCheckRead],
)
def list_manual_checks(
    scan_run_id: UUID,
    session: SessionDep,
) -> list[ManualCheckRead]:
    try:
        return [
            ManualCheckRead.model_validate(item)
            for item in ReportService.list_manual_checks(session, scan_run_id)
        ]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
