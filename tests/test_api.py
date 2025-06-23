import os

from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(".env")
os.environ["REPL_POOL_MAX_REPLS"] = "1"
os.environ["REPL_POOL_MAX_REUSE"] = "1"
os.environ["REPL_POOL_INIT_REPLS"] = "0"

import asyncio
import importlib

import pytest

from fast_repl import settings
from fast_repl.main import app


# Module scope needed to ensure tests have REPLs on same event loop.
@pytest.fixture(autouse=True, scope="module")  # type: ignore
async def client() -> TestClient:
    with TestClient(app) as c:
        yield c


@pytest.mark.asyncio  # type: ignore
async def test_repl_check_nat(client: TestClient) -> None:
    resp = client.post("/repl", json={"cmd": "#check Nat"})
    assert resp.status_code == 200

    expected = {
        "messages": [
            {
                "severity": "info",
                "pos": {"line": 1, "column": 0},
                "endPos": {"line": 1, "column": 6},
                "data": "Nat : Type",
            }
        ],
        "env": 0,
    }
    for key, value in expected.items():
        assert resp.json()[key] == value
    print("all good up to here")


@pytest.mark.asyncio  # type: ignore
async def test_repl_mathlib(client: TestClient) -> None:
    resp = client.post("/repl", json={"cmd": "import Mathlib"})
    assert resp.status_code == 200

    # Exposing the "env" at the endpoint level makes no sense.
    # Instead subsequent calls using mathlib should be fast because of caching header repls.
    # TODO: implement caching + corresponding tests.
    # resp1 = client.post("/repl", json={"cmd": "import Mathlib\ndef f := 2", "env": 0})
    # assert resp1.status_code == 200

    expected = {
        "env": 0
    }  # Env is 1 because max one repl and pool is shared by all tests.
    for key, value in expected.items():
        assert resp.json()[key] == value
    assert resp.json()["time"] < 15
    # assert resp1.json()["time"] < 1
