from scripts import benchmark_pipeline as benchmark_module
from scripts.benchmark_pipeline import benchmark_pipeline


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, base_url, timeout):
        self.base_url = base_url
        self.timeout = timeout
        self.status_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def post(self, path, files):
        assert path == "/fridge-photo"
        return FakeResponse({"task_id": "task-123"})

    def get(self, path):
        assert path == "/tasks/task-123"
        self.status_calls += 1
        if self.status_calls == 1:
            return FakeResponse({"status": "PENDING"})
        return FakeResponse(
            {
                "status": "SUCCESS",
                "result": {
                    "timings": {
                        "ingredient_extraction_seconds": 1,
                        "recipe_retrieval_seconds": 2,
                        "recipe_refinement_seconds": 3,
                    }
                },
            }
        )


def test_benchmark_pipeline_records_completed_task_latency(monkeypatch, tmp_path):
    image_path = tmp_path / "fridge.jpg"
    image_path.write_bytes(b"fake image bytes")
    monkeypatch.setattr(benchmark_module.httpx, "Client", FakeClient)
    monkeypatch.setattr(benchmark_module.time, "sleep", lambda seconds: None)
    timer_values = iter([0, 0.1, 1])
    monkeypatch.setattr(benchmark_module.time, "perf_counter", lambda: next(timer_values))

    results = benchmark_pipeline(
        api_url="http://testserver",
        image_path=image_path,
        runs=1,
        poll_interval=0.1,
        timeout=10,
    )

    assert len(results) == 1
    assert results[0].latency == 1
    assert results[0].status == "SUCCESS"
    assert results[0].timings["recipe_refinement_seconds"] == 3
