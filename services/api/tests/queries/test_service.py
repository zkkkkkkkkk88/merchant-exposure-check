from sqlalchemy.orm import Session

from app.merchants.schemas import (
    MerchantCreate,
    MerchantProfileFactWrite,
    MerchantProfileWrite,
)
from app.merchants.service import MerchantService
from app.queries.schemas import QueryUpdate
from app.queries.service import QueryLibraryService


def test_generation_creates_incrementing_query_set_versions(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="O'eat Gastronomy",
            city="杭州",
            district="上城区",
            industry="餐饮",
            products=["西餐", "约会餐厅"],
        ),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(
            facts=[
                MerchantProfileFactWrite(
                    field_key="location.city",
                    value="杭州",
                    confirmation_status="confirmed",
                ),
                MerchantProfileFactWrite(
                    field_key="category.precise",
                    value="西餐厅",
                    confirmation_status="confirmed",
                ),
            ]
        ),
    )

    first = QueryLibraryService.generate(db_session, merchant.id, count=6)
    second = QueryLibraryService.generate(db_session, merchant.id, count=6)

    assert first.version == 1
    assert second.version == 2
    assert first.id != second.id
    assert len(first.queries) == 6
    assert all(query.review_status == "pending" for query in first.queries)
    assert all(query.intent_type in {"recommendation", "verification"} for query in first.queries)
    assert all("餐饮" not in query.text for query in first.queries)


def test_review_updates_query_without_changing_its_set(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试餐厅", city="杭州", industry="餐饮"),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(
            facts=[
                MerchantProfileFactWrite(
                    field_key="location.city",
                    value="杭州",
                    confirmation_status="confirmed",
                ),
                MerchantProfileFactWrite(
                    field_key="category.precise",
                    value="西餐厅",
                    confirmation_status="confirmed",
                ),
            ]
        ),
    )
    query_set = QueryLibraryService.generate(db_session, merchant.id, count=6)
    query = query_set.queries[0]

    updated = QueryLibraryService.update_query(
        db_session,
        query.id,
        QueryUpdate(
            text="杭州餐厅推荐",
            priority=3,
            is_enabled=False,
            review_status="approved",
        ),
    )

    assert updated.text == "杭州餐厅推荐"
    assert updated.priority == 3
    assert updated.is_enabled is False
    assert updated.review_status == "approved"
    assert updated.query_set_id == query_set.id
