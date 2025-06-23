from __future__ import annotations

import asyncio

from loguru import logger

from fast_repl.errors import PoolError
from fast_repl.repl import Repl
from fast_repl.settings import settings


class ReplPoolManager:
    def __init__(
        self,
        *,
        max_repls: int = settings.MAX_REPLS,
        max_reuse: int = settings.MAX_REUSE,
        memory_gb: int = settings.REPL_MEMORY_GB,
    ) -> None:
        logger.info(
            "Initializing REPL pool with max_repls={}, max_reuse={}, memory_gb={}",
            max_repls,
            max_reuse,
            memory_gb,
        )
        self.max_repls = max_repls
        self.max_reuse = max_reuse
        self.memory_gb = memory_gb
        self._pool: asyncio.Queue[Repl] = asyncio.Queue(maxsize=max_repls)
        for _ in range(max_repls):
            self._pool.put_nowait(Repl(max_memory_gb=memory_gb, max_reuse=max_reuse))

    # TODO: implement initialization based on header
    # User input is a dict where key = header, value = number of REPLs
    # async def init_pool(self) -> None:
    #     for _ in range(self.init_repls):
    #         await self._create_and_add()
    #     logger.info("REPL pool initialized with %d instances", self.init_repls)

    # async def _create_and_add(self) -> None:
    #     async with self._lock:
    #         if self._total >= self.max_repls:
    #             logger.warning(
    #                 "Attempted to create a REPL instance but the pool is full"
    #             )
    #             return
    #         repl = Repl(max_memory_gb=self.memory_gb, max_reuse=self.max_reuse)
    #         await repl.start()
    #         self._pool.append(repl)
    #         self._total += 1
    #         logger.debug(f"Created a new REPL instance: {repl.uuid}")

    # async def get_repl(self) -> Repl:
    #     logger.debug("Requesting a REPL instance from the pool")
    #     if self._pool.empty():
    #         logger.info(
    #             f"TOTAL REPLs in pool: {self._total}, max_repls: {self.max_repls}"
    #         )
    #         if self._total < self.max_repls:
    #             await self._create_and_add()
    #         else:
    #             raise PoolError("No available REPL")
    #     repl: Repl = await self._pool.get()
    #     logger.debug(f"Acquired a REPL instance: {repl.uuid}")
    #     return repl

    async def get_repl(self) -> Repl:
        try:
            repl: Repl = self._pool.get_nowait()
            logger.info(f"Using REPL {repl.uuid.hex[:8]}")
            return repl
        except asyncio.QueueEmpty:
            logger.error(
                f"Pool is empty, total REPLs in pool: {self._pool.qsize()}, max_repls: {self.max_repls}"
            )
            raise PoolError("No available REPL")

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
