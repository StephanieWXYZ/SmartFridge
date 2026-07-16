import app.worker as worker_module
from app.models import Recipe, RecipeRecommendation
from app.worker import extract_ingredients_task, match_recipes_task, refine_recipe_task


def test_extract_ingredients_task_returns_photo_result():
    result = extract_ingredients_task.run("fridge.jpg", "image/jpeg", b"fake image bytes".hex())

    assert result["filename"] == "fridge.jpg"
    assert result["status"] == "received"
    assert "ingredient_extraction_seconds" in result["timings"]


def test_match_recipes_task_skips_failed_photo_analysis():
    result = match_recipes_task.run(
        {
            "filename": "notes.txt",
            "content_type": "text/plain",
            "size_bytes": 12,
            "ingredients": [],
            "status": "unsupported_file_type",
        }
    )

    assert result["recommendations"] == []
    assert result["status"] == "unsupported_file_type"
    assert result["timings"] == {}


def test_match_recipes_task_searches_with_extracted_ingredients(monkeypatch):
    calls = []

    def fake_search_recipes(inventory):
        calls.append(inventory)
        return [
            RecipeRecommendation(
                recipe=Recipe(name="Egg Bowl", ingredients=["eggs"], instructions=["Cook eggs."]),
                matched_ingredients=["eggs"],
                missing_ingredients=[],
                score=1,
            )
        ]

    monkeypatch.setattr(worker_module, "search_recipes", fake_search_recipes)

    result = match_recipes_task.run(
        {
            "filename": "fridge.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 16,
            "ingredients": [{"name": "eggs", "quantity": None}],
            "status": "received",
        }
    )

    assert calls[0].ingredients[0].name == "eggs"
    assert result["recommendations"][0]["recipe"]["name"] == "Egg Bowl"
    assert result["status"] == "matched"
    assert "recipe_retrieval_seconds" in result["timings"]


def test_refine_recipe_task_calls_refiner(monkeypatch):
    def fake_refine_recipe(matching_result):
        return {
            **matching_result,
            "refined_recipe": {"best_match": "Egg Bowl"},
            "status": "refined",
        }

    monkeypatch.setattr(worker_module, "refine_recipe", fake_refine_recipe)

    result = refine_recipe_task.run(
        {
            "photo": {"ingredients": []},
            "recommendations": [],
            "status": "matched",
        }
    )

    assert result["status"] == "refined"
    assert result["refined_recipe"]["best_match"] == "Egg Bowl"
    assert "recipe_refinement_seconds" in result["timings"]
    assert "total_worker_seconds" in result["timings"]
