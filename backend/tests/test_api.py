from fastapi.testclient import TestClient

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
