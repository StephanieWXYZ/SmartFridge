from app.models import Ingredient


def extract_ingredients_from_photo(contents: bytes) -> list[Ingredient]:
    if not contents:
        return []

    return []
