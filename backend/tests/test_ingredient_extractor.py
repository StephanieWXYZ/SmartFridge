from app.ingredient_extractor import extract_ingredients_from_photo


def test_extract_ingredients_returns_empty_list_until_ai_is_connected():
    ingredients = extract_ingredients_from_photo(b"fake image bytes")

    assert ingredients == []
