from app.models import FridgeInventory, Recipe, RecipeRecommendation


STARTER_RECIPES = [
    Recipe(
        name="Spinach Omelet",
        ingredients=["eggs", "spinach", "milk", "cheese"],
        instructions=[
            "Whisk eggs with milk.",
            "Add spinach and cheese.",
            "Cook in a skillet until the eggs are set.",
        ],
    ),
    Recipe(
        name="Tomato Pasta",
        ingredients=["pasta", "tomato", "garlic", "olive oil"],
        instructions=[
            "Boil the pasta.",
            "Warm tomato, garlic, and olive oil in a pan.",
            "Toss the pasta with the sauce.",
        ],
    ),
]


def recommend_recipes(inventory: FridgeInventory) -> list[RecipeRecommendation]:
    available = {ingredient.name.strip().lower() for ingredient in inventory.ingredients}
    recommendations: list[RecipeRecommendation] = []

    for recipe in STARTER_RECIPES:
        required = {ingredient.lower() for ingredient in recipe.ingredients}
        matched = sorted(required & available)
        missing = sorted(required - available)
        score = len(matched) / len(required)

        recommendations.append(
            RecipeRecommendation(
                recipe=recipe,
                matched_ingredients=matched,
                missing_ingredients=missing,
                score=round(score, 2),
            )
        )

    return sorted(recommendations, key=lambda recommendation: recommendation.score, reverse=True)
