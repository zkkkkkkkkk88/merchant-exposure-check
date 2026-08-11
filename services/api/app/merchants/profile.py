from collections.abc import Iterable, Mapping
from typing import Any


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

