import binascii
import os
import time

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
    started_at = time.perf_counter()
    contents = binascii.unhexlify(contents_hex)
    result = analyze_fridge_photo(filename, content_type, contents)
    payload = result.model_dump()
    payload["timings"] = {"ingredient_extraction_seconds": _elapsed(started_at)}
    return payload


@celery_app.task(name="match_recipes_task")
def match_recipes_task(photo_result: dict[str, object]) -> dict[str, object]:
    started_at = time.perf_counter()
    if photo_result["status"] != "received":
        return {
            "photo": photo_result,
            "recommendations": [],
            "status": photo_result["status"],
            "timings": photo_result.get("timings", {}),
        }

    inventory = FridgeInventory.model_validate({"ingredients": photo_result["ingredients"]})
    recommendations = search_recipes(inventory)
    timings = {
        **dict(photo_result.get("timings", {})),
        "recipe_retrieval_seconds": _elapsed(started_at),
    }

    return {
        "photo": photo_result,
        "recommendations": [recommendation.model_dump() for recommendation in recommendations],
        "status": "matched",
        "timings": timings,
    }


@celery_app.task(name="refine_recipe_task")
def refine_recipe_task(matching_result: dict[str, object]) -> dict[str, object]:
    started_at = time.perf_counter()
    if matching_result["status"] != "matched":
        return matching_result

    result = refine_recipe(matching_result)
    timings = {
        **dict(matching_result.get("timings", {})),
        "recipe_refinement_seconds": _elapsed(started_at),
    }
    result["timings"] = timings
    result["timings"]["total_worker_seconds"] = round(sum(timings.values()), 3)
    return result


def _elapsed(started_at: float) -> float:
    return round(time.perf_counter() - started_at, 3)
