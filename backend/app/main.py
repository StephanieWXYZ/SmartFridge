from celery.result import AsyncResult
from fastapi import FastAPI, File, UploadFile

from app.models import FridgeInventory, RecipeRecommendation, TaskStatus, TaskSubmission
from app.recommendations import recommend_recipes
from app.worker import build_recipe_pipeline, celery_app

app = FastAPI(
    title="SmartFridge API",
    summary="Recipe recommendations from fridge and pantry ingredients.",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/recommendations", response_model=list[RecipeRecommendation])
def create_recommendations(inventory: FridgeInventory) -> list[RecipeRecommendation]:
    return recommend_recipes(inventory)


@app.post("/fridge-photo", response_model=TaskSubmission)
async def upload_fridge_photo(file: UploadFile = File(...)) -> TaskSubmission:
    contents = await file.read()
    workflow = build_recipe_pipeline(file.filename, file.content_type, contents.hex())
    task = workflow.apply_async()
    return TaskSubmission(task_id=task.id, status="queued")


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task_status(task_id: str) -> TaskStatus:
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.ready():
        if task_result.successful():
            return TaskStatus(task_id=task_id, status=task_result.status, result=task_result.result)

        return TaskStatus(task_id=task_id, status="FAILURE", error=str(task_result.info))

    return TaskStatus(task_id=task_id, status=task_result.status)
