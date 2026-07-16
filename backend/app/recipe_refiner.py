import os
from typing import Any

from app.gemini_client import refine_recipe_with_gemini

MAX_REFINEMENT_RECIPES = int(os.getenv("MAX_REFINEMENT_RECIPES", "1"))
MAX_REFINEMENT_INGREDIENTS = int(os.getenv("MAX_REFINEMENT_INGREDIENTS", "12"))
MAX_REFINEMENT_INSTRUCTION_CHARS = int(os.getenv("MAX_REFINEMENT_INSTRUCTION_CHARS", "700"))


def refine_recipe(matching_result: dict[str, object]) -> dict[str, object]:
    photo = matching_result.get("photo", {})
    ingredients = photo.get("ingredients", []) if isinstance(photo, dict) else []
    recommendations = matching_result.get("recommendations", [])

    refined_recipe = refine_recipe_with_gemini(
        ingredients=_compact_ingredients(ingredients if isinstance(ingredients, list) else []),
        recommendations=_compact_recommendations(recommendations if isinstance(recommendations, list) else []),
    )

    return {
        **matching_result,
        "refined_recipe": refined_recipe,
        "status": refined_recipe["status"],
    }


def _compact_ingredients(ingredients: list[object]) -> list[dict[str, object]]:
    compacted: list[dict[str, object]] = []
    for ingredient in ingredients:
        if isinstance(ingredient, dict) and ingredient.get("name"):
            compacted.append({"name": ingredient["name"]})
        elif hasattr(ingredient, "name"):
            compacted.append({"name": getattr(ingredient, "name")})
    return compacted


def _compact_recommendations(recommendations: list[object]) -> list[dict[str, Any]]:
    compacted: list[dict[str, Any]] = []
    for recommendation in recommendations[:MAX_REFINEMENT_RECIPES]:
        if not isinstance(recommendation, dict):
            continue

        recipe = recommendation.get("recipe", {})
        if not isinstance(recipe, dict):
            continue

        compacted.append(
            {
                "name": recipe.get("name"),
                "score": recommendation.get("score"),
                "ingredients": _limit_list(recipe.get("ingredients"), MAX_REFINEMENT_INGREDIENTS),
                "instructions": _limit_text(recipe.get("instructions"), MAX_REFINEMENT_INSTRUCTION_CHARS),
            }
        )
    return compacted


def _limit_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:limit]]


def _limit_text(value: object, max_chars: int) -> str:
    if isinstance(value, list):
        text = " ".join(str(item) for item in value)
    else:
        text = str(value or "")
    return text[:max_chars]
