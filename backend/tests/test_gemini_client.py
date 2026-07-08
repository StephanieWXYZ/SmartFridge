from app.gemini_client import extract_ingredients_with_gemini, refine_recipe_with_gemini


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
