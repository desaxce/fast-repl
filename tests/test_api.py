from dotenv import load_dotenv
from fastapi.testclient import TestClient

load_dotenv("../.env")

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

        resp1 = client.post(
            "/repl", json={"cmd": "import Mathlib\ndef f := 2", "env": 0}
        )
        assert resp1.status_code == 200

    expected = {"env": 0}
    for key, value in expected.items():
        assert resp.json()[key] == value

    assert resp.json()["time"] < 15
    assert resp1.json()["time"] < 1
