from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.merchants.schemas import MerchantRead
from app.merchants.service import MerchantNotFoundError, MerchantService
from app.queries.generator import TemplateQueryGenerator
from app.queries.models import Query, QuerySet
from app.queries.schemas import QueryUpdate


class QueryNotFoundError(LookupError):
    pass


class QueryLibraryService:
    @staticmethod
    def generate(
        session: Session,
        merchant_id: UUID,
        count: int = 30,
        generator: TemplateQueryGenerator | None = None,
    ) -> QuerySet:
        merchant = MerchantService.get(session, merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(str(merchant_id))

        generator = generator or TemplateQueryGenerator()
        latest_version = session.scalar(
            select(func.max(QuerySet.version)).where(QuerySet.merchant_id == merchant_id)
        )
        query_set = QuerySet(
            merchant_id=merchant_id,
            version=(latest_version or 0) + 1,
            generator_name=generator.name,
            queries=[
                Query(
                    text=draft.text,
                    category=draft.category,
                    reason=draft.reason,
                    priority=draft.priority,
                )
                for draft in generator.generate(MerchantRead.model_validate(merchant), count)
            ],
        )
        session.add(query_set)
        session.commit()
        session.refresh(query_set)
        return query_set

    @staticmethod
    def list_sets(session: Session, merchant_id: UUID) -> list[QuerySet]:
        statement = (
            select(QuerySet)
            .where(QuerySet.merchant_id == merchant_id)
            .order_by(QuerySet.version.desc())
        )
        return list(session.scalars(statement).all())

    @staticmethod
    def update_query(session: Session, query_id: UUID, payload: QueryUpdate) -> Query:
        query = session.get(Query, query_id)
        if query is None:
            raise QueryNotFoundError(str(query_id))

        values = payload.model_dump(exclude_unset=True)
        if isinstance(values.get("text"), str):
            values["text"] = " ".join(values["text"].split())
        for field, value in values.items():
            setattr(query, field, value)

        session.commit()
        session.refresh(query)
        return query
