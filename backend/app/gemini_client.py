import io
import json
import os
import time
from functools import lru_cache
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field

from app.models import Ingredient

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_GEMINI_ATTEMPTS = int(os.getenv("GEMINI_MAX_ATTEMPTS", "3"))


class AiProviderQuotaError(RuntimeError):
    pass


class RecipeSubstitution(BaseModel):
    original: str
    substitute: str


class RefinedRecipeResponse(BaseModel):
    best_match: str | None = None
    instructions: list[str] = Field(default_factory=list)
    substitutions: list[RecipeSubstitution] = Field(default_factory=list)
    shopping_list: list[str] = Field(default_factory=list)


class IngredientExtractionResponse(BaseModel):
    ingredients: list[str] = Field(default_factory=list)


def extract_ingredients_with_gemini(image_bytes: bytes) -> list[Ingredient]:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return []

    image = Image.open(io.BytesIO(image_bytes))
    prompt = """
    Identify all food ingredients in this fridge or pantry photo.
    Return only food ingredient names. Ignore containers, appliances, shelves,
    and non-food items.

    Return JSON with:
    {
        "ingredients": ["milk", "eggs", "spinach"]
    }
    """

    result = _generate_json(
        contents=[prompt, image],
        expected_type=dict,
        max_output_tokens=256,
        response_schema=IngredientExtractionResponse,
    )
    ingredient_names = result.get("ingredients", [])
    if not isinstance(ingredient_names, list):
        raise json.JSONDecodeError("Gemini returned invalid ingredient data.", str(result), 0)

    return [Ingredient(name=name) for name in ingredient_names]


def refine_recipe_with_gemini(
    ingredients: list[dict[str, object]],
    recommendations: list[dict[str, object]],
) -> dict[str, object]:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
            "best_match": None,
            "instructions": [],
            "substitutions": {},
            "shopping_list": [],
            "status": "ai_not_configured",
        }

    prompt = f"""
    You are a helpful chef. The user has these ingredients:
    {ingredients}

    These recipes were retrieved from the recipe index:
    {recommendations}

    Select the best recipe, suggest substitutions from the user's ingredients,
    and list only the missing items they still need to buy.

    Return JSON with:
    {{
        "best_match": "Recipe title",
        "instructions": ["step 1", "step 2"],
        "substitutions": [
            {{"original": "missing or recipe ingredient", "substitute": "available ingredient"}}
        ],
        "shopping_list": ["item"]
    }}

    Return only valid JSON. Do not include markdown fences or explanatory text.
    """

    result = _generate_json(
        contents=prompt,
        expected_type=dict,
        max_output_tokens=4096,
        response_schema=RefinedRecipeResponse,
    )
    result["substitutions"] = _substitution_list_to_dict(result.get("substitutions", []))
    result["status"] = "refined"
    return result


@lru_cache(maxsize=4)
def _gemini_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def _generate_json(
    contents: object,
    expected_type: type,
    max_output_tokens: int,
    response_schema: type[BaseModel] | None = None,
) -> Any:
    api_key = os.environ["GOOGLE_API_KEY"]
    client = _gemini_client(api_key)
    last_error: Exception | None = None

    for attempt in range(1, MAX_GEMINI_ATTEMPTS + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=max_output_tokens,
                    response_schema=response_schema,
                ),
            )
            parsed_response = getattr(response, "parsed", None)
            if parsed_response is not None:
                return _coerce_parsed_response(parsed_response, expected_type)
            return _parse_json_response(response.text, expected_type)
        except genai_errors.ClientError as error:
            if getattr(error, "code", None) == 429 or "RESOURCE_EXHAUSTED" in str(error):
                raise AiProviderQuotaError(
                    "Gemini quota reached. Please wait for the quota to reset or use a different API key."
                ) from error
            raise
        except (json.JSONDecodeError, genai_errors.ServerError) as error:
            last_error = error
            if attempt == MAX_GEMINI_ATTEMPTS:
                raise
            time.sleep(0.5 * attempt)

    if last_error is not None:
        raise last_error
    raise RuntimeError("Gemini did not return a response.")


def _parse_json_response(text: str, expected_type: type) -> Any:
    clean_json = _extract_json_text(text)
    parsed = json.loads(clean_json)
    if not isinstance(parsed, expected_type):
        raise json.JSONDecodeError("Gemini returned the wrong JSON shape.", clean_json, 0)
    return parsed


def _coerce_parsed_response(parsed_response: object, expected_type: type) -> Any:
    if isinstance(parsed_response, BaseModel):
        parsed_response = parsed_response.model_dump()
    if not isinstance(parsed_response, expected_type):
        raise json.JSONDecodeError("Gemini returned the wrong parsed shape.", str(parsed_response), 0)
    return parsed_response


def _substitution_list_to_dict(substitutions: object) -> dict[str, str]:
    if isinstance(substitutions, dict):
        return {str(original): str(substitute) for original, substitute in substitutions.items()}
    if not isinstance(substitutions, list):
        return {}

    substitution_map: dict[str, str] = {}
    for substitution in substitutions:
        if not isinstance(substitution, dict):
            continue
        original = substitution.get("original")
        substitute = substitution.get("substitute")
        if original and substitute:
            substitution_map[str(original)] = str(substitute)
    return substitution_map


def _extract_json_text(text: str) -> str:
    stripped = text.replace("```json", "").replace("```", "").strip()
    object_start = stripped.find("{")
    array_start = stripped.find("[")
    starts = [index for index in (object_start, array_start) if index != -1]
    if not starts:
        return stripped

    start = min(starts)
    end = max(stripped.rfind("}"), stripped.rfind("]"))
    if end == -1 or end < start:
        return stripped
    return stripped[start : end + 1]
