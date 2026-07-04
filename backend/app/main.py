from fastapi import FastAPI

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
