import pytest

from app.errors import NoAvailableReplError
from app.manager import Manager


@pytest.mark.asyncio  # type: ignore
async def test_get_repl() -> None:
    manager = Manager(max_repls=1, max_uses=1)

    repl = await manager.get_repl()

    assert repl is not None

    await manager.release_repl(repl)


@pytest.mark.asyncio  # type: ignore
async def test_exhausted() -> None:
    manager = Manager(max_repls=0, max_uses=1)

    with pytest.raises(NoAvailableReplError):
        await manager.get_repl()
