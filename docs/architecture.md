# Architecture

SmartFridge is organized around a FastAPI gateway and a Celery background pipeline.
The API returns a task ID for image-based requests, while longer AI and retrieval work
runs in worker tasks backed by Redis.

## Request Flow

```text
Client
  -> FastAPI /fridge-photo
  -> Redis task queue
  -> Celery worker
  -> extract ingredients
  -> search recipes
  -> refine recipe
  -> Redis task result
  -> FastAPI /tasks/{task_id}
```

## Pipeline Stages

1. Ingredient extraction

   `extract_ingredients_task` receives uploaded image bytes and calls the photo analysis
   path. The Gemini client handles image-to-ingredient extraction when `GOOGLE_API_KEY`
   is configured.

2. Recipe retrieval

   `match_recipes_task` turns extracted ingredients into a recipe search request. When
   OpenAI and Pinecone keys are configured, it creates an OpenAI embedding and queries
   the Pinecone recipe index. Local fallback recommendations keep development and tests
   deterministic when external AI credentials are not configured.

3. Recipe refinement

   `refine_recipe_task` sends the extracted ingredients and retrieved recipes to the
   recipe refiner. Gemini produces the final structured recipe response when configured.

## Supporting Services

- FastAPI exposes upload, recommendation, health, and task-status endpoints.
- Redis stores Celery messages and task results.
- Celery workers run the three pipeline stages outside the request path.
- Pinecone stores recipe vectors generated from OpenAI embeddings.
- Docker Compose runs web, worker, and Redis locally.
- Terraform defines the ECS deployment for web, worker, Redis, networking, load
  balancing, and logs.

## Deployment Model

The production deployment uses separate ECS services for the FastAPI web process, Celery
worker process, and Redis. The GitHub Actions deployment workflow is manually triggered
and publishes separate Docker images for the web and worker services.
