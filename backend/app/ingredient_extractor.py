from app.models import Ingredient
from app.gemini_client import extract_ingredients_with_gemini


def extract_ingredients_from_photo(contents: bytes) -> list[Ingredient]:
    if not contents:
        return []

    return extract_ingredients_with_gemini(contents)
