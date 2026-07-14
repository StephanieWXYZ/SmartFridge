import json

from app.recipe_indexer import iter_batches, load_recipe_records, recipe_text


def test_load_recipe_records_from_jsonl(tmp_path):
    dataset = tmp_path / "recipes.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "1",
                "name": "Omelet",
                "ingredients": ["eggs", "milk"],
                "steps": ["Whisk.", "Cook."],
            }
        )
    )

    records = load_recipe_records(dataset)

    assert records == [
        {
            "id": "1",
            "name": "Omelet",
            "ingredients": ["eggs", "milk"],
            "steps": ["Whisk.", "Cook."],
        }
    ]


def test_load_recipe_records_from_csv(tmp_path):
    dataset = tmp_path / "recipes.csv"
    dataset.write_text("recipe_id,title,ingredients,instructions\n42,Pasta,\"pasta,tomato\",Boil\n")

    records = load_recipe_records(dataset)

    assert records[0]["id"] == "42"
    assert records[0]["name"] == "Pasta"
    assert records[0]["ingredients"] == ["pasta", "tomato"]
    assert records[0]["steps"] == ["Boil"]


def test_recipe_text_joins_ingredients():
    text = recipe_text({"name": "Omelet", "ingredients": ["eggs", "milk"]})

    assert text == "Omelet: eggs, milk"


def test_iter_batches_splits_records():
    records = [{"id": index} for index in range(5)]

    batches = list(iter_batches(records, batch_size=2))

    assert batches == [[{"id": 0}, {"id": 1}], [{"id": 2}, {"id": 3}], [{"id": 4}]]
