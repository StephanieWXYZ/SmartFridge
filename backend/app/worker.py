import binascii
import os

from celery import Celery

from app.photo_analysis import analyze_fridge_photo

celery_app = Celery(
    "smartfridge_worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)


@celery_app.task(name="analyze_fridge_photo_task")
def analyze_fridge_photo_task(
    filename: str | None,
    content_type: str | None,
    contents_hex: str,
) -> dict[str, object]:
    contents = binascii.unhexlify(contents_hex)
    result = analyze_fridge_photo(filename, content_type, contents)
    return result.model_dump()
