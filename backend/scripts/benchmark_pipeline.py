import argparse
import statistics
import time
from pathlib import Path

import httpx


def benchmark_pipeline(
    api_url: str,
    image_path: Path,
    runs: int,
    poll_interval: float,
    timeout: float,
) -> list[float]:
    latencies: list[float] = []

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

            latencies.append(time.perf_counter() - started_at)

    return latencies


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SmartFridge image-to-recipe latency.")
    parser.add_argument("image", type=Path, help="Path to a fridge image to upload")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()

    latencies = benchmark_pipeline(
        api_url=args.api_url,
        image_path=args.image,
        runs=args.runs,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
    )

    print(f"Runs: {len(latencies)}")
    print(f"Average latency: {statistics.mean(latencies):.2f}s")
    print(f"Min latency: {min(latencies):.2f}s")
    print(f"Max latency: {max(latencies):.2f}s")


if __name__ == "__main__":
    main()
