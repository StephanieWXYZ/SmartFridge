import json

from app.gemini_client import AiProviderQuotaError, refine_recipe_with_gemini


def refine_recipe(matching_result: dict[str, object]) -> dict[str, object]:
    photo = matching_result.get("photo", {})
    ingredients = photo.get("ingredients", []) if isinstance(photo, dict) else []
    recommendations = matching_result.get("recommendations", [])

    safe_ingredients = ingredients if isinstance(ingredients, list) else []
    safe_recommendations = recommendations if isinstance(recommendations, list) else []

    try:
        refined_recipe = refine_recipe_with_gemini(
            ingredients=safe_ingredients,
            recommendations=safe_recommendations,
        )
    except (json.JSONDecodeError, AiProviderQuotaError):
        refined_recipe = _fallback_recipe_from_recommendation(safe_recommendations)

    return {
        **matching_result,
        "refined_recipe": refined_recipe,
        "status": refined_recipe["status"],
    }


def _fallback_recipe_from_recommendation(recommendations: list[dict[str, object]]) -> dict[str, object]:
    top_recommendation = recommendations[0] if recommendations else {}
    recipe = top_recommendation.get("recipe", {}) if isinstance(top_recommendation, dict) else {}
    recipe = recipe if isinstance(recipe, dict) else {}

    return {
        "best_match": str(recipe.get("name", "Recommended recipe")),
        "instructions": _string_list(recipe.get("instructions")),
        "substitutions": {},
        "shopping_list": _string_list(top_recommendation.get("missing_ingredients")),
        "status": "refined",
        "source": "retrieved_recipe_fallback",
    }


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
