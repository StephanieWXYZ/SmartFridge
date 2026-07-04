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


def test_fridge_photo_upload_accepts_file():
    response = client.post(
        "/fridge-photo",
        files={"file": ("fridge.jpg", b"fake image bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "fridge.jpg"
    assert data["content_type"] == "image/jpeg"
    assert data["size_bytes"] == len(b"fake image bytes")
    assert data["ingredients"] == []
    assert data["status"] == "received"


def test_fridge_photo_upload_flags_non_image_files():
    response = client.post(
        "/fridge-photo",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content_type"] == "text/plain"
    assert data["status"] == "unsupported_file_type"


def test_fridge_photo_upload_flags_empty_image_files():
    response = client.post(
        "/fridge-photo",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["size_bytes"] == 0
    assert data["status"] == "empty_file"
