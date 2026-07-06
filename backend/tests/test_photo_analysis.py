from app.photo_analysis import analyze_fridge_photo


def test_photo_analysis_accepts_image_files():
    result = analyze_fridge_photo("fridge.jpg", "image/jpeg", b"fake image bytes")

    assert result.filename == "fridge.jpg"
    assert result.content_type == "image/jpeg"
    assert result.size_bytes == len(b"fake image bytes")
    assert result.ingredients == []
    assert result.status == "received"


def test_photo_analysis_flags_non_image_files():
    result = analyze_fridge_photo("notes.txt", "text/plain", b"not an image")

    assert result.content_type == "text/plain"
    assert result.status == "unsupported_file_type"


def test_photo_analysis_flags_empty_image_files():
    result = analyze_fridge_photo("empty.jpg", "image/jpeg", b"")

    assert result.size_bytes == 0
    assert result.status == "empty_file"
