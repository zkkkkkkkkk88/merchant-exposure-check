import pytest

from app.analysis.contracts import ExtractedMention, ExtractionPayload
from app.analysis.extractor import extract_target_mention, validate_extraction


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
