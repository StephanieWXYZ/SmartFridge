from app.models import FridgeInventory, Ingredient
from app.recipe_search import search_recipes


def test_recipe_search_uses_local_fallback_without_api_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)

    recommendations = search_recipes(
        FridgeInventory(
            ingredients=[
                Ingredient(name="eggs"),
                Ingredient(name="spinach"),
                Ingredient(name="milk"),
            ]
        )
    )

    assert recommendations[0].recipe.name == "Spinach Omelet"
