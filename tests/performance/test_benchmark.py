from statistics import mean
from typing import List

import pytest
from datasets import load_dataset
from fastapi.testclient import TestClient

from fast_repl.main import app


@pytest.mark.performance
def test_proof_dataset_benchmark(perf_rows: int, perf_shuffle: bool) -> None:
    ds = load_dataset("Goedel-LM/Lean-workbook-proofs", split="train")
    if perf_shuffle:
        ds = ds.shuffle(seed=0)
    if perf_rows:
        ds = ds.select(range(perf_rows))

    times: List[float] = []
    with TestClient(app) as client:
        for item in ds:
            proof = item["full_proof"]
            resp = client.post("/repl", json={"cmd": proof})
            assert resp.status_code == 200
            data = resp.json()
            assert "time" in data
            times.append(float(data["time"]))

    print("Benchmark results for", len(times), "proofs (shuffle=" + str(perf_shuffle) + ")")
    print("min:", min(times), "max:", max(times), "mean:", mean(times))
