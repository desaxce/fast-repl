import importlib
import pytest
from dotenv import load_dotenv

from fast_repl import settings

load_dotenv(".env")
importlib.reload(settings)


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


@pytest.fixture(scope="session")
def perf_rows(request: pytest.FixtureRequest) -> int:
    return int(request.config.getoption("--perf-rows"))


@pytest.fixture(scope="session")
def perf_shuffle(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--perf-shuffle"))
