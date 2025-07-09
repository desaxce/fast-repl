from __future__ import annotations

import asyncio
from time import time

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
        self._lock = asyncio.Lock()
        self._free: list[Repl] = []
        self._busy: set[Repl] = set()

        for _ in range(max_repls):
            self._free.append(Repl(max_memory_gb=memory_gb, max_reuse=max_reuse))

    # TODO: implement initialization based on header where user input
    # TODO: is a dict where key = header, value = number of REPLs. Have it do `import Mathlib\nimport Aesop` by default.

    async def get_repl(self, header: str = "") -> Repl:
        """
        Async-safe way to get a `Repl` instance for a given header.
        Immediately raises an Exception if not possible.
        """
        async with self._lock:
            logger.info(
                f"[REPLs] | #free = {len(self._free)}, #busy = {len(self._busy)}"
            )
            for i, r in enumerate(self._free):
                if r.header == header:  # repl shouldn't be exhausted (max age to check)
                    repl = self._free.pop(i)
                    self._busy.add(repl)
                    logger.info(f"Using REPL {repl.uuid.hex[:8]}")
                    return repl
            total = len(self._free) + len(self._busy)

            if total < self.max_repls:
                return self._start_new(header)

            if self._free:
                oldest = min(self._free, key=lambda r: r.created_at)
                self._free.remove(oldest)
                await oldest.close()
                return self._start_new(header)

            raise PoolError("no available REPL for the given header")

    async def destroy_repl(self, repl: Repl) -> None:
        async with self._lock:
            uuid = repl.uuid
            self._busy.discard(repl)
            if repl in self._free:
                self._free.remove(repl)
            logger.info(f"Destroying REPL {uuid.hex[:8]}")
            await repl.close()
            del repl
            logger.info(f"Destroyed REPL {uuid.hex[:8]}")

    async def release_repl(self, repl: Repl) -> None:
        async with self._lock:
            if repl not in self._busy:
                logger.error(
                    f"Attempted to release a REPL that is not busy: {repl.uuid.hex[:8]}"
                )
                return

            if repl.exhausted:
                uuid = repl.uuid
                logger.info(f"REPL {uuid.hex[:8]} is exhausted, closing it")
                self._busy.discard(repl)

                await repl.close()
                del repl
                logger.info(f"Deleted REPL {uuid.hex[:8]}")
                return
            self._busy.remove(repl)
            self._free.append(repl)
            logger.info(f"Released REPL {repl.uuid.hex[:8]}")

    def _start_new(self, header: str) -> Repl:
        r = Repl(max_memory_gb=self.memory_gb, max_reuse=self.max_reuse, header=header)
        r.created_at = time()
        self._busy.add(r)
        return r

    # TODO: Implement initalization with header starts
    async def cleanup(self) -> None:
        # TODO: remove all free repls + wait on busy ones and clean as well?
        pass
