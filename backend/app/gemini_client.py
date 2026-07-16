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


class RefinedRecipeResponse(BaseModel):
    best_match: str | None = None
    instructions: list[str] = Field(default_factory=list, max_length=3)
    substitutions: list[str] = Field(default_factory=list, max_length=3)
    shopping_list: list[str] = Field(default_factory=list, max_length=5)


def extract_ingredients_with_gemini(image_bytes: bytes) -> list[Ingredient]:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return []

    image = Image.open(io.BytesIO(image_bytes))
    prompt = """
    Identify all food ingredients in this fridge or pantry photo.
    Return only a JSON list of ingredient names.
    Example: ["milk", "eggs", "spinach"]
    """

    ingredient_names = _generate_json(
        contents=[prompt, image],
        expected_type=list,
        max_output_tokens=256,
    )

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
            "substitutions": [],
            "shopping_list": [],
            "status": "ai_not_configured",
        }

    prompt = f"""
    You are a helpful chef. The user has these fridge ingredients:
    {ingredients}

    These are the strongest recipe matches from the recipe index:
    {recommendations}

    Create a concise recipe plan using the highest-scored match. Keep the response short:
    no more than 3 instruction steps, no more than 3 substitutions, and no more than
    5 shopping-list items. Keep each string under 80 characters.

    Return JSON with:
    {{
        "best_match": "Recipe title",
        "instructions": ["step 1", "step 2"],
        "substitutions": ["use substitute instead of original"],
        "shopping_list": ["item"]
    }}

    Return only valid JSON. Do not include markdown fences or explanatory text.
    """

    result = _generate_json(
        contents=prompt,
        expected_type=dict,
        max_output_tokens=2048,
        response_schema=RefinedRecipeResponse,
    )
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
