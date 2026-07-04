from fastapi import FastAPI, File, UploadFile

from app.models import FridgeInventory, RecipeRecommendation
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


@app.post("/fridge-photo")
async def upload_fridge_photo(file: UploadFile = File(...)) -> dict[str, object]:
    contents = await file.read()

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size_bytes": len(contents),
        "message": "Photo upload received. Ingredient extraction will be added later.",
    }
