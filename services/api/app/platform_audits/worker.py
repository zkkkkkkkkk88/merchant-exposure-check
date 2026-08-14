import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.merchants.models import Merchant
from app.platform_audits.amap import AmapClient
from app.platform_audits.models import PlatformAuditRun
from app.platform_audits.service import PlatformAuditService
from app.platform_audits.tencent_maps import TencentMapClient
from app.scans.adapters.ark import ArkSearchAdapter
from app.scans.adapters.base import SearchAdapter, SearchRequest

PLATFORM_CATALOG = (
    ("amap", "高德地图"),
    ("baidu_maps", "百度地图"),
    ("tencent_maps", "腾讯地图"),
    ("official_web", "官网 / 公众号公开页"),
    ("social_video", "抖音 / 视频号公开内容"),
    ("registry", "工商登记"),
    ("medical_registry", "医疗机构公开登记"),
    ("recruitment", "招聘 / 第三方公开页"),
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_platform_query(merchant: Merchant, platform_name: str) -> str:
    return (
        f"请只检索{platform_name}的公开页面，核实商家“{merchant.name}”"
        f"（{merchant.city}{merchant.district or ''}）的信息。"
        "返回 JSON：found，以及 fields 中的 name、address、phone、opening_hours、products、credentials。"
        "找不到可确认页面时 found=false，不要推断为未发布。"
    )


def parse_public_info(raw_text: str) -> tuple[bool, dict]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("返回内容不是可解析的 JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("found"), bool):
        raise ValueError("返回内容缺少 found")
    fields = payload.get("fields") or {}
    if not isinstance(fields, dict):
        raise ValueError("fields 格式不正确")
    return payload["found"], fields


async def process_next_platform_audit(
    session_factory: sessionmaker[Session],
    adapter: SearchAdapter | None,
    amap: AmapClient | None = None,
    tencent_maps: TencentMapClient | None = None,
) -> UUID | None:
    with session_factory() as session:
        run = session.scalar(
            select(PlatformAuditRun)
            .where(PlatformAuditRun.status == "queued")
            .order_by(PlatformAuditRun.created_at)
            .with_for_update(skip_locked=True)
        )
        if run is None:
            return None
        run.status = "running"
        run.started_at = utc_now()
        session.commit()
        run_id = run.id
        merchant_id = run.merchant_id

    failure_count = 0
    for platform_key, platform_name in PLATFORM_CATALOG:
        query = None
        try:
            with session_factory() as session:
                merchant = session.get(Merchant, merchant_id)
                if merchant is None:
                    raise ValueError("商家不存在")
                query = build_platform_query(merchant, platform_name)
            if platform_key == "amap" and amap is not None:
                lookup = await amap.lookup(
                    merchant_name=merchant.name,
                    city=merchant.city,
                    district=merchant.district,
                )
                found, fields, evidence = lookup.found, lookup.fields, lookup.evidence
            elif platform_key == "tencent_maps" and tencent_maps is not None:
                lookup = await tencent_maps.lookup(
                    merchant_name=merchant.name,
                    city=merchant.city,
                    district=merchant.district,
                )
                found, fields, evidence = lookup.found, lookup.fields, lookup.evidence
            else:
                if adapter is None:
                    raise ValueError("未配置公开检索服务")
                response = await adapter.search(
                    SearchRequest(
                        query=query,
                        merchant_id=merchant_id,
                        correlation_id=f"platform-audit:{run_id}:{platform_key}",
                    )
                )
                found, fields = parse_public_info(response.raw_text)
                evidence = [
                    {"url": citation.url, "title": citation.title, "snippet": citation.snippet}
                    for citation in response.citations
                ]
            with session_factory() as session:
                PlatformAuditService(session).record_platform(
                    run_id,
                    platform_key,
                    platform_name,
                    found=found,
                    fields=fields,
                    evidence=evidence,
                    search_query=query,
                )
        except Exception as exc:  # one platform must not abort the other checks
            failure_count += 1
            with session_factory() as session:
                PlatformAuditService(session).record_failure(
                    run_id, platform_key, platform_name, str(exc), search_query=query
                )

    with session_factory() as session:
        run = session.get(PlatformAuditRun, run_id)
        if run is not None:
            run.status = (
                "completed"
                if failure_count == 0
                else "failed"
                if failure_count == len(PLATFORM_CATALOG)
                else "partial"
            )
            run.finished_at = utc_now()
            if failure_count:
                run.error_message = f"{failure_count} 个平台本次未完成检索"
            session.commit()
    return run_id


async def run_platform_worker(poll_interval: float = 2.0) -> None:
    settings = get_settings()
    api_key = settings.ark_api_key.get_secret_value()
    adapter = ArkSearchAdapter(api_key=api_key, model=settings.ark_model) if api_key else None
    amap_key = settings.amap_key.get_secret_value()
    amap = AmapClient(amap_key) if amap_key else None
    tencent_key = settings.tencent_map_key.get_secret_value()
    tencent_maps = TencentMapClient(tencent_key) if tencent_key else None
    while True:
        processed = await process_next_platform_audit(SessionLocal, adapter, amap, tencent_maps)
        if processed is None:
            await asyncio.sleep(poll_interval)


def main() -> None:
    asyncio.run(run_platform_worker())


if __name__ == "__main__":
    main()
