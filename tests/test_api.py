import os
from pathlib import Path

from fastapi.testclient import TestClient

os.environ["BASE"] = str(Path(__file__).resolve().parent.parent)

from fast_repl.main import app


def test_repl_check_nat() -> None:
    with TestClient(app) as client:
        resp = client.post("/repl/", json={"cmd": "#check Nat"})
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
