import pytest

from app.analysis.contracts import ExtractedMention, ExtractionPayload
from app.analysis.extractor import (
    extract_ranked_mentions,
    extract_target_mention,
    validate_extraction,
)


def test_extraction_rejects_citation_urls_not_saved_with_result() -> None:
    payload = ExtractionPayload(
        is_valid=True,
        has_explicit_ranking=True,
        confidence=0.9,
        mentions=[
            ExtractedMention(
                raw_name="O'eat Gastronomy",
                position=1,
                confidence=0.9,
                citation_urls=["https://invented.example/source"],
            )
        ],
    )

    with pytest.raises(ValueError, match="not present in saved result"):
        validate_extraction(payload, {"https://real.example/source"})


def test_target_extractor_recognizes_numbered_brand_mention() -> None:
    payload = extract_target_mention(
        "1. O'eat Gastronomy：适合约会。",
        target_names=["O'eat Gastronomy", "O'eat"],
    )

    assert payload.is_valid is True
    assert payload.has_explicit_ranking is True
    assert payload.mentions[0].raw_name == "O'eat Gastronomy"
    assert payload.mentions[0].position == 1
    assert payload.is_recommended is True


def test_target_extractor_does_not_treat_negative_context_as_recommendation() -> None:
    payload = extract_target_mention(
        "O'eat Gastronomy 暂不推荐，因为公开信息不足。",
        target_names=["O'eat Gastronomy"],
    )

    assert payload.mentions
    assert payload.is_recommended is False


def test_ranked_extractor_returns_each_explicit_restaurant_entry_once() -> None:
    mentions = extract_ranked_mentions(
        """
        ### 1. O'eat Gastronomy（杭州万象城店）
        适合约会。
        ### 2. Alimentari Mulino 意大利餐吧·烘焙（杭州万象城店）
        手工意面。
        3、pennehut畔尼意面（杭州万象城店）：位于五楼。
        """
    )

    assert [(item.raw_name, item.position) for item in mentions] == [
        ("O'eat Gastronomy", 1),
        ("Alimentari Mulino 意大利餐吧·烘焙", 2),
        ("pennehut畔尼意面", 3),
    ]


def test_ranked_extractor_keeps_each_restaurant_reason_inside_its_section() -> None:
    mentions = extract_ranked_mentions(
        """
        1. Alimentari Mulino（杭州万象城店）
        特色：手工意面，适合朋友小坐。
        2. pennehut畔尼意面：交通方便
        招牌：窑烤意式披萨。
        ### 选择建议
        请按实际预算选择。
        """
    )

    assert mentions[0].recommendation_reason == "特色：手工意面，适合朋友小坐。"
    assert mentions[1].recommendation_reason == "交通方便 招牌：窑烤意式披萨。"
