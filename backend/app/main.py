from fastapi import FastAPI, File, UploadFile

from app.models import FridgeInventory, PhotoAnalysisResult, RecipeRecommendation
from app.photo_analysis import analyze_fridge_photo
from app.recommendations import recommend_recipes

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


@app.post("/fridge-photo", response_model=PhotoAnalysisResult)
async def upload_fridge_photo(file: UploadFile = File(...)) -> PhotoAnalysisResult:
    contents = await file.read()
    return analyze_fridge_photo(file.filename, file.content_type, contents)
