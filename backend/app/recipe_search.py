import ast
import json
import os
import re
from functools import lru_cache

from openai import OpenAI
from pinecone import Pinecone

from app.models import FridgeInventory, Recipe, RecipeRecommendation
from app.recommendations import recommend_recipes

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "fridge-ai-recipes")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
RECIPE_MATCH_COUNT = int(os.getenv("RECIPE_MATCH_COUNT", "4"))
RECIPE_CANDIDATE_COUNT = int(os.getenv("RECIPE_CANDIDATE_COUNT", "12"))


def search_recipes(inventory: FridgeInventory) -> list[RecipeRecommendation]:
    if not _vector_search_is_configured():
        return recommend_recipes(inventory)

    query_text = ", ".join(ingredient.name for ingredient in inventory.ingredients)
    if not query_text:
        return []

    openai_client = _openai_client(os.environ["OPENAI_API_KEY"])
    index = _pinecone_index(os.environ["PINECONE_API_KEY"], PINECONE_INDEX_NAME)

    embedding_response = openai_client.embeddings.create(
        input=[query_text],
        model=EMBEDDING_MODEL,
    )
    query_vector = embedding_response.data[0].embedding
    search_results = index.query(vector=query_vector, top_k=RECIPE_CANDIDATE_COUNT, include_metadata=True)

    recommendations = [_recommendation_from_match(match, inventory) for match in search_results["matches"]]
    display_ready = [
        recommendation for recommendation in recommendations if _is_display_ready(recommendation)
    ]
    return (display_ready or recommendations)[:RECIPE_MATCH_COUNT]


def _vector_search_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") and os.getenv("PINECONE_API_KEY"))


@lru_cache(maxsize=4)
def _openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


@lru_cache(maxsize=8)
def _pinecone_index(api_key: str, index_name: str):
    return Pinecone(api_key=api_key).Index(index_name)


def _recommendation_from_match(match: dict[str, object], inventory: FridgeInventory) -> RecipeRecommendation:
    metadata = match.get("metadata", {})
    recipe = Recipe(
        name=_clean_recipe_name(metadata.get("name", "Untitled Recipe")),
        ingredients=_metadata_list(metadata.get("ingredients")),
        instructions=_normalize_steps(_metadata_list(metadata.get("steps"))),
    )
    available = {_normalize_ingredient(ingredient.name) for ingredient in inventory.ingredients}
    required = {_normalize_ingredient(ingredient) for ingredient in recipe.ingredients}
    matched = sorted(ingredient for ingredient in required if _has_available_match(ingredient, available))

    return RecipeRecommendation(
        recipe=recipe,
        matched_ingredients=matched,
        missing_ingredients=sorted(required - set(matched)),
        score=round(float(match.get("score", 0)), 3),
    )


def _metadata_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [_clean_metadata_item(item) for item in value if _clean_metadata_item(item)]

    if isinstance(value, str):
        parsed = _parse_list_string(value)
        if parsed is not None:
            return [_clean_metadata_item(item) for item in parsed if _clean_metadata_item(item)]
        return [_clean_metadata_item(item) for item in value.split(",") if _clean_metadata_item(item)]

    return []


def _parse_list_string(value: str) -> list[object] | None:
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(value)
        except (SyntaxError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(parsed, list):
            return parsed
    return None


def _clean_metadata_item(value: object) -> str:
    return str(value).strip().strip("\"'[] ")


def _clean_recipe_name(value: object) -> str:
    return re.sub(r"\s+", " ", _clean_metadata_item(value)).strip()


def _normalize_steps(steps: list[str]) -> list[str]:
    normalized: list[str] = []
    pending: list[str] = []

    for step in steps:
        clean_step = _clean_metadata_item(step)
        if not clean_step:
            continue
        pending.append(clean_step)
        pending_text = ", ".join(pending)
        if len(pending_text) >= 28 or clean_step.endswith((".", "!", "?")):
            normalized.append(pending_text)
            pending = []

    if pending:
        if normalized and len(", ".join(pending)) < 18:
            normalized[-1] = f"{normalized[-1]}, {', '.join(pending)}"
        else:
            normalized.append(", ".join(pending))

    return normalized


def _is_display_ready(recommendation: RecipeRecommendation) -> bool:
    recipe = recommendation.recipe
    meaningful_steps = [step for step in recipe.instructions if len(step) >= 20]
    return (
        _has_readable_title(recipe.name)
        and len(recipe.ingredients) >= 3
        and len(recipe.instructions) >= 3
        and len(meaningful_steps) >= 3
    )


def _has_readable_title(title: str) -> bool:
    return len(title) >= 4 and not re.search(r"[a-z]\d|\d[a-z]", title.lower())


def _normalize_ingredient(value: str) -> str:
    normalized = re.sub(r"\b(fresh|raw|sliced|diced|chopped|minced|small|large)\b", "", value.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized.endswith("ies"):
        return f"{normalized[:-3]}y"
    if normalized.endswith("oes"):
        return normalized[:-2]
    if normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def _has_available_match(required_ingredient: str, available: set[str]) -> bool:
    return any(
        required_ingredient == ingredient
        or required_ingredient in ingredient
        or ingredient in required_ingredient
        for ingredient in available
    )
