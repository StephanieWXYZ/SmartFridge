import json

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


def test_extract_ingredients_falls_back_to_openai_when_gemini_returns_bad_json(monkeypatch):
    calls = []

    def fake_extract_ingredients_with_gemini(contents):
        calls.append(("gemini", contents))
        raise json.JSONDecodeError("bad response", "", 0)

    def fake_extract_ingredients_with_openai(contents):
        calls.append(("openai", contents))
        return [Ingredient(name="milk")]

    monkeypatch.setattr(
        extractor_module,
        "extract_ingredients_with_gemini",
        fake_extract_ingredients_with_gemini,
    )
    monkeypatch.setattr(
        extractor_module,
        "extract_ingredients_with_openai",
        fake_extract_ingredients_with_openai,
    )

    ingredients = extract_ingredients_from_photo(b"fake image bytes")

    assert ingredients == [Ingredient(name="milk")]
    assert calls == [("gemini", b"fake image bytes"), ("openai", b"fake image bytes")]
