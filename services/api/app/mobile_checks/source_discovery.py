from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.merchants.models import Merchant
from app.mobile_checks.schemas import (
    CompetitorOccurrence,
    MobileSourceCandidate,
    MobileSourceDiscoveryCreate,
    MobileSourceDiscoveryGroup,
    MobileSourceDiscoveryRead,
)
from app.platform_audits.models import PlatformAuditRun
from app.scans.adapters.base import RawCitation, SearchAdapter, SearchRequest


def _normalized_entity(name: str) -> str:
    return "".join(name.casefold().split())


def select_discovery_entities(
    merchant_name: str,
    competitors: list[CompetitorOccurrence],
) -> list[str]:
    target_key = _normalized_entity(merchant_name)
    eligible: list[tuple[int, int, str]] = []
    seen = {target_key}
    for index, competitor in enumerate(competitors):
        name = competitor.name.strip()
        key = _normalized_entity(name)
        if competitor.occurrence_count < 2 or not key or key in seen:
            continue
        seen.add(key)
        eligible.append((-competitor.occurrence_count, index, name))
    eligible.sort()
    return [merchant_name, *(name for _, _, name in eligible[:3])]


def normalize_http_url(value: str | None) -> str | None:
    if not value:
        return None
    parts = urlsplit(value.strip())
    if parts.scheme.casefold() not in {"http", "https"} or not parts.netloc:
        return None
    return urlunsplit(
        (parts.scheme.casefold(), parts.netloc.casefold(), parts.path, parts.query, "")
    )


def _source_type(url: str, title: str) -> str:
    text = f"{url} {title}".casefold()
    host = urlsplit(url).hostname or ""
    if host.endswith(".gov.cn") or host == "gov.cn":
        return "government"
    if any(token in text for token in ("工商", "登记", "registry", "信用中国")):
        return "registry"
    if any(token in text for token in ("amap.com", "map.qq.com", "map.baidu.com", "地图")):
        return "profile"
    if any(token in text for token in ("招聘", "job", "zhipin", "liepin")):
        return "recruitment"
    if "douyin.com" in text or "抖音" in text:
        return "douyin"
    return "other"


def _candidate_from_citation(
    entity_name: str,
    citation: RawCitation | dict,
    *,
    reused_from_audit: bool,
) -> MobileSourceCandidate | None:
    if isinstance(citation, dict):
        raw_url = citation.get("url")
        raw_title = citation.get("title")
        snippet = citation.get("snippet")
    else:
        raw_url = citation.url
        raw_title = citation.title
        snippet = citation.snippet
    url = normalize_http_url(str(raw_url) if raw_url else None)
    if url is None:
        return None
    title = str(raw_title).strip() if raw_title else (urlsplit(url).hostname or url)
    source_type = _source_type(url, title)
    official = source_type in {"government", "registry"}
    return MobileSourceCandidate(
        entity_name=entity_name,
        source_type=source_type,
        title=title[:500],
        facts=[str(snippet).strip()[:500]] if snippet and str(snippet).strip() else [],
        url=url,
        evidence_kind="official" if official else "third_party",
        access_status="correctable" if source_type == "profile" else "reference",
        reused_from_audit=reused_from_audit,
    )


def build_source_query(entity_name: str, city: str, location_text: str | None) -> str:
    location = (location_text or city).strip()
    return (
        f"查找{location}的“{entity_name}”公开可核验网页。优先政府登记、地图详情、"
        "机构官网和可信第三方页面；只返回确属该机构且带真实网址的结果。"
    )


class MobileSourceDiscoveryService:
    def __init__(self, session: Session, adapter: SearchAdapter):
        self.session = session
        self.adapter = adapter

    def _latest_audit_sources(
        self,
        merchant_id: UUID,
        entity_name: str,
    ) -> list[MobileSourceCandidate]:
        run = self.session.scalar(
            select(PlatformAuditRun)
            .where(
                PlatformAuditRun.merchant_id == merchant_id,
                PlatformAuditRun.status.in_(("completed", "partial")),
            )
            .order_by(PlatformAuditRun.created_at.desc(), PlatformAuditRun.id.desc())
            .options(selectinload(PlatformAuditRun.platforms))
        )
        if run is None:
            return []
        candidates: list[MobileSourceCandidate] = []
        seen: set[str] = set()
        for platform in run.platforms:
            if not platform.found:
                continue
            for evidence in platform.evidence:
                candidate = _candidate_from_citation(
                    entity_name,
                    evidence,
                    reused_from_audit=True,
                )
                if candidate is None or candidate.url in seen:
                    continue
                seen.add(candidate.url)
                candidates.append(candidate)
                if len(candidates) == 3:
                    return candidates
        return candidates

    async def discover(
        self,
        merchant_id: UUID,
        payload: MobileSourceDiscoveryCreate,
    ) -> MobileSourceDiscoveryRead:
        merchant = self.session.get(Merchant, merchant_id)
        if merchant is None:
            raise LookupError("merchant not found")
        entities = select_discovery_entities(merchant.name, payload.competitors)
        groups: list[MobileSourceDiscoveryGroup] = []
        external_call_count = 0
        for index, entity_name in enumerate(entities):
            sources = (
                self._latest_audit_sources(merchant.id, entity_name)
                if index == 0
                else []
            )
            error = None
            if len(sources) < 3:
                external_call_count += 1
                try:
                    response = await self.adapter.search(
                        SearchRequest(
                            query=build_source_query(
                                entity_name,
                                merchant.city,
                                payload.location_text,
                            ),
                            merchant_id=merchant.id,
                            correlation_id=f"mobile-source:{merchant.id}:{index}",
                        )
                    )
                    seen = {source.url for source in sources}
                    for citation in response.citations:
                        candidate = _candidate_from_citation(
                            entity_name,
                            citation,
                            reused_from_audit=False,
                        )
                        if candidate is None or candidate.url in seen:
                            continue
                        seen.add(candidate.url)
                        sources.append(candidate)
                        if len(sources) == 3:
                            break
                except Exception:
                    error = "本次检索未完成"
            groups.append(
                MobileSourceDiscoveryGroup(
                    entity_name=entity_name,
                    sources=sources[:3],
                    error=error,
                )
            )
        return MobileSourceDiscoveryRead(
            groups=groups,
            external_call_count=external_call_count,
        )
