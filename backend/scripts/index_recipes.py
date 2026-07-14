import argparse
import os
from pathlib import Path

from app.recipe_indexer import index_recipes


def main() -> None:
    parser = argparse.ArgumentParser(description="Index recipe records into Pinecone.")
    parser.add_argument("dataset", type=Path, help="Path to a .csv or .jsonl recipe dataset")
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    openai_api_key = os.environ["OPENAI_API_KEY"]
    pinecone_api_key = os.environ["PINECONE_API_KEY"]
    indexed_count = index_recipes(
        dataset_path=args.dataset,
        openai_api_key=openai_api_key,
        pinecone_api_key=pinecone_api_key,
        batch_size=args.batch_size,
    )
    print(f"Indexed {indexed_count} recipes.")


if __name__ == "__main__":
    main()
