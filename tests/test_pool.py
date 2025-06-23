import pytest

from fast_repl.errors import PoolError
from fast_repl.repl_pool import ReplPoolManager


@pytest.mark.asyncio  # type: ignore
async def test_pool_provides_repl() -> None:
    pool = ReplPoolManager(max_repls=1, max_reuse=1, memory_gb=1)
    repl = await pool.get_repl()
    assert repl is not None
    await pool.release_repl(repl)


@pytest.mark.asyncio  # type: ignore
async def test_pool_exhausted() -> None:
    pool = ReplPoolManager(
        max_repls=0, max_reuse=1, memory_gb=1
    )  # TODO: init with custom headers
    with pytest.raises(PoolError):
        await pool.get_repl()
