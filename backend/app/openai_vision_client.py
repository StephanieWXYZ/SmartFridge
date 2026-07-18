import base64
import json
import os
from functools import lru_cache

from openai import OpenAI

from app.models import Ingredient

OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", "gpt-4o-mini")


def extract_ingredients_with_openai(image_bytes: bytes) -> list[Ingredient]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    image_data = base64.b64encode(image_bytes).decode("ascii")
    response = _openai_client(api_key).chat.completions.create(
        model=OPENAI_VISION_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Identify food ingredients visible in this fridge or pantry photo. "
                            "Ignore containers, shelves, appliances, and non-food items. "
                            'Return only JSON like {"ingredients":["milk","eggs","spinach"]}.'
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=300,
    )
    content = response.choices[0].message.content
    parsed = json.loads(content or "{}")
    ingredient_names = parsed.get("ingredients", [])
    if not isinstance(ingredient_names, list):
        raise json.JSONDecodeError("OpenAI returned invalid ingredient data.", str(parsed), 0)

    return [Ingredient(name=str(name)) for name in ingredient_names if str(name).strip()]


@lru_cache(maxsize=4)
def _openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)
