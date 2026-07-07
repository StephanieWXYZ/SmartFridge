import io
import json
import os

from google import genai
from PIL import Image

from app.models import Ingredient


def extract_ingredients_with_gemini(image_bytes: bytes) -> list[Ingredient]:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return []

    image = Image.open(io.BytesIO(image_bytes))
    client = genai.Client(api_key=api_key)
    prompt = """
    Identify all food ingredients in this fridge or pantry photo.
    Return only a JSON list of ingredient names.
    Example: ["milk", "eggs", "spinach"]
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image],
    )
    clean_json = response.text.replace("```json", "").replace("```", "").strip()
    ingredient_names = json.loads(clean_json)

    return [Ingredient(name=name) for name in ingredient_names]
