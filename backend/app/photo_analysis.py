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

    return PhotoAnalysisResult(
        filename=filename,
        content_type=content_type,
        size_bytes=len(contents),
        status="received",
    )
