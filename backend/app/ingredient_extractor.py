import json

from google.genai import errors as genai_errors

from app.gemini_client import AiProviderQuotaError, extract_ingredients_with_gemini
from app.models import Ingredient
from app.openai_vision_client import extract_ingredients_with_openai


def extract_ingredients_from_photo(contents: bytes) -> list[Ingredient]:
    if not contents:
        return []

    try:
        return extract_ingredients_with_gemini(contents)
    except (json.JSONDecodeError, AiProviderQuotaError, genai_errors.ServerError):
        openai_ingredients = extract_ingredients_with_openai(contents)
        if openai_ingredients:
            return openai_ingredients
        raise
