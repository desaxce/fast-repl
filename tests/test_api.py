import asyncio
import importlib
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from loguru import logger
from starlette import status
from utils import assert_json_equal

from app.schemas import CheckRequest


@pytest.mark.asyncio  # type: ignore
async def test_repl_check_nat(client: TestClient) -> None:
    payload = CheckRequest(
        snippets=[{"id": "1", "code": "#check Nat"}],
    ).model_dump()
    resp = client.post("check", json=payload)
    assert resp.status_code == status.HTTP_200_OK

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
        {
            "MAX_REPLS": 1,
            "MAX_USES": 3,
        },  # bumped max_uses to 3 because now header makes age increment
    ],
    indirect=True,
)
async def test_repl_mathlib(client: TestClient) -> None:
    payload = CheckRequest(
        snippets=[{"id": "1", "code": "import Mathlib\ndef f := 1"}],
        debug=True,  # Enable debug to see diagnostics
    ).model_dump()
    resp = client.post("check", json=payload)
    assert resp.status_code == status.HTTP_200_OK

    expected = {"env": 1}  # Env is 1 because initialization with header bumps env value

    assert_json_equal(resp.json(), expected, ignore_keys=["time", "diagnostics"])
    assert resp.json()["time"] < 15

    payload = CheckRequest(
        snippets=[{"id": "1", "code": "import Mathlib\ndef f := 2"}],
        debug=True,
    ).model_dump()
    resp1 = client.post("check", json=payload)
    assert resp1.status_code == status.HTTP_200_OK
    expected = {
        "env": 2
    }  # Env is 2 because max one repl and pool is shared by all tests.

    assert_json_equal(resp1.json(), expected, ignore_keys=["time", "diagnostics"])

    assert resp1.json()["time"] < 1


@pytest.mark.asyncio  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "client",
    [
        {"MAX_REPLS": 1, "MAX_USES": 2},
    ],
    indirect=True,
)
# @pytest.mark.skip(reason="Need to wait till header-based repls cache implemented")
async def test_repl_timeout(client: TestClient) -> None:
    # TODO: we need to ensure same REPL used twice, so max_repls = 1 and max_uses >=2
    # TODO: add option which says which REPL tackled validation.

    payload = CheckRequest(
        snippets=[{"id": "1", "code": "import Mathlib"}],
        timeout=1,  # Set a short timeout to trigger a timeout error
    ).model_dump()
    try:
        resp = client.post("check", json=payload)
    except Exception as e:
        logger.info(f"Error during request: {e}")
        logger.info(resp.status_code)
    assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    logger.info(resp.json())

    assert "timed out" in resp.json()["detail"]

    await asyncio.sleep(5)  # 5 seconds should be enough to load Mathlib
    payload = CheckRequest(
        snippets=[{"id": "1", "code": "theorem one_plus_one : 1 + 1 = 2 := by rfl"}],
        timeout=5,
    ).model_dump()
    resp = client.post("check", json=payload)
    assert resp.status_code == status.HTTP_200_OK
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
        "time": 0.450849,
    }
    assert_json_equal(resp.json(), expected, ignore_keys=["time", "diagnostics"])


@pytest.mark.asyncio  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "client",
    [
        {"MAX_REPLS": 1, "MAX_USES": 3},
    ],
    indirect=True,  # todo: what does this do
)
async def test_repl_exhausted(client: TestClient) -> None:
    payload = CheckRequest(
        snippets=[{"id": "1", "code": "#check Nat"}], debug=True
    ).model_dump()

    try:
        resp = client.post("check", json=payload)
    except Exception as e:
        logger.info(f"Error during request: {e}")
        logger.info(resp.status_code)
        raise

    repl_uuid = resp.json()["diagnostics"]["repl_uuid"]

    payload = CheckRequest(
        snippets=[{"id": "2", "code": "#check 0"}], debug=True
    ).model_dump()

    try:
        resp = client.post("check", json=payload)
    except Exception as e:
        logger.info(f"Error during request: {e}")
        logger.info(resp.status_code)
        raise

    assert repl_uuid == resp.json()["diagnostics"]["repl_uuid"]

    payload = CheckRequest(
        snippets=[{"id": "2", "code": "#check 1"}], debug=True
    ).model_dump()

    try:
        resp = client.post("check", json=payload)
    except Exception as e:
        logger.info(f"Error during request: {e}")
        logger.info(resp.status_code)
        raise

    assert repl_uuid == resp.json()["diagnostics"]["repl_uuid"]

    payload = CheckRequest(
        snippets=[{"id": "3", "code": "#check 2"}], debug=True
    ).model_dump()

    try:
        resp = client.post("check", json=payload)
    except Exception as e:
        logger.info(f"Error during request: {e}")
        logger.info(resp.status_code)
        raise

    assert repl_uuid != resp.json()["diagnostics"]["repl_uuid"]
