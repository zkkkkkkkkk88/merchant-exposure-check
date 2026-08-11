import re
from collections.abc import Collection, Sequence

from app.analysis.contracts import ExtractedMention, ExtractionPayload


def validate_extraction(
    payload: ExtractionPayload,
    allowed_citation_urls: Collection[str],
) -> ExtractionPayload:
    allowed = set(allowed_citation_urls)
    referenced = {
        url
        for item in [*payload.mentions, *payload.facts]
        for url in item.citation_urls
    }
    invented = referenced - allowed
    if invented:
        raise ValueError("Extraction citation URL is not present in saved result")
    return payload


def extract_target_mention(
    raw_text: str,
    target_names: Sequence[str],
) -> ExtractionPayload:
    ordered_names = sorted(
        {name.strip() for name in target_names if name.strip()},
        key=len,
        reverse=True,
    )
    matched_name = next(
        (name for name in ordered_names if name.casefold() in raw_text.casefold()),
        None,
    )
    if matched_name is None:
        return ExtractionPayload(
            is_valid=bool(raw_text.strip()),
            has_explicit_ranking=False,
            confidence=0.7 if raw_text.strip() else 0.0,
        )

    position_match = re.search(
        rf"(?im)^\s*(\d+)[.、)]\s*{re.escape(matched_name)}",
        raw_text,
    )
    position = int(position_match.group(1)) if position_match else None
    negative_recommendation = re.search(
        r"(?:暂不|不建议|不予|未被|没有).{0,6}(?:推荐|选择)",
        raw_text,
    )
    positive_recommendation = position is not None or bool(
        re.search(r"(?:推荐|适合|值得|首选)", raw_text)
    )
    return ExtractionPayload(
        is_valid=True,
        has_explicit_ranking=position is not None,
        is_recommended=positive_recommendation and negative_recommendation is None,
        confidence=0.85,
        mentions=[
            ExtractedMention(
                raw_name=matched_name,
                position=position,
                confidence=0.85,
            )
        ],
    )
