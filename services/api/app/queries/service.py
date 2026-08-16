from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.merchants.profile import confirmed_fact_map
from app.merchants.schemas import MerchantRead
from app.merchants.service import MerchantNotFoundError, MerchantService
from app.queries.generator import TemplateQueryGenerator
from app.queries.models import Query, QuerySet
from app.queries.rules.restaurant import RestaurantProfile, RestaurantRulePack
from app.queries.schemas import QueryUpdate
from app.mobile_checks.models import MobileValidationItem
from app.reports.models import ManualCheck
from app.scans.models import QueryResult, ScanRun


class QueryNotFoundError(LookupError):
    pass


class IncompleteMerchantProfileError(ValueError):
    pass


class QueryLibraryService:
    @staticmethod
    def generate(
        session: Session,
        merchant_id: UUID,
        count: int = 15,
        generator: TemplateQueryGenerator | None = None,
    ) -> QuerySet:
        merchant = MerchantService.get(session, merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(str(merchant_id))

        if generator is None:
            facts = confirmed_fact_map(MerchantService.get_profile(session, merchant_id).facts)
            precise_category = facts.get("category.precise")
            if "口腔" in merchant.industry or (isinstance(precise_category, str) and "口腔" in precise_category):
                facts["category.precise"] = "民营口腔门诊或诊所"
            context = merchant.local_context
            if context is not None and context.status == "completed":
                scope = context.county or context.city or context.province
                if scope:
                    facts["location.city"] = scope
                if context.county:
                    facts.pop("location.district", None)
                    facts.pop("location.venue", None)
                elif context.city:
                    facts.pop("location.district", None)
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
        active_sets = session.scalars(
            select(QuerySet).where(
                QuerySet.merchant_id == merchant_id,
                QuerySet.is_archived.is_(False),
            )
        )
        for active_set in active_sets:
            active_set.is_archived = True
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
            .where(QuerySet.merchant_id == merchant_id, QuerySet.is_archived.is_(False))
            .order_by(QuerySet.version.desc())
        )
        return list(session.scalars(statement).all())

    @staticmethod
    def cleanup_legacy_sets(session: Session, merchant_id: UUID) -> dict[str, int]:
        query_sets = list(session.scalars(
            select(QuerySet)
            .where(QuerySet.merchant_id == merchant_id)
            .order_by(QuerySet.version.desc(), QuerySet.created_at.desc(), QuerySet.id.desc())
        ))
        if not query_sets:
            return {"deleted": 0, "archived": 0, "kept": 0}

        deleted = 0
        archived = 0
        for query_set in query_sets[1:]:
            query_ids = select(Query.id).where(Query.query_set_id == query_set.id)
            referenced = any((
                session.scalar(select(ScanRun.id).where(ScanRun.query_set_id == query_set.id).limit(1)),
                session.scalar(select(QueryResult.id).where(QueryResult.query_id.in_(query_ids)).limit(1)),
                session.scalar(select(ManualCheck.id).where(ManualCheck.query_id.in_(query_ids)).limit(1)),
                session.scalar(select(MobileValidationItem.id).where(MobileValidationItem.query_id.in_(query_ids)).limit(1)),
            ))
            if referenced:
                if not query_set.is_archived:
                    query_set.is_archived = True
                    archived += 1
            else:
                session.delete(query_set)
                deleted += 1
        session.commit()
        return {"deleted": deleted, "archived": archived, "kept": 1}

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
