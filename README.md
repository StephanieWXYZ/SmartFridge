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
