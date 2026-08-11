from sqlalchemy.orm import Session

from app.merchants.schemas import MerchantCreate, MerchantSourceCreate, MerchantUpdate
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
