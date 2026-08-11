import re
import unicodedata

_CJK = "\u3400-\u4dbf\u4e00-\u9fff"


def normalize_brand_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = normalized.replace("’", "'").replace("‘", "'").replace("`", "'")
    normalized = re.sub(r"[^\w\s'\u3400-\u4dbf\u4e00-\u9fff]", "", normalized)
    normalized = " ".join(normalized.split())
    normalized = re.sub(rf"(?<=[{_CJK}])\s+|\s+(?=[{_CJK}])", "", normalized)
    return normalized
