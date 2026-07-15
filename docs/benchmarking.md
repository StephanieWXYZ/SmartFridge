# Benchmarking

SmartFridge includes a benchmark script for measuring the complete image-to-recipe
workflow. The benchmark starts when a fridge image is uploaded and ends when the Celery
pipeline reports a terminal task status.

## Measured Path

The benchmark covers:

- `POST /fridge-photo` upload latency
- Celery task creation
- ingredient extraction
- recipe retrieval
- recipe refinement
- task polling through `GET /tasks/{task_id}`

## Requirements

Run the benchmark with the API, worker, Redis, and external AI services configured.
The benchmark should use the same image sample and run count when comparing different
pipeline versions.

Required services:

- FastAPI backend
- Celery worker
- Redis broker and result backend
- Gemini API key for image extraction and recipe refinement
- OpenAI API key for embeddings
- Pinecone index containing recipe vectors

## Command

```bash
cd backend
python scripts/benchmark_pipeline.py path/to/fridge.jpg --runs 5
```

The script prints the number of runs, average latency, minimum latency, and maximum
latency.

## Reporting Results

Report benchmark results only after running the script against a configured environment.
Include the image sample, run count, and average latency so the result is reproducible.
