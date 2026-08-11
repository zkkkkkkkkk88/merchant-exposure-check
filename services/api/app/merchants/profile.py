import re
from collections.abc import Iterable, Mapping
from typing import Any

from app.merchants.schemas import MerchantProfileFactRead


def confirmed_fact_map(facts: Iterable[Any]) -> dict[str, object]:
    """Return only facts a merchant explicitly confirmed."""
    confirmed: dict[str, object] = {}
    for fact in facts:
        if isinstance(fact, Mapping):
            field_key = fact.get("field_key")
            status = fact.get("confirmation_status")
            value = fact.get("value")
        else:
            field_key = getattr(fact, "field_key", None)
            status = getattr(fact, "confirmation_status", None)
            value = getattr(fact, "value", None)
        if isinstance(field_key, str) and status == "confirmed":
            confirmed[field_key] = value
    return confirmed


def parse_restaurant_profile_text(
    raw_text: str,
    *,
    city: str,
    source_urls: list[str],
) -> list[MerchantProfileFactRead]:
    facts: dict[str, MerchantProfileFactRead] = {}

    def add(field_key: str, value: object, confidence: float) -> None:
        facts[field_key] = MerchantProfileFactRead(
            field_key=field_key,
            value=value,
            confirmation_status="pending",
            confidence=confidence,
            source_urls=source_urls,
        )

    if city and city in raw_text:
        add("location.city", city, 0.99)

    categories = ("西餐厅", "牛排馆", "火锅店", "咖啡馆", "日料店", "中餐厅", "餐厅")
    precise_category = next((item for item in categories if item in raw_text), None)
    if precise_category:
        add("category.precise", precise_category, 0.95)

    if "万象城" in raw_text:
        add("location.venue", "万象城", 0.94)

    price = re.search(
        r"双人餐[^\d]{0,8}(\d{2,5})\s*(?:到|至|[-–—])\s*(\d{2,5})\s*元?",
        raw_text,
    )
    if price:
        add("price.display", f"双人餐 {price.group(1)}–{price.group(2)} 元", 0.96)

    services = {
        "宝宝椅": "service.baby_chair",
        "无烟餐厅": "service.smoke_free",
        "明厨亮灶": "service.open_kitchen",
        "停车": "service.parking",
        "包间": "service.private_room",
    }
    for label, field_key in services.items():
        if label in raw_text:
            add(field_key, True, 0.9)

    if any(term in raw_text for term in ("地铁", "交通方便", "交通便利")):
        add("need.transport", "交通方便", 0.86)

    occasions = [item for item in ("约会", "亲子", "商务", "纪念日", "朋友聚餐") if item in raw_text]
    if occasions:
        add("occasion.list", occasions, 0.88)

    return list(facts.values())
