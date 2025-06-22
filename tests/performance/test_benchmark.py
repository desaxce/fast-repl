from statistics import mean
from typing import List

import pytest
from datasets import load_dataset
from fastapi.testclient import TestClient
from loguru import logger

from fast_repl.main import app


@pytest.mark.performance  # type: ignore[misc]
def test_proof_dataset_benchmark(perf_rows: int, perf_shuffle: bool) -> None:
    ds = load_dataset(
        "Goedel-LM/Lean-workbook-proofs", split="train"
    )  # TODO: check which lean version is this?
    if perf_shuffle:
        ds = ds.shuffle(seed=0)
    if perf_rows:
        ds = ds.select(range(perf_rows))

    logger.info(f"Number of proofs to benchmark: {len(ds)}")
    times: List[float] = []
    with TestClient(app) as client:
        for item in ds:
            logger.info(f"Running proof: {item["problem_id"]}")
            proof = item["full_proof"]
            resp = client.post("/repl", json={"cmd": proof})
            assert resp.status_code == 200
            data = resp.json()
            assert "time" in data
            times.append(float(data["time"]))

    logger.info(
        f"Benchmark results for {len(times)} proofs (shuffle= {str(perf_shuffle)} ",
    )
    logger.info(
        f"min: {min(times):.2f} s, max: {max(times):.2f} s and mean: {mean(times):.2f} s"
    )
    assert mean(times) < 30, "Mean time for proofs should be less than 10 seconds"
