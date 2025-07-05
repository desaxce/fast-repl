import importlib

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from fast_repl.main import create_app
from fast_repl.settings import Settings


@pytest.fixture(
    params=[
        {"MAX_REPLS": 5, "MAX_REUSE": 10},
    ]
)  # type: ignore
def client(request):
    overrides = getattr(request, "param", {})
    s = Settings(_env_file=None)
    for k, v in overrides.items():
        setattr(s, k, v)
    app = create_app(s)
    with TestClient(app, base_url="http://testserver/api") as c:
        yield c


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--perf-rows",
        action="store",
        default=10,
        type=int,
        help="Number of proofs to run in performance benchmarks",
    )
    parser.addoption(
        "--perf-shuffle",
        action="store_true",
        default=False,
        help="Shuffle dataset rows for performance benchmarks",
    )


@pytest.fixture(scope="session")  # type: ignore
def perf_rows(request: pytest.FixtureRequest) -> int:
    return int(request.config.getoption("--perf-rows"))


@pytest.fixture(scope="session")  # type: ignore
def perf_shuffle(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--perf-shuffle"))
