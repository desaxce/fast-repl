from __future__ import annotations

import asyncio
import json
from time import time

from loguru import logger

from app.errors import NoAvailableReplError, ReplError
from app.repl import Repl
from app.schemas import CheckResponse, Snippet
from app.settings import settings
from app.utils import is_blank


class Manager:
    def __init__(
        self,
        *,
        max_repls: int = settings.MAX_REPLS,
        max_uses: int = settings.MAX_USES,
        max_mem: int = settings.MAX_MEM,
    ) -> None:

        self.max_repls = max_repls
        self.max_uses = max_uses
        self.max_mem = max_mem
        self._lock = asyncio.Lock()
        self._free: list[Repl] = []
        self._busy: set[Repl] = set()

        for _ in range(max_repls):
            self._free.append(Repl(max_mem=max_mem, max_uses=max_uses))

        logger.info(
            "[Manager] Initialized with: \n  MAX_REPLS={},\n  MAX_USES={},\n  MAX_MEM={} MB",
            max_repls,
            max_uses,
            max_mem,
        )

    async def initialize_repls(self) -> None:
        if self.max_repls < sum(settings.INIT_REPLS.values()):
            raise ValueError(
                f"Cannot initialize REPLs: Σ (INIT_REPLS values) = {sum(settings.INIT_REPLS.values())} > {self.max_repls} = MAX_REPLS"
            )
        initialized_repls: list[Repl] = []
        for header, count in settings.INIT_REPLS.items():
            for _ in range(count):
                initialized_repls.append(await self.get_repl(header=header))

        async def _prep_and_release(repl: Repl) -> None:
            await self.prep(repl, snippet_id="init", timeout=5, debug=False)
            await self.release_repl(repl)

        await asyncio.gather(*(_prep_and_release(r) for r in initialized_repls))

        logger.info(
            f"Initialized REPLs with: {json.dumps(settings.INIT_REPLS, indent=2)}"
        )

    async def get_repl(self, header: str = "", snippet_id: str = "") -> Repl:
        """
        Async-safe way to get a `Repl` instance for a given header.
        Immediately raises an Exception if not possible.
        """
        async with self._lock:
            logger.info(
                f"# Free = {len(self._free)} | # Busy = {len(self._busy)} | # Max = {self.max_repls}"
            )
            for i, r in enumerate(self._free):
                if r.header == header:  # repl shouldn't be exhausted (max age to check)
                    repl = self._free.pop(i)
                    self._busy.add(repl)

                    logger.info(
                        f"\\[{repl.uuid.hex[:8]}] Reusing ({"started" if repl.is_running else "non-started"}) REPL for {snippet_id}"
                    )
                    return repl
            total = len(self._free) + len(self._busy)

            if total < self.max_repls:
                return self.start_new(header)

            if self._free:
                oldest = min(self._free, key=lambda r: r.created_at)
                self._free.remove(oldest)
                await oldest.close()
                del oldest
                return self.start_new(header)

            raise NoAvailableReplError("No available REPLs")

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
            logger.info(f"\\[{repl.uuid.hex[:8]}] Released!")

    def start_new(self, header: str) -> Repl:
        repl = Repl(max_mem=self.max_mem, max_uses=self.max_uses, header=header)
        repl.created_at = time()
        self._busy.add(repl)
        return repl

    async def cleanup(self) -> None:
        async with self._lock:
            logger.info("Cleaning up REPL manager...")
            for repl in self._free:
                await repl.close()
                del repl
            self._free.clear()

            for repl in self._busy:
                await repl.close()
                del repl
            self._busy.clear()

            logger.info("REPL manager cleaned up!")
        pass

    async def prep(
        self, repl: Repl, snippet_id: str, timeout: float, debug: bool
    ) -> CheckResponse | None:
        if repl.is_running:
            return None

        try:
            await repl.start()
        except Exception as e:
            logger.exception("Failed to start REPL: %s", e)
            await self.destroy_repl(repl)
            raise ReplError("Failed to start REPL") from e

        if not is_blank(repl.header):
            try:
                cmd_response = await repl.send_timeout(
                    Snippet(id=f"{snippet_id}-header", code=repl.header),
                    timeout=timeout,
                    debug=debug,
                    is_header=True,
                )
            except Exception as e:
                logger.exception("Failed to run header on REPL: %s", e)
                await self.destroy_repl(repl)
                raise ReplError("Failed to run header on REPL") from e

            if cmd_response.error:
                logger.error(f"Header command failed: {cmd_response.error}")
                await self.destroy_repl(repl)

            return cmd_response
        return None  # TODO: store first header command response
