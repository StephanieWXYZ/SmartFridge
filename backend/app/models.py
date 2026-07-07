from typing import Any, Literal

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


class PhotoAnalysisResult(BaseModel):
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int = Field(..., ge=0)
    ingredients: list[Ingredient] = Field(default_factory=list)
    status: Literal["received", "unsupported_file_type", "empty_file"]


class TaskSubmission(BaseModel):
    task_id: str
    status: Literal["queued"]


class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None
