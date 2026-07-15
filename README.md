# SmartFridge
> AI-Powered Fridge-to-Recipe Recommendation System

[![Backend CI](https://github.com/StephanieWXYZ/SmartFridge/actions/workflows/ci.yml/badge.svg)](https://github.com/StephanieWXYZ/SmartFridge/actions/workflows/ci.yml)

## Backend

SmartFridge uses a FastAPI backend, Celery worker, Redis queue, and AI-powered recipe
retrieval pipeline to turn fridge photos or ingredient lists into recipe
recommendations.

Key backend capabilities:

- async image-to-recipe workflow with FastAPI, Celery, and Redis
- 3-stage pipeline for ingredient extraction, recipe retrieval, and recipe refinement
- OpenAI embeddings with Pinecone vector search for recipe matching
- Docker Compose for local web, worker, and Redis services
- Terraform and GitHub Actions for AWS ECS deployment

See [SmartFridge Architecture](docs/architecture.md) for the backend pipeline and
deployment layout.

## Local Development

To run the API locally:

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

## Environment

Copy `backend/.env.example` to `backend/.env` and provide service credentials for the
AI-backed workflow.

```bash
cd backend
cp .env.example .env
```

The backend supports deterministic local tests without external AI credentials. Full
image-to-recipe generation uses:

- `GOOGLE_API_KEY` for Gemini ingredient extraction and recipe refinement
- `OPENAI_API_KEY` for ingredient embeddings
- `PINECONE_API_KEY` and `PINECONE_INDEX_NAME` for recipe vector search
- `REDIS_URL` for Celery task queue and results

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

See [Deployment](docs/deployment.md) for the required cloud setup and release steps.

## Recipe Indexing

The `backend/scripts/index_recipes.py` script indexes a CSV or JSONL recipe dataset into
Pinecone using OpenAI ingredient embeddings.

```bash
cd backend
OPENAI_API_KEY=... PINECONE_API_KEY=... python scripts/index_recipes.py path/to/recipes.jsonl
```

## Benchmarking

The `backend/scripts/benchmark_pipeline.py` script measures end-to-end latency for the
photo upload, Celery pipeline, recipe search, and refinement flow.

```bash
cd backend
python scripts/benchmark_pipeline.py path/to/fridge.jpg --runs 5
```

See [Benchmarking](docs/benchmarking.md) for the measurement workflow.
