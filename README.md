# SmartFridge
> AI-Powered Fridge-to-Recipe Recommendation System

## Backend

The backend is a FastAPI app. To run it locally:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Once it is running, the API docs are available at:

```text
http://127.0.0.1:8000/docs
```

The first recommendation endpoint accepts ingredients and returns matching recipe ideas.

## Docker

To run the API, worker, and Redis together:

```bash
cd backend
docker compose up --build
```

The web service runs on `http://127.0.0.1:8000`.
