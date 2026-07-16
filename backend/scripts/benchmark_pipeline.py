import argparse
import statistics
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass
class BenchmarkRun:
    latency: float
    status: str
    error: str | None = None
    timings: dict[str, float] | None = None


def benchmark_pipeline(
    api_url: str,
    image_path: Path,
    runs: int,
    poll_interval: float,
    timeout: float,
) -> list[BenchmarkRun]:
    results: list[BenchmarkRun] = []

    with httpx.Client(base_url=api_url, timeout=timeout) as client:
        for _ in range(runs):
            started_at = time.perf_counter()
            with image_path.open("rb") as image_file:
                response = client.post(
                    "/fridge-photo",
                    files={"file": (image_path.name, image_file, "image/jpeg")},
                )
            response.raise_for_status()
            task_id = response.json()["task_id"]

            while True:
                status_response = client.get(f"/tasks/{task_id}")
                status_response.raise_for_status()
                payload = status_response.json()
                if payload["status"] in {"SUCCESS", "FAILURE"}:
                    break
                if time.perf_counter() - started_at > timeout:
                    raise TimeoutError(f"Task {task_id} did not finish within {timeout} seconds.")
                time.sleep(poll_interval)

            result = payload.get("result") or {}
            results.append(
                BenchmarkRun(
                    latency=time.perf_counter() - started_at,
                    status=payload["status"],
                    error=payload.get("error"),
                    timings=result.get("timings") if isinstance(result, dict) else None,
                )
            )

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SmartFridge image-to-recipe latency.")
    parser.add_argument("image", type=Path, help="Path to a fridge image to upload")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()

    results = benchmark_pipeline(
        api_url=args.api_url,
        image_path=args.image,
        runs=args.runs,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )

    successful_runs = [result for result in results if result.status == "SUCCESS"]
    failed_runs = [result for result in results if result.status == "FAILURE"]

    print(f"Runs attempted: {len(results)}")
    print(f"Successful runs: {len(successful_runs)}")
    print(f"Failed runs: {len(failed_runs)}")

    if successful_runs:
        successful_latencies = [result.latency for result in successful_runs]
        print(f"Average successful latency: {statistics.mean(successful_latencies):.2f}s")
        print(f"Min successful latency: {min(successful_latencies):.2f}s")
        print(f"Max successful latency: {max(successful_latencies):.2f}s")

        timing_keys = sorted(
            {
                key
                for result in successful_runs
                for key in (result.timings or {})
            }
        )
        for key in timing_keys:
            values = [
                result.timings[key]
                for result in successful_runs
                if result.timings and key in result.timings
            ]
            print(f"Average {key}: {statistics.mean(values):.2f}s")

    for index, result in enumerate(failed_runs, start=1):
        print(f"Failure {index}: {result.error or 'unknown error'}")


if __name__ == "__main__":
    main()
