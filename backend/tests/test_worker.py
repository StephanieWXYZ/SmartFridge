from app.worker import extract_ingredients_task, match_recipes_task, refine_recipe_task


def test_extract_ingredients_task_returns_photo_result():
    result = extract_ingredients_task.run("fridge.jpg", "image/jpeg", b"fake image bytes".hex())

    assert result["filename"] == "fridge.jpg"
    assert result["status"] == "received"


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


def test_refine_recipe_task_marks_ai_refinement_as_pending():
    result = refine_recipe_task.run(
        {
            "photo": {"ingredients": []},
            "recommendations": [],
            "status": "matched",
        }
    )

    assert result["status"] == "refinement_pending"
    assert "AI model" in result["message"]
