import pytest

from app.analysis.normalization import normalize_brand_name


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("O'eat Gastronomy（杭州万象城店）", "o'eat gastronomy杭州万象城店"),
        (" O’EAT   Gastronomy ", "o'eat gastronomy"),
        ("欧逸 O'eat", "欧逸o'eat"),
    ],
)
def test_normalize_brand_name(raw: str, expected: str) -> None:
    assert normalize_brand_name(raw) == expected
