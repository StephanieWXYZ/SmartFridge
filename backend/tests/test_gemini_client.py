import json

from app.gemini_client import (
    _extract_json_text,
    _parse_json_response,
    extract_ingredients_with_gemini,
    refine_recipe_with_gemini,
)


def test_gemini_extractor_returns_empty_list_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    ingredients = extract_ingredients_with_gemini(b"fake image bytes")

    assert ingredients == []


def test_gemini_refiner_returns_not_configured_result_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = refine_recipe_with_gemini(
        ingredients=[{"name": "eggs"}],
        recommendations=[{"recipe": {"name": "Omelet"}}],
    )

    assert result["status"] == "ai_not_configured"
    assert result["shopping_list"] == []


def test_extract_json_text_removes_markdown_and_explanatory_text():
    text = "Here is the result:\n```json\n{\"best_match\":\"Soup\"}\n```"

    assert _extract_json_text(text) == '{"best_match":"Soup"}'


def test_parse_json_response_rejects_wrong_shape():
    try:
        _parse_json_response('{"best_match":"Soup"}', list)
    except json.JSONDecodeError:
        return

    raise AssertionError("Expected JSONDecodeError")
