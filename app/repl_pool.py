from __future__ import annotations

import asyncio

from loguru import logger

from app.errors import PoolError
from app.repl import Repl
from app.settings import settings


class ReplManager:
    def __init__(
        self,
        *,
        max_repls: int = settings.MAX_REPLS,
        max_reuse: int = settings.MAX_REUSE,
        memory_gb: int = settings.REPL_MEMORY_GB,
    ) -> None:
        logger.info(
            "Initializing REPL pool with: \n\tMAX_REPLS={}, \n\tMAX_REUSE={}, \n\tREPL_MEMORY_GB={}",
            max_repls,
            max_reuse,
            memory_gb,
        )
        self.max_repls = max_repls
        self.max_reuse = max_reuse
        self.memory_gb = memory_gb
        self._pool: asyncio.Queue[Repl] = asyncio.Queue(maxsize=max_repls)

        # TODO: Find the right way to initialize pool. Can't afford to have constructor be async
        for _ in range(max_repls):
            self._pool.put_nowait(Repl(max_memory_gb=memory_gb, max_reuse=max_reuse))

    # TODO: implement initialization based on header
    # User input is a dict where key = header, value = number of REPLs

    async def get_repl(self, header: str = "") -> Repl:
        try:
            repl: Repl = self._pool.get_nowait()
            logger.info(f"Using REPL {repl.uuid.hex[:8]}")
            return repl
        except asyncio.QueueEmpty:
            logger.error(
                f"Pool is empty, total REPLs in pool: {self._pool.qsize()}, max_repls: {self.max_repls}"
            )
            raise PoolError("No available REPL")

    async def destroy_repl(self, repl: Repl) -> None:
        uuid = repl.uuid
        logger.info(f"Destroying REPL {uuid.hex[:8]}")
        await repl.close()
        del repl
        logger.info(f"Destroyed REPL {uuid.hex[:8]}")
        # Recreate a new REPL instance to maintain pool size
        await self._pool.put(
            Repl(max_memory_gb=self.memory_gb, max_reuse=self.max_reuse)
        )

    async def release_repl(self, repl: Repl) -> None:
        if repl.exhausted:
            uuid = repl.uuid
            logger.info(f"EOL for REPL {uuid.hex[:8]}")
            await repl.close()
            del repl
            logger.info(f"Deleted REPL {uuid.hex[:8]}")
            # Recreate a new REPL instance to maintain pool size
            await self._pool.put(
                Repl(max_memory_gb=self.memory_gb, max_reuse=self.max_reuse)
            )
        else:
            await self._pool.put(repl)
            logger.info(f"Returned REPL {repl.uuid.hex[:8]}")

    async def cleanup(self) -> None:
        while not self._pool.empty():
            repl = await self._pool.get()
            await repl.close()
