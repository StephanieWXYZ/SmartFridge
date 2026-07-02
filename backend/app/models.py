from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    name: str = Field(..., min_length=1, examples=["eggs"])
    quantity: str | None = Field(default=None, examples=["1 carton"])


class FridgeInventory(BaseModel):
    ingredients: list[Ingredient] = Field(default_factory=list)


class Recipe(BaseModel):
    name: str = Field(..., min_length=1, examples=["Spinach Omelet"])
    ingredients: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)


class RecipeRecommendation(BaseModel):
    recipe: Recipe
    matched_ingredients: list[str] = Field(default_factory=list)
    missing_ingredients: list[str] = Field(default_factory=list)
    score: float = Field(..., ge=0, le=1)
