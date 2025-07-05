import asyncio
import importlib
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient


@pytest.mark.asyncio  # type: ignore
async def test_repl_check_nat(client: TestClient) -> None:
    resp = client.post("check", json={"cmd": "#check Nat"})
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
    # TODO: create utility to assert JSON eq.
    for key, value in expected.items():
        assert resp.json()[key] == value


@pytest.mark.asyncio  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "client",
    [
        {"MAX_REPLS": 1, "MAX_REUSE": 2},
    ],
    indirect=True,
)
async def test_repl_mathlib(client: TestClient) -> None:
    resp = client.post("check", json={"cmd": "import Mathlib"})
    assert resp.status_code == 200

    expected = {
        "env": 0
    }  # Env is 0 because max one repl and pool is shared by all tests.

    for key, value in expected.items():
        assert resp.json()[key] == value
    assert resp.json()["time"] < 15

    # Exposing the "env" at the endpoint level makes no sense.
    # Instead subsequent calls using mathlib should be fast because of caching header repls.
    # TODO: implement caching + corresponding tests.
    resp1 = client.post("check", json={"cmd": "import Mathlib\ndef f := 2", "env": 0})
    assert resp1.status_code == 200
    expected = {
        "env": 1
    }  # Env is 1 because max one repl and pool is shared by all tests.

    for key, value in expected.items():
        assert resp1.json()[key] == value
    assert resp1.json()["time"] < 15
    assert resp1.json()["time"] < 1


@pytest.mark.asyncio  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "client",
    [
        {"MAX_REPLS": 1, "MAX_REUSE": 2},
    ],
    indirect=True,
)
async def test_repl_timeout(client: TestClient) -> None:
    # TODO: we need to ensure same REPL used twice, so max_repls = 1 and max_reuse >=2
    # TODO: add option which says which REPL tackled validation.
    resp = client.post("check", json={"cmd": "import Mathlib"}, params={"timeout": 1})
    assert resp.status_code == 500
    assert "timed out" in resp.json()["detail"]

    await asyncio.sleep(5)  # 5 seconds should be enough to load Mathlib
    resp = client.post(
        "check",
        json={"cmd": "theorem one_plus_one : 1 + 1 = 2 := by rfl"},
        timeout=5,
    )
    assert resp.status_code == 200
    # TODO: assert same repl used - probably not actually, since the first timedout.
    # But should assert that only max_repl = 1 and that it's reusable >=1
    expected = {
        "messages": [
            {
                "severity": "info",
                "pos": {"line": 1, "column": 0},
                "endPos": {"line": 1, "column": 42},
                "data": "Goals accomplished!",
            }
        ],
        "env": 0,
        # "time": 0.4508490000007441,
        # "cpu_max": 0.0,
    }
    # TODO: make json comparison here
    for key, value in expected.items():
        assert resp.json()[key] == value
