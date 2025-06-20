from typing import AsyncGenerator

import pytest

from fast_repl.repl import Repl


@pytest.fixture  # type: ignore
async def repl() -> AsyncGenerator[Repl, None]:
    repl_instance = Repl()
    yield repl_instance
    await repl_instance.close()


@pytest.mark.asyncio  # type: ignore
async def test_start(repl: Repl) -> None:
    assert repl.proc is None

    await repl.start()

    assert repl.proc is not None
