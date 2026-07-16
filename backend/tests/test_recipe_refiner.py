import app.recipe_refiner as refiner_module
from app.recipe_refiner import refine_recipe


def test_refine_recipe_adds_refined_result(monkeypatch):
    def fake_refine_recipe_with_gemini(ingredients, recommendations):
        assert ingredients == [{"name": "eggs"}]
        assert recommendations == [
            {
                "name": "Omelet",
                "score": None,
                "ingredients": [],
                "instructions": "",
            }
        ]
        return {
            "best_match": "Omelet",
            "instructions": ["Cook eggs."],
            "substitutions": [],
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


def test_refine_recipe_compacts_recommendations_for_ai_prompt(monkeypatch):
    captured = {}

    def fake_refine_recipe_with_gemini(ingredients, recommendations):
        captured["ingredients"] = ingredients
        captured["recommendations"] = recommendations
        return {
            "best_match": "Spinach Bake",
            "instructions": [],
            "substitutions": [],
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

    assert captured["ingredients"] == [{"name": "eggs"}]
    assert len(captured["recommendations"]) == 1
    assert captured["recommendations"][0]["name"] == "Spinach Bake"
    assert len(captured["recommendations"][0]["ingredients"]) == 12
    assert len(captured["recommendations"][0]["instructions"]) == 700
