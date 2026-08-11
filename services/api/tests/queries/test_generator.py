from sqlalchemy.orm import Session

from app.merchants.schemas import MerchantCreate, MerchantRead
from app.merchants.service import MerchantService
from app.queries.generator import TemplateQueryGenerator


def test_template_generator_creates_balanced_unique_discovery_questions(
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(
            name="O'eat Gastronomy",
            branch_name="杭州万象城店",
            city="杭州",
            district="上城区",
            industry="餐饮",
            products=["西餐", "约会餐厅"],
        ),
    )

    drafts = TemplateQueryGenerator().generate(
        MerchantRead.model_validate(merchant),
        count=30,
    )

    assert len(drafts) == 30
    assert {draft.category for draft in drafts} == {
        "geo",
        "category",
        "product",
        "price",
        "occasion",
        "need",
    }
    assert len({draft.text for draft in drafts}) == 30
    assert all("O'eat" not in draft.text for draft in drafts)
    assert all(draft.reason.strip() for draft in drafts)
    assert all(1 <= draft.priority <= 5 for draft in drafts)


def test_template_generator_keeps_one_hundred_questions_unique_without_district(
    db_session: Session,
) -> None:
    merchant = MerchantService.create(
        db_session,
        MerchantCreate(name="测试餐厅", city="杭州", industry="餐饮"),
    )

    drafts = TemplateQueryGenerator().generate(
        MerchantRead.model_validate(merchant),
        count=100,
    )

    assert len(drafts) == 100
    assert len({draft.text for draft in drafts}) == 100
