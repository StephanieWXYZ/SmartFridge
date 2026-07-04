from app.ingredient_extractor import extract_ingredients_from_photo
from app.models import PhotoAnalysisResult


def analyze_fridge_photo(
    filename: str | None,
    content_type: str | None,
    contents: bytes,
) -> PhotoAnalysisResult:
    if content_type is None or not content_type.startswith("image/"):
        return PhotoAnalysisResult(
            filename=filename,
            content_type=content_type,
            size_bytes=len(contents),
            status="unsupported_file_type",
        )

    if not contents:
        return PhotoAnalysisResult(
            filename=filename,
            content_type=content_type,
            size_bytes=0,
            status="empty_file",
        )

    ingredients = extract_ingredients_from_photo(contents)

    return PhotoAnalysisResult(
        filename=filename,
        content_type=content_type,
        size_bytes=len(contents),
        ingredients=ingredients,
        status="received",
    )
