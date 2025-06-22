import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv(".env")
os.environ["REPL_POOL_MAX_REPLS"] = "1"
os.environ["REPL_POOL_MAX_REUSE"] = "1"
os.environ["REPL_POOL_INIT_REPLS"] = "0"

import importlib

from fast_repl import settings

importlib.reload(settings)
from fast_repl.main import app


def test_repl_check_nat() -> None:
    with TestClient(app) as client:
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


def test_repl_mathlib() -> None:
    with TestClient(app) as client:
        resp = client.post("/repl", json={"cmd": "import Mathlib"})
        assert resp.status_code == 200
    with TestClient(app) as client:
        resp1 = client.post(
            "/repl", json={"cmd": "import Mathlib\ndef f := 2", "env": 0}
        )
        assert resp1.status_code == 200

    expected = {"env": 0}
    for key, value in expected.items():
        assert resp.json()[key] == value

    assert resp.json()["time"] < 15
    assert resp1.json()["time"] < 1
