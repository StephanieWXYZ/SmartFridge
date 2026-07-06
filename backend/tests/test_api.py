from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


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

    def fake_delay(filename, content_type, contents_hex):
        calls.append((filename, content_type, contents_hex))
        return FakeTask()

    monkeypatch.setattr(main_module.analyze_fridge_photo_task, "delay", fake_delay)

    response = client.post(
        "/fridge-photo",
        files={"file": ("fridge.jpg", b"fake image bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {"task_id": "task-123", "status": "queued"}
    assert calls == [("fridge.jpg", "image/jpeg", b"fake image bytes".hex())]
