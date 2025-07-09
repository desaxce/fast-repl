from __future__ import annotations

import asyncio
import json
import os
from pprint import pformat
from statistics import mean

import httpx
import pytest
from datasets import load_dataset
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient, Limits
from loguru import logger
from tqdm import tqdm

from app.main import app
from app.schemas import CheckRequest
from app.settings import settings


@pytest.mark.perfs  # type: ignore[misc]
@pytest.mark.asyncio  # type: ignore[misc]
async def test_goedel(perf_rows: int, perf_shuffle: bool) -> None:
    ds = load_dataset(
        "Goedel-LM/Lean-workbook-proofs", split="train"
    )  # Goedel is on v4.9.0, some proofs aren't valid in later versions.
    if perf_shuffle:
        ds = ds.shuffle(seed=0)
    if perf_rows:
        ds = ds.select(range(perf_rows))

    logger.info(f"Checking {len(ds)} proofs")
    times: list[float] = []

    # TODO: Create real perf tests not using ASGI transport
    # limits = Limits(max_connections=settings.MAX_REPLS, max_keepalive_connections=5)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver/api",
        # limits=limits,
    ) as client:
        logger.info(settings.BASE)
        logger.debug(f"MAX_REPLS: {settings.MAX_REPLS}\nMAX_USES: {settings.MAX_USES}")
        semaphore = asyncio.Semaphore(
            settings.MAX_REPLS
        )  # limit concurrent requests don't use this semaphore just llilmit in async client

        async def run_item(item: dict[str, str]) -> None:
            async with semaphore:
                proof = item["full_proof"]
                payload = CheckRequest(
                    snippets=[{"id": item["problem_id"], "code": proof}],
                    timeout=30,
                ).model_dump()
                resp = await client.post("check", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                logger.info(json.dumps(data, indent=2))
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
