import json
import re
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.merchants.models import Merchant, MerchantLocalContext
from app.scans.adapters.base import SearchAdapter, SearchRequest


class ResolvedLocalContext(BaseModel):
    province: str | None = None
    city: str | None = None
    county: str | None = None
    township: str | None = None
    normalized_address: str | None = None
    landmarks: list[str] = Field(default_factory=list)
    transport_options: list[str] = Field(default_factory=list)


def parse_local_context(raw_text: str) -> ResolvedLocalContext:
    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match is None:
        raise ValueError("local context response must contain JSON")
    try:
        return ResolvedLocalContext.model_validate(json.loads(match.group(0)))
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError("local context response must contain valid JSON") from error


def build_local_context_prompt(merchant: Merchant) -> str:
    confirmed = {
        fact.field_key: fact.value
        for fact in merchant.profile_facts
        if fact.confirmation_status == "confirmed"
    }
    city = confirmed.get("location.city") or merchant.city
    district = confirmed.get("location.district") or merchant.district
    address = confirmed.get("location.address") or merchant.address
    return (
        f"联网核验行政区划和地址。商家:{merchant.name};城市:{city};"
        f"区县:{district or '无'};地址:{address or '无'}。"
        "优先识别县、自治县或县级市，无县才用市，无市才用省。"
        "地标和交通必须有来源，不推测机场、车站、商圈。只输出JSON:"
        '{"province":null,"city":null,"county":null,"township":null,'
        '"normalized_address":null,"landmarks":[],"transport_options":[]}'
    )


async def process_next_local_context(
    session_factory: sessionmaker[Session],
    adapter: SearchAdapter | None,
) -> UUID | None:
    with session_factory() as session:
        context = session.scalar(
            select(MerchantLocalContext)
            .where(MerchantLocalContext.status == "pending")
            .order_by(MerchantLocalContext.created_at)
            .with_for_update(skip_locked=True)
        )
        if context is None:
            return None
        merchant = session.get(Merchant, context.merchant_id)
        if merchant is None:
            return None
        context.status = "running"
        session.commit()
        merchant_id = merchant.id
        prompt = build_local_context_prompt(merchant)

    try:
        if adapter is None:
            raise ValueError("Ark adapter is not configured")
        response = await adapter.search(
            SearchRequest(query=prompt, merchant_id=merchant_id, correlation_id=f"local-context:{merchant_id}")
        )
        resolved = parse_local_context(response.raw_text)
        source_urls = [citation.url for citation in response.citations]
        if not source_urls:
            raise ValueError("local context response has no citations")
        if not (resolved.county or resolved.city or resolved.province):
            raise ValueError("local context response has no confirmed region")
        with session_factory() as session:
            context = session.get(MerchantLocalContext, merchant_id)
            if context is None:
                return merchant_id
            for field, value in resolved.model_dump().items():
                setattr(context, field, value)
            context.source_urls = source_urls
            context.raw_summary = response.raw_text
            context.error_message = None
            context.status = "completed"
            session.commit()
    except Exception as error:
        with session_factory() as session:
            context = session.get(MerchantLocalContext, merchant_id)
            if context is not None:
                context.status = "failed"
                context.error_message = str(error)
                session.commit()
    return merchant_id
