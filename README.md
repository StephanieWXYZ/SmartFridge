# SmartFridge
> AI-Powered Fridge-to-Recipe Recommendation System

[![Backend CI](https://github.com/StephanieWXYZ/SmartFridge/actions/workflows/ci.yml/badge.svg)](https://github.com/StephanieWXYZ/SmartFridge/actions/workflows/ci.yml)

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

## CI

GitHub Actions runs backend linting, tests, and a Docker image build on pushes and pull
requests to `main`.

## Infrastructure

Terraform files in `backend/terraform` define the AWS ECS deployment for the FastAPI web
service, Celery worker, Redis service, load balancer, networking, and logs.

## Deployment

The deployment workflow builds separate web and worker Docker images, pushes them to
Amazon ECR, and forces the ECS web and worker services to redeploy.

## Recipe Indexing

The `backend/scripts/index_recipes.py` script indexes a CSV or JSONL recipe dataset into
Pinecone using OpenAI ingredient embeddings. It is intended for one-time dataset setup,
not automatic CI or deployment.

```bash
cd backend
OPENAI_API_KEY=... PINECONE_API_KEY=... python scripts/index_recipes.py path/to/recipes.jsonl
```

## Benchmarking

The `backend/scripts/benchmark_pipeline.py` script measures end-to-end latency for the
photo upload, Celery pipeline, recipe search, and refinement flow. Run this only after
the API, worker, Redis, and required AI service keys are configured.

```bash
cd backend
python scripts/benchmark_pipeline.py path/to/fridge.jpg --runs 5
```
