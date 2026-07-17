from fastapi.testclient import TestClient

import app.main as main_module
from app.main import _classify_task_error, app


client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_recommendations_return_best_match_first():
    response = client.post(
        "/recommendations",
        json={
            "ingredients": [
                {"name": "eggs"},
                {"name": "spinach"},
                {"name": "milk"},
            ]
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data[0]["recipe"]["name"] == "Spinach Omelet"
    assert data[0]["matched_ingredients"] == ["eggs", "milk", "spinach"]
    assert data[0]["missing_ingredients"] == ["cheese"]


class FakeTask:
    id = "task-123"


def test_fridge_photo_upload_queues_background_task(monkeypatch):
    calls = []

    class FakePipeline:
        def apply_async(self):
            calls.append("apply_async")
            return FakeTask()

    def fake_build_recipe_pipeline(filename, content_type, contents_hex):
        calls.append((filename, content_type, contents_hex))
        return FakePipeline()

    monkeypatch.setattr(main_module, "build_recipe_pipeline", fake_build_recipe_pipeline)

    response = client.post(
        "/fridge-photo",
        files={"file": ("fridge.jpg", b"fake image bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {"task_id": "task-123", "status": "queued"}
    assert calls == [("fridge.jpg", "image/jpeg", b"fake image bytes".hex()), "apply_async"]


def test_task_error_classifier_names_quota_errors():
    error_code, message = _classify_task_error(RuntimeError("429 RESOURCE_EXHAUSTED quota exceeded"))

    assert error_code == "AI_QUOTA_REACHED"
    assert "Gemini quota reached" in message


def test_task_error_classifier_names_parse_errors():
    error_code, message = _classify_task_error(ValueError("Gemini returned invalid ingredient data."))

    assert error_code == "AI_RESPONSE_PARSE_ERROR"
    assert "could not parse" in message


def test_task_error_classifier_names_unknown_errors():
    error_code, message = _classify_task_error(RuntimeError("something surprising"))

    assert error_code == "TASK_FAILED"
    assert "unexpectedly" in message
