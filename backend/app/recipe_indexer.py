import csv
import json
from collections.abc import Iterable
from pathlib import Path

from openai import OpenAI
from pinecone import Pinecone

from app.recipe_search import EMBEDDING_MODEL, PINECONE_INDEX_NAME


def load_recipe_records(path: Path) -> list[dict[str, object]]:
    if path.suffix == ".jsonl":
        return [_normalize_recipe(json.loads(line)) for line in path.read_text().splitlines() if line]

    if path.suffix == ".csv":
        with path.open(newline="") as file:
            return [_normalize_recipe(row) for row in csv.DictReader(file)]

    raise ValueError("Recipe dataset must be a .csv or .jsonl file.")


def recipe_text(recipe: dict[str, object]) -> str:
    ingredients = recipe.get("ingredients", [])
    if isinstance(ingredients, list):
        ingredient_text = ", ".join(str(ingredient) for ingredient in ingredients)
    else:
        ingredient_text = str(ingredients)

    return f"{recipe['name']}: {ingredient_text}"


def iter_batches(records: list[dict[str, object]], batch_size: int) -> Iterable[list[dict[str, object]]]:
    for index in range(0, len(records), batch_size):
        yield records[index : index + batch_size]


def index_recipes(
    dataset_path: Path,
    openai_api_key: str,
    pinecone_api_key: str,
    index_name: str = PINECONE_INDEX_NAME,
    embedding_model: str = EMBEDDING_MODEL,
    batch_size: int = 100,
) -> int:
    records = load_recipe_records(dataset_path)
    openai_client = OpenAI(api_key=openai_api_key)
    pinecone_client = Pinecone(api_key=pinecone_api_key)
    index = pinecone_client.Index(index_name)

    indexed_count = 0
    for batch in iter_batches(records, batch_size):
        embedding_response = openai_client.embeddings.create(
            input=[recipe_text(recipe) for recipe in batch],
            model=embedding_model,
        )
        vectors = [
            {
                "id": str(recipe["id"]),
                "values": embedding.embedding,
                "metadata": {
                    "name": recipe["name"],
                    "ingredients": recipe["ingredients"],
                    "steps": recipe["steps"],
                },
            }
            for recipe, embedding in zip(batch, embedding_response.data, strict=True)
        ]
        index.upsert(vectors=vectors)
        indexed_count += len(vectors)

    return indexed_count


def _normalize_recipe(row: dict[str, object]) -> dict[str, object]:
    recipe_id = row.get("id") or row.get("recipe_id") or row.get("name")
    name = str(row.get("name") or row.get("title") or "Untitled Recipe")
    ingredients = _coerce_list(row.get("ingredients"))
    steps = _coerce_list(row.get("steps") or row.get("instructions"))

    return {
        "id": recipe_id,
        "name": name,
        "ingredients": ingredients,
        "steps": steps,
    }


def _coerce_list(value: object) -> list[str]:
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass

    return [item.strip() for item in text.split(",") if item.strip()]
