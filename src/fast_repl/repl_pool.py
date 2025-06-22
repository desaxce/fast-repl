from __future__ import annotations

import asyncio

from fast_repl.errors import PoolError
from fast_repl.repl import Repl
from fast_repl.settings import INIT_REPLS, MAX_REPLS, MAX_REUSE, REPL_MEMORY_GB


class ReplPoolManager:
    def __init__(
        self,
        *,
        max_repls: int = MAX_REPLS,
        max_reuse: int = MAX_REUSE,
        memory_gb: int = REPL_MEMORY_GB,
        init_repls: int = INIT_REPLS,
    ) -> None:
        self.max_repls = max_repls
        self.max_reuse = max_reuse
        self.memory_gb = memory_gb
        self.init_repls = min(init_repls, max_repls)
        self._pool: asyncio.Queue[Repl] = asyncio.Queue(maxsize=max_repls)
        self._total = 0

    async def init_pool(self) -> None:
        for _ in range(self.init_repls):
            await self._create_and_add()

    async def _create_and_add(self) -> None:
        repl = Repl(max_memory_gb=self.memory_gb, max_reuse=self.max_reuse)
        await repl.start()
        await self._pool.put(repl)
        self._total += 1

    async def get_repl(self) -> Repl:
        if self._pool.empty():
            if self._total < self.max_repls:
                await self._create_and_add()
            else:
                raise PoolError("No available REPL")
        return await self._pool.get()

    async def release_repl(self, repl: Repl) -> None:
        if repl.exhausted:
            await repl.close()
            self._total -= 1
        else:
            await self._pool.put(repl)

    async def cleanup(self) -> None:
        while not self._pool.empty():
            repl = await self._pool.get()
            await repl.close()
            self._total -= 1
        assert self._total == 0, "Pool cleanup did not empty the pool"
