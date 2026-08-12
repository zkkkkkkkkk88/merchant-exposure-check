import re
from collections.abc import Collection, Sequence

from app.analysis.contracts import ExtractedMention, ExtractionPayload
from app.analysis.normalization import normalize_brand_name

_RANKED_ENTRY = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*)?\s*(\d{1,2})[.、)]\s*(.+?)\s*$"
)


def extract_ranked_mentions(raw_text: str) -> list[ExtractedMention]:
    """Extract explicit ranked entities without guessing from prose or citations."""
    mentions: list[ExtractedMention] = []
    seen: set[str] = set()
    matches = list(_RANKED_ENTRY.finditer(raw_text))
    for index, match in enumerate(matches):
        heading = match.group(2).strip().strip("*# ")
        heading_parts = re.split(r"[：:]|\s+[—–-]\s+", heading, maxsplit=1)
        candidate = heading_parts[0]
        candidate = re.sub(r"\s*[（(][^）)]*(?:店|杭州|商场|门店)[^）)]*[）)]\s*$", "", candidate)
        candidate = candidate.strip().strip("*# ")
        normalized = normalize_brand_name(candidate)
        if not normalized or normalized in seen or len(candidate) > 200:
            continue
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(raw_text)
        section = raw_text[match.end():section_end]
        section = re.split(r"(?m)^\s*#{1,6}\s+", section, maxsplit=1)[0]
        reason_parts = [heading_parts[1].strip()] if len(heading_parts) == 2 else []
        reason_parts.extend(
            cleaned
            for line in section.splitlines()
            if (cleaned := line.strip().strip("*-# "))
        )
        reason = " ".join(reason_parts)[:1000] or None
        seen.add(normalized)
        mentions.append(
            ExtractedMention(
                raw_name=candidate,
                position=int(match.group(1)),
                recommendation_reason=reason,
                confidence=0.82,
            )
        )
    return mentions


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
