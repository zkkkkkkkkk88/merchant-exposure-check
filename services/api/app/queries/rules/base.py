from typing import Protocol

from app.queries.schemas import QueryDraft


class QueryRulePack(Protocol):
    name: str

    def generate(self, profile: object, count: int) -> list[QueryDraft]: ...

