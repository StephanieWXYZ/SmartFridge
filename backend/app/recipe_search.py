import os

from openai import OpenAI
from pinecone import Pinecone

from app.models import FridgeInventory, Recipe, RecipeRecommendation
from app.recommendations import recommend_recipes

PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "fridge-ai-recipes")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def search_recipes(inventory: FridgeInventory) -> list[RecipeRecommendation]:
    if not _vector_search_is_configured():
        return recommend_recipes(inventory)

    query_text = ", ".join(ingredient.name for ingredient in inventory.ingredients)
    if not query_text:
        return []

    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index = pinecone_client.Index(PINECONE_INDEX_NAME)

    embedding_response = openai_client.embeddings.create(
        input=[query_text],
        model=EMBEDDING_MODEL,
    )
    query_vector = embedding_response.data[0].embedding
    search_results = index.query(vector=query_vector, top_k=3, include_metadata=True)

    return [_recommendation_from_match(match) for match in search_results["matches"]]


def _vector_search_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") and os.getenv("PINECONE_API_KEY"))


def _recommendation_from_match(match: dict[str, object]) -> RecipeRecommendation:
    metadata = match.get("metadata", {})
    recipe = Recipe(
        name=str(metadata.get("name", "Untitled Recipe")),
        ingredients=_metadata_list(metadata.get("ingredients")),
        instructions=_metadata_list(metadata.get("steps")),
    )

    return RecipeRecommendation(
        recipe=recipe,
        matched_ingredients=[],
        missing_ingredients=[],
        score=round(float(match.get("score", 0)), 3),
    )


def _metadata_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return []
