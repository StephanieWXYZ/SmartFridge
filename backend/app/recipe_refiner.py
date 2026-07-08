from app.gemini_client import refine_recipe_with_gemini


def refine_recipe(matching_result: dict[str, object]) -> dict[str, object]:
    photo = matching_result.get("photo", {})
    ingredients = photo.get("ingredients", []) if isinstance(photo, dict) else []
    recommendations = matching_result.get("recommendations", [])

    refined_recipe = refine_recipe_with_gemini(
        ingredients=ingredients if isinstance(ingredients, list) else [],
        recommendations=recommendations if isinstance(recommendations, list) else [],
    )

    return {
        **matching_result,
        "refined_recipe": refined_recipe,
        "status": refined_recipe["status"],
    }
