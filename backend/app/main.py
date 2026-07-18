import os
from pathlib import Path

from celery.result import AsyncResult
from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles

from app.models import FridgeInventory, RecipeRecommendation, TaskStatus, TaskSubmission
from app.recommendations import recommend_recipes
from app.worker import build_recipe_pipeline, celery_app

app = FastAPI(
    title="SmartFridge API",
    summary="Recipe recommendations from fridge and pantry ingredients.",
)


@app.get("/health")
@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/recommendations", response_model=list[RecipeRecommendation])
@app.post("/api/recommendations", response_model=list[RecipeRecommendation])
def create_recommendations(inventory: FridgeInventory) -> list[RecipeRecommendation]:
    return recommend_recipes(inventory)


@app.post("/fridge-photo", response_model=TaskSubmission)
@app.post("/api/fridge-photo", response_model=TaskSubmission)
async def upload_fridge_photo(file: UploadFile = File(...)) -> TaskSubmission:
    contents = await file.read()
    workflow = build_recipe_pipeline(file.filename, file.content_type, contents.hex())
    task = workflow.apply_async()
    return TaskSubmission(task_id=task.id, status="queued")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
@app.get("/api/tasks/{task_id}", response_model=TaskStatus)
def get_task_status(task_id: str) -> TaskStatus:
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.ready():
        if task_result.successful():
            return TaskStatus(task_id=task_id, status=task_result.status, result=task_result.result)

        error_code, error_message = _classify_task_error(task_result.info)
        return TaskStatus(task_id=task_id, status="FAILURE", error_code=error_code, error=error_message)

    return TaskStatus(task_id=task_id, status=task_result.status)


def _classify_task_error(error: object) -> tuple[str, str]:
    error_name = error.__class__.__name__
    error_text = str(error)
    normalized = f"{error_name} {error_text}".lower()

    if "aiproviderquotaerror" in normalized or "resource_exhausted" in normalized or "quota" in normalized:
        return (
            "AI_QUOTA_REACHED",
            "Gemini quota reached. Please wait for the quota to reset or use a different API key.",
        )

    if "jsondecodeerror" in normalized or "wrong json" in normalized or "invalid ingredient data" in normalized:
        return (
            "AI_RESPONSE_PARSE_ERROR",
            "Gemini returned a response the app could not parse. Please try again.",
        )

    if "servererror" in normalized or "503" in normalized or "unavailable" in normalized:
        return (
            "AI_PROVIDER_UNAVAILABLE",
            "The AI provider is temporarily unavailable. Please try again later.",
        )

    if "cannot identify image file" in normalized or "unidentifiedimageerror" in normalized:
        return (
            "INVALID_IMAGE",
            "The uploaded file could not be read as an image. Please choose a different photo.",
        )

    if "openai" in normalized or "pinecone" in normalized or "embedding" in normalized:
        return (
            "EXTERNAL_PROVIDER_ERROR",
            "An external AI or recipe-search provider failed. Please try again later.",
        )

    return ("TASK_FAILED", "The recipe task failed unexpectedly. Please try again.")


def _mount_frontend() -> None:
    if os.getenv("SERVE_FRONTEND", "").lower() not in {"1", "true", "yes"}:
        return

    frontend_dist = Path(__file__).resolve().parents[1] / "frontend_dist"
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


_mount_frontend()
