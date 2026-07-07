from app.gemini_client import extract_ingredients_with_gemini


def test_gemini_extractor_returns_empty_list_without_api_key(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    ingredients = extract_ingredients_with_gemini(b"fake image bytes")

    assert ingredients == []
