import app.ingredient_extractor as extractor_module
from app.ingredient_extractor import extract_ingredients_from_photo
from app.models import Ingredient


def test_extract_ingredients_returns_empty_list_without_image_bytes():
    ingredients = extract_ingredients_from_photo(b"")

    assert ingredients == []


def test_extract_ingredients_uses_gemini_client(monkeypatch):
    def fake_extract_ingredients_with_gemini(contents):
        assert contents == b"fake image bytes"
        return [Ingredient(name="eggs")]

    monkeypatch.setattr(
        extractor_module,
        "extract_ingredients_with_gemini",
        fake_extract_ingredients_with_gemini,
    )

    ingredients = extract_ingredients_from_photo(b"fake image bytes")

    assert ingredients == [Ingredient(name="eggs")]
