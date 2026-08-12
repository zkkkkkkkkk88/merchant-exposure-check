from sqlalchemy.orm import Session

from app.merchants.schemas import (
    MerchantCreate,
    MerchantProfileFactWrite,
    MerchantProfileWrite,
    MerchantSourceCreate,
    MerchantUpdate,
)
from app.merchants.service import MerchantService


def test_create_merchant_keeps_public_sources(db_session: Session) -> None:
    payload = MerchantCreate(
        name="  O'eat   Gastronomy  ",
        branch_name="杭州万象城店",
        city="杭州",
        district="上城区",
        industry="餐饮",
        products=["西餐", "约会餐厅"],
        sources=[
            MerchantSourceCreate(
                kind="meituan",
                url="https://pmtmeishi.meituan.com/dp/prefer/list/1510759369",
            )
        ],
    )

    merchant = MerchantService.create(db_session, payload)

    assert merchant.name == "O'eat Gastronomy"
    assert merchant.normalized_name == "o'eat gastronomy"
    assert merchant.city == "杭州"
    assert merchant.products == ["西餐", "约会餐厅"]
    assert len(merchant.sources) == 1
    assert merchant.sources[0].kind == "meituan"


def test_list_returns_created_merchants(db_session: Session) -> None:
    for name in ["第一家", "第二家"]:
        MerchantService.create(
            db_session,
            MerchantCreate(name=name, city="杭州", industry="餐饮"),
        )

    merchants = MerchantService.list(db_session)

    assert [merchant.name for merchant in merchants] == ["第一家", "第二家"]


def test_update_replaces_supplied_fields_and_sources(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="旧名称",
            city="杭州",
            industry="餐饮",
            sources=[MerchantSourceCreate(kind="website", url="https://example.com/old")],
        ),
    )

    updated = MerchantService.update(
        db_session,
        merchant.id,
        MerchantUpdate(
            name=" 新名称 ",
            products=["早午餐"],
            sources=[MerchantSourceCreate(kind="meituan", url="https://example.com/new")],
        ),
    )

    assert updated.name == "新名称"
    assert updated.normalized_name == "新名称"
    assert updated.products == ["早午餐"]
    assert [source.url for source in updated.sources] == ["https://example.com/new"]


def test_replace_profile_can_update_existing_fact_values(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试门店", city="云南", industry="医疗"),
    )
    initial = MerchantProfileWrite(facts=[
        MerchantProfileFactWrite(field_key="location.city", value="云南", confirmation_status="confirmed"),
        MerchantProfileFactWrite(field_key="category.precise", value="口腔医疗机构", confirmation_status="confirmed"),
    ])
    MerchantService.replace_profile(db_session, merchant.id, initial)

    updated = MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(facts=[
            initial.facts[0],
            MerchantProfileFactWrite(field_key="category.precise", value="口腔门诊", confirmation_status="confirmed"),
        ]),
    )

    facts = {fact.field_key: fact.value for fact in updated.facts}
    assert facts["category.precise"] == "口腔门诊"
    assert len([fact for fact in updated.facts if fact.field_key == "category.precise"]) == 1


def test_create_enqueues_local_context_and_address_change_invalidates_it(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="县城门诊",
            city="云南",
            district="普洱市",
            industry="口腔医疗机构",
            address="澜沧县勐朗镇东朗路1号",
        ),
    )

    assert merchant.local_context.status == "pending"
    merchant.local_context.status = "completed"
    db_session.commit()

    MerchantService.update(
        db_session,
        merchant.id,
        MerchantUpdate(address="澜沧县勐朗镇东朗路2号"),
    )

    assert merchant.local_context.status == "pending"
    assert merchant.local_context.county is None


def test_non_address_update_keeps_completed_local_context(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="县城门诊", city="云南", industry="口腔医疗机构"),
    )
    merchant.local_context.status = "completed"
    merchant.local_context.county = "澜沧县"
    db_session.commit()

    MerchantService.update(db_session, merchant.id, MerchantUpdate(opening_hours="09:00-18:00"))

    assert merchant.local_context.status == "completed"
    assert merchant.local_context.county == "澜沧县"


def test_profile_address_change_invalidates_local_context(db_session: Session) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="县城门诊", city="云南", industry="口腔医疗机构"),
    )
    merchant.local_context.status = "completed"
    merchant.local_context.county = "澜沧县"
    db_session.commit()

    MerchantService.replace_profile(
        db_session,
        merchant.id,
        MerchantProfileWrite(facts=[
            MerchantProfileFactWrite(field_key="location.city", value="云南", confirmation_status="confirmed"),
            MerchantProfileFactWrite(field_key="location.address", value="澜沧县勐朗镇东朗路2号", confirmation_status="confirmed"),
            MerchantProfileFactWrite(field_key="category.precise", value="口腔医疗机构", confirmation_status="confirmed"),
        ]),
    )

    assert merchant.local_context.status == "pending"
    assert merchant.local_context.county is None
