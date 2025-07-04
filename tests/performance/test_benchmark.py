from __future__ import annotations

import asyncio
import os
from statistics import mean

import httpx
import pytest
from datasets import load_dataset
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from loguru import logger
from tqdm import tqdm

from fast_repl.main import app
from fast_repl.settings import settings

# TODO: print json commands and snippets nicely + pretty cat the proofs sent (replacing \n with eols)


@pytest.mark.performance  # type: ignore[misc]
@pytest.mark.asyncio  # type: ignore[misc]
async def test_proof_dataset_benchmark(perf_rows: int, perf_shuffle: bool) -> None:
    ds = load_dataset(
        "Goedel-LM/Lean-workbook-proofs", split="train"
    )  # TODO: check which lean version is this? It's 4.9
    if perf_shuffle:
        ds = ds.shuffle(seed=0)
    if perf_rows:
        ds = ds.select(range(perf_rows))

    logger.info(f"Checking {len(ds)} proofs")
    times: list[float] = []

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        logger.debug(
            f"max_repls: {settings.MAX_REPLS}, max_reuse: {settings.MAX_REUSE}"
        )
        semaphore = asyncio.Semaphore(settings.MAX_REPLS)  # limit concurrent requests

        async def run_item(item: dict[str, str]) -> None:
            async with semaphore:
                proof = item["full_proof"]
                resp = await client.post("/repl", json={"cmd": proof})
                assert resp.status_code == 200
                data = resp.json()
                assert "time" in data
                times.append(float(data["time"]))

        tasks = [
            asyncio.create_task(run_item(item))
            for item in ds
            if item["problem_id"]
            not in [
                "lean_workbook_10036",
                # "lean_workbook_1003",
            ]  # skip this one, it's too long
        ]

        for fut in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Proofs"):
            await fut
    logger.info(
        f"min: {min(times):.2f} s, max: {max(times):.2f} s and mean: {mean(times):.2f} s"
    )
    assert (
        mean(times) < 10
    ), "Mean time for proofs should be less than 10 seconds"  # max repls = 5
