from sqlalchemy.orm import Session

from app.merchants.schemas import MerchantCreate
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

    first = QueryLibraryService.generate(db_session, merchant.id, count=30)
    second = QueryLibraryService.generate(db_session, merchant.id, count=30)

    assert first.version == 1
    assert second.version == 2
    assert first.id != second.id
    assert len(first.queries) == 30
    assert all(query.review_status == "pending" for query in first.queries)


def test_review_updates_query_without_changing_its_set(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试餐厅", city="杭州", industry="餐饮"),
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
