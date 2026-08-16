from app.queries.rules.restaurant import RestaurantProfile, RestaurantRulePack


def oeat_profile() -> RestaurantProfile:
    return RestaurantProfile(
        merchant_name="O'eat Gastronomy",
        facts={
            "location.city": "杭州",
            "location.venue": "万象城",
            "category.precise": "西餐厅",
            "price.display": "双人餐 300–450 元",
            "product.list": ["牛排", "意面"],
            "service.baby_chair": True,
            "occasion.list": ["约会", "亲子"],
            "need.transport": "交通方便",
        },
    )


def test_oeat_questions_never_use_generic_dining_or_low_price() -> None:
    drafts = RestaurantRulePack().generate(oeat_profile(), count=30)

    assert len(drafts) == 30
    assert len({draft.text for draft in drafts}) == 30
    assert all("餐饮" not in draft.text for draft in drafts)
    assert all("50元以内" not in draft.text for draft in drafts)
    assert all("100元以内" not in draft.text for draft in drafts)
    assert all("200元以内" not in draft.text for draft in drafts)
    assert any("西餐厅" in draft.text and "万象城" in draft.text for draft in drafts)
    assert any("300–450" in draft.text for draft in drafts)


def test_confirmed_services_and_intent_are_traceable() -> None:
    drafts = RestaurantRulePack().generate(oeat_profile(), count=30)

    baby_chair = [draft for draft in drafts if "宝宝" in draft.text]
    assert baby_chair
    assert all("service.baby_chair" in draft.fact_keys for draft in baby_chair)
    assert {draft.intent_type for draft in drafts} == {"recommendation", "verification"}
    assert any(
        draft.intent_type == "verification" and "O'eat Gastronomy" in draft.text
        for draft in drafts
    )


def test_unconfirmed_service_is_not_included() -> None:
    profile = oeat_profile()
    profile.facts.pop("service.baby_chair")

    drafts = RestaurantRulePack().generate(profile, count=30)

    assert all("宝宝" not in draft.text for draft in drafts)
    assert all("baby_chair" not in draft.fact_keys for draft in drafts)


def test_small_query_set_keeps_price_and_verification_coverage() -> None:
    drafts = RestaurantRulePack().generate(oeat_profile(), count=12)

    assert any(draft.category == "price" and "300–450" in draft.text for draft in drafts)
    assert any(draft.intent_type == "verification" for draft in drafts)


def test_fifteen_question_set_uses_confirmed_products() -> None:
    drafts = RestaurantRulePack().generate(oeat_profile(), count=15)

    product_questions = [draft for draft in drafts if draft.category == "product"]
    assert product_questions
    assert any("牛排" in draft.text or "意面" in draft.text for draft in product_questions)
    assert all("product.list" in draft.fact_keys for draft in product_questions)
