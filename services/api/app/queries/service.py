from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.merchants.schemas import MerchantRead
from app.merchants.profile import confirmed_fact_map
from app.merchants.service import MerchantNotFoundError, MerchantService
from app.queries.generator import TemplateQueryGenerator
from app.queries.models import Query, QuerySet
from app.queries.rules.restaurant import RestaurantProfile, RestaurantRulePack
from app.queries.schemas import QueryUpdate


class QueryNotFoundError(LookupError):
    pass


class IncompleteMerchantProfileError(ValueError):
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

        if generator is None:
            facts = confirmed_fact_map(MerchantService.get_profile(session, merchant_id).facts)
            rule_pack = RestaurantRulePack()
            try:
                drafts = rule_pack.generate(
                    RestaurantProfile(merchant_name=merchant.name, facts=facts),
                    count,
                )
            except ValueError as error:
                raise IncompleteMerchantProfileError(str(error)) from error
            generator_name = rule_pack.name
        else:
            drafts = generator.generate(MerchantRead.model_validate(merchant), count)
            generator_name = generator.name
        latest_version = session.scalar(
            select(func.max(QuerySet.version)).where(QuerySet.merchant_id == merchant_id)
        )
        query_set = QuerySet(
            merchant_id=merchant_id,
            version=(latest_version or 0) + 1,
            generator_name=generator_name,
            queries=[
                Query(
                    text=draft.text,
                    category=draft.category,
                    reason=draft.reason,
                    priority=draft.priority,
                    intent_type=draft.intent_type,
                    fact_keys=draft.fact_keys,
                )
                for draft in drafts
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
