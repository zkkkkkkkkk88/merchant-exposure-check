from sqlalchemy.orm import Session

from app.merchants.schemas import (
    MerchantCreate,
    MerchantProfileFactWrite,
    MerchantProfileWrite,
)
from app.merchants.service import MerchantService
from app.queries.schemas import QueryUpdate
from app.queries.service import QueryLibraryService


def test_oral_care_generation_scopes_recommendations_to_private_peers(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="澜沧皓雅口腔门诊部", city="普洱市", industry="口腔医疗"),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(facts=[
            MerchantProfileFactWrite(field_key="location.city", value="澜沧县", confirmation_status="confirmed"),
            MerchantProfileFactWrite(field_key="category.precise", value="口腔医疗机构", confirmation_status="confirmed"),
        ]),
    )

    generated = QueryLibraryService.generate(db_session, merchant.id, count=6)
    recommendations = [query.text for query in generated.queries if query.intent_type == "recommendation"]

    assert recommendations
    assert all("民营口腔门诊或诊所" in text for text in recommendations)


def test_restaurant_generation_does_not_add_private_medical_scope(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="O'eat Gastronomy", city="杭州", industry="餐饮"),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(facts=[
            MerchantProfileFactWrite(field_key="location.city", value="杭州", confirmation_status="confirmed"),
            MerchantProfileFactWrite(field_key="category.precise", value="西餐厅", confirmation_status="confirmed"),
        ]),
    )

    generated = QueryLibraryService.generate(db_session, merchant.id, count=6)

    assert any("西餐厅" in query.text for query in generated.queries)
    assert all("民营" not in query.text for query in generated.queries)


def test_regeneration_uses_the_latest_edited_profile(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试门店", city="云南", industry="医疗"),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(facts=[
            MerchantProfileFactWrite(field_key="location.city", value="云南", confirmation_status="confirmed"),
            MerchantProfileFactWrite(field_key="category.precise", value="口腔医疗机构", confirmation_status="confirmed"),
        ]),
    )
    QueryLibraryService.generate(db_session, merchant.id, count=6)
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(facts=[
            MerchantProfileFactWrite(field_key="location.city", value="云南", confirmation_status="confirmed"),
            MerchantProfileFactWrite(field_key="category.precise", value="口腔门诊", confirmation_status="confirmed"),
        ]),
    )

    second = QueryLibraryService.generate(db_session, merchant.id, count=6)

    assert second.version == 2
    assert any("口腔门诊" in query.text for query in second.queries)
    assert all("口腔医疗机构" not in query.text for query in second.queries)


def test_generation_prefers_completed_county_context_over_province_profile(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="县城门诊", city="云南", industry="口腔医疗机构"),
    )
    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(facts=[
            MerchantProfileFactWrite(field_key="location.city", value="云南", confirmation_status="confirmed"),
            MerchantProfileFactWrite(field_key="category.precise", value="口腔医疗机构", confirmation_status="confirmed"),
        ]),
    )
    merchant.local_context.status = "completed"
    merchant.local_context.province = "云南省"
    merchant.local_context.city = "普洱市"
    merchant.local_context.county = "澜沧县"
    db_session.commit()

    query_set = QueryLibraryService.generate(db_session, merchant.id, count=6)

    assert all("澜沧县" in query.text or merchant.name in query.text for query in query_set.queries)
    assert all("云南有什么" not in query.text and "普洱市有什么" not in query.text for query in query_set.queries)


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
    db_session.refresh(first)
    assert first.is_archived is True
    assert second.is_archived is False
    assert [item.id for item in QueryLibraryService.list_sets(db_session, merchant.id)] == [second.id]
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
