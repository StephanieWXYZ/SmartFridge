import json

import app.recipe_refiner as refiner_module
from app.recipe_refiner import refine_recipe


def test_refine_recipe_adds_refined_result(monkeypatch):
    def fake_refine_recipe_with_gemini(ingredients, recommendations):
        assert ingredients == [{"name": "eggs"}]
        assert recommendations == [{"recipe": {"name": "Omelet"}}]
        return {
            "best_match": "Omelet",
            "instructions": ["Cook eggs."],
            "substitutions": {},
            "shopping_list": [],
            "status": "refined",
        }

    monkeypatch.setattr(
        refiner_module,
        "refine_recipe_with_gemini",
        fake_refine_recipe_with_gemini,
    )

    result = refine_recipe(
        {
            "photo": {"ingredients": [{"name": "eggs"}]},
            "recommendations": [{"recipe": {"name": "Omelet"}}],
            "status": "matched",
        }
    )

    assert result["status"] == "refined"
    assert result["refined_recipe"]["best_match"] == "Omelet"


def test_refine_recipe_sends_full_context_to_ai_prompt(monkeypatch):
    captured = {}

    def fake_refine_recipe_with_gemini(ingredients, recommendations):
        captured["ingredients"] = ingredients
        captured["recommendations"] = recommendations
        return {
            "best_match": "Spinach Bake",
            "instructions": [],
            "substitutions": {},
            "shopping_list": [],
            "status": "refined",
        }

    monkeypatch.setattr(
        refiner_module,
        "refine_recipe_with_gemini",
        fake_refine_recipe_with_gemini,
    )

    refine_recipe(
        {
            "photo": {"ingredients": [{"name": "eggs", "quantity": "2"}]},
            "recommendations": [
                {
                    "recipe": {
                        "name": "Spinach Bake",
                        "ingredients": [f"ingredient-{index}" for index in range(20)],
                        "instructions": ["step " * 500],
                    },
                    "score": 0.91,
                },
                {
                    "recipe": {"name": "Second Recipe"},
                    "score": 0.8,
                },
            ],
            "status": "matched",
        }
    )

    assert captured["ingredients"] == [{"name": "eggs", "quantity": "2"}]
    assert len(captured["recommendations"]) == 2
    assert captured["recommendations"][0]["recipe"]["name"] == "Spinach Bake"
    assert len(captured["recommendations"][0]["recipe"]["ingredients"]) == 20
    assert captured["recommendations"][0]["recipe"]["instructions"] == ["step " * 500]


def test_refine_recipe_falls_back_when_ai_returns_bad_json(monkeypatch):
    def fake_refine_recipe_with_gemini(ingredients, recommendations):
        raise json.JSONDecodeError("bad response", "{", 0)

    monkeypatch.setattr(
        refiner_module,
        "refine_recipe_with_gemini",
        fake_refine_recipe_with_gemini,
    )

    result = refine_recipe(
        {
            "photo": {"ingredients": [{"name": "eggs"}]},
            "recommendations": [
                {
                    "recipe": {
                        "name": "Veggie Omelet",
                        "instructions": ["Whisk eggs.", "Cook vegetables.", "Fold together."],
                    },
                    "missing_ingredients": ["olive oil"],
                }
            ],
            "status": "matched",
        }
    )

    assert result["status"] == "refined"
    assert result["refined_recipe"]["best_match"] == "Veggie Omelet"
    assert result["refined_recipe"]["instructions"] == ["Whisk eggs.", "Cook vegetables.", "Fold together."]
    assert result["refined_recipe"]["shopping_list"] == ["olive oil"]
    assert result["refined_recipe"]["source"] == "retrieved_recipe_fallback"
