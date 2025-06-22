import pytest

from fast_repl.repl_pool import ReplPoolManager
from fast_repl.errors import PoolError


@pytest.mark.asyncio
async def test_pool_provides_repl() -> None:
    pool = ReplPoolManager(max_repls=1, max_reuse=1, memory_gb=1, init_repls=1)
    await pool.init_pool()
    repl = await pool.get_repl()
    assert repl is not None
    await pool.release_repl(repl)


@pytest.mark.asyncio
async def test_pool_exhausted() -> None:
    pool = ReplPoolManager(max_repls=0, max_reuse=1, memory_gb=1, init_repls=0)
    await pool.init_pool()
    with pytest.raises(PoolError):
        await pool.get_repl()
