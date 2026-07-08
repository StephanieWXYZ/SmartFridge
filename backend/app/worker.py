import binascii
import os

from celery import Celery, chain

from app.models import FridgeInventory
from app.photo_analysis import analyze_fridge_photo
from app.recipe_search import search_recipes
from app.recipe_refiner import refine_recipe

celery_app = Celery(
    "smartfridge_worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)


def build_recipe_pipeline(filename: str | None, content_type: str | None, contents_hex: str):
    return chain(
        extract_ingredients_task.s(filename, content_type, contents_hex),
        match_recipes_task.s(),
        refine_recipe_task.s(),
    )


@celery_app.task(name="extract_ingredients_task")
def extract_ingredients_task(
    filename: str | None,
    content_type: str | None,
    contents_hex: str,
) -> dict[str, object]:
    contents = binascii.unhexlify(contents_hex)
    result = analyze_fridge_photo(filename, content_type, contents)
    return result.model_dump()


@celery_app.task(name="match_recipes_task")
def match_recipes_task(photo_result: dict[str, object]) -> dict[str, object]:
    if photo_result["status"] != "received":
        return {
            "photo": photo_result,
            "recommendations": [],
            "status": photo_result["status"],
        }

    inventory = FridgeInventory.model_validate({"ingredients": photo_result["ingredients"]})
    recommendations = search_recipes(inventory)

    return {
        "photo": photo_result,
        "recommendations": [recommendation.model_dump() for recommendation in recommendations],
        "status": "matched",
    }


@celery_app.task(name="refine_recipe_task")
def refine_recipe_task(matching_result: dict[str, object]) -> dict[str, object]:
    if matching_result["status"] != "matched":
        return matching_result

    return refine_recipe(matching_result)
