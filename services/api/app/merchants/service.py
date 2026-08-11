from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.merchants.models import Merchant, MerchantProfileFact, MerchantSource
from app.merchants.schemas import (
    MerchantCreate,
    MerchantProfileFactRead,
    MerchantProfileRead,
    MerchantProfileWrite,
    MerchantSourceCreate,
    MerchantUpdate,
)


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def build_source(source: MerchantSourceCreate) -> MerchantSource:
    return MerchantSource(
        kind=normalize_text(source.kind),
        url=str(source.url),
        is_verified=source.is_verified,
    )


class MerchantNotFoundError(LookupError):
    pass


class MerchantService:
    @staticmethod
    def create(session: Session, payload: MerchantCreate) -> Merchant:
        name = normalize_text(payload.name)
        merchant = Merchant(
            name=name,
            normalized_name=name.casefold(),
            branch_name=normalize_text(payload.branch_name) if payload.branch_name else None,
            city=normalize_text(payload.city),
            district=normalize_text(payload.district) if payload.district else None,
            industry=normalize_text(payload.industry),
            address=normalize_text(payload.address) if payload.address else None,
            price_range=normalize_text(payload.price_range) if payload.price_range else None,
            opening_hours=normalize_text(payload.opening_hours) if payload.opening_hours else None,
            products=[normalize_text(item) for item in payload.products],
            strengths=[normalize_text(item) for item in payload.strengths],
            sources=[build_source(source) for source in payload.sources],
        )
        session.add(merchant)
        session.commit()
        session.refresh(merchant)
        return merchant

    @staticmethod
    def list(session: Session) -> list[Merchant]:
        statement = select(Merchant).order_by(Merchant.created_at, Merchant.id)
        return list(session.scalars(statement).all())

    @staticmethod
    def get(session: Session, merchant_id: UUID) -> Merchant | None:
        return session.get(Merchant, merchant_id)

    @staticmethod
    def update(session: Session, merchant_id: UUID, payload: MerchantUpdate) -> Merchant:
        merchant = MerchantService.get(session, merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(str(merchant_id))

        values = payload.model_dump(exclude_unset=True, exclude={"sources"})
        for field, value in values.items():
            if field in {"products", "strengths"} and value is not None:
                value = [normalize_text(item) for item in value]
            elif isinstance(value, str):
                value = normalize_text(value)
            setattr(merchant, field, value)

        if "name" in values and merchant.name is not None:
            merchant.normalized_name = merchant.name.casefold()
        if payload.sources is not None:
            merchant.sources = [build_source(source) for source in payload.sources]

        session.commit()
        session.refresh(merchant)
        return merchant

    @staticmethod
    def get_profile(session: Session, merchant_id: UUID) -> MerchantProfileRead:
        merchant = MerchantService.get(session, merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(str(merchant_id))

        stored = {
            fact.field_key: MerchantProfileFactRead.model_validate(fact)
            for fact in merchant.profile_facts
        }
        candidates: dict[str, object | None] = {
            "location.city": merchant.city,
            "location.district": merchant.district,
            "category.legacy": merchant.industry,
            "location.address": merchant.address,
            "price.display": merchant.price_range,
            "hours.display": merchant.opening_hours,
            "product.list": merchant.products or None,
            "strength.list": merchant.strengths or None,
        }
        for field_key, value in candidates.items():
            if value is not None and field_key not in stored:
                stored[field_key] = MerchantProfileFactRead(
                    field_key=field_key,
                    value=value,
                    confirmation_status="pending",
                )
        return MerchantProfileRead(merchant_id=merchant.id, facts=list(stored.values()))

    @staticmethod
    def replace_profile(
        session: Session,
        merchant_id: UUID,
        payload: MerchantProfileWrite,
    ) -> MerchantProfileRead:
        merchant = MerchantService.get(session, merchant_id)
        if merchant is None:
            raise MerchantNotFoundError(str(merchant_id))
        merchant.profile_facts = [
            MerchantProfileFact(
                field_key=fact.field_key,
                value=fact.value,
                confirmation_status=fact.confirmation_status,
                confidence=fact.confidence,
                source_urls=[str(url) for url in fact.source_urls],
            )
            for fact in payload.facts
        ]
        session.commit()
        session.refresh(merchant)
        return MerchantService.get_profile(session, merchant_id)
