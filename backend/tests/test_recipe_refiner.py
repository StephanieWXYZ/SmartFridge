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
