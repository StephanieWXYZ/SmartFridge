from app.models import FridgeInventory, Ingredient, Recipe, RecipeRecommendation
from app.recipe_search import (
    _is_display_ready,
    _metadata_list,
    _normalize_ingredient,
    _normalize_steps,
    _recommendation_from_match,
    search_recipes,
)


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


def test_recommendation_from_match_computes_missing_ingredients():
    recommendation = _recommendation_from_match(
        {
            "score": 0.92,
            "metadata": {
                "name": "Veggie Omelet",
                "ingredients": ["eggs", "spinach", "cheese"],
                "steps": ["Whisk eggs.", "Cook in a pan."],
            },
        },
        FridgeInventory(ingredients=[Ingredient(name="eggs"), Ingredient(name="spinach")]),
    )

    assert recommendation.matched_ingredients == ["egg", "spinach"]
    assert recommendation.missing_ingredients == ["cheese"]


def test_metadata_list_parses_json_array_strings():
    assert _metadata_list('["eggs", "spinach"]') == ["eggs", "spinach"]


def test_metadata_list_parses_python_array_strings():
    assert _metadata_list("['garlic', 'natural-style peanut butter', 'soy sauce']") == [
        "garlic",
        "natural-style peanut butter",
        "soy sauce",
    ]
    assert _metadata_list("['mince the garlic in a food processor', 'add peanut butter']") == [
        "mince the garlic in a food processor",
        "add peanut butter",
    ]


def test_recommendation_from_match_cleans_title_and_step_fragments():
    recommendation = _recommendation_from_match(
        {
            "score": 0.8,
            "metadata": {
                "name": "  sesame   noodles  ",
                "ingredients": "['garlic', 'soy sauce', 'spaghetti']",
                "steps": "['mince the garlic in a food processor', 'add peanut butter', 'soy sauce', 'sugar']",
            },
        },
        FridgeInventory(ingredients=[Ingredient(name="garlic")]),
    )

    assert recommendation.recipe.name == "sesame noodles"
    assert recommendation.recipe.ingredients == ["garlic", "soy sauce", "spaghetti"]
    assert recommendation.recipe.instructions == [
        "mince the garlic in a food processor",
        "add peanut butter, soy sauce, sugar",
    ]


def test_normalize_steps_merges_short_fragments():
    assert _normalize_steps(["cook", "drain", "and crumble bacon", "layer salad ingredients"]) == [
        "cook, drain, and crumble bacon",
        "layer salad ingredients",
    ]


def test_normalize_ingredient_removes_common_descriptors_and_singularizes():
    assert _normalize_ingredient("fresh tomatoes") == "tomato"
    assert _normalize_ingredient("sliced mushrooms") == "mushroom"
    assert _normalize_ingredient("berries") == "berry"
    assert _normalize_ingredient("green peppers") == "green pepper"


def test_display_ready_rejects_messy_dataset_titles():
    recommendation = RecipeRecommendation(
        recipe=Recipe(
            name="tasty s the power of flower7 salad",
            ingredients=["spinach", "pepper", "peas"],
            instructions=[
                "place the spinach on a platter",
                "arrange the peppers around the spinach",
                "serve the salad after chilling",
            ],
        ),
        score=0.7,
    )

    assert not _is_display_ready(recommendation)
