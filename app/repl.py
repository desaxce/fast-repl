import asyncio
import json
import os
import platform
import signal
import tempfile
import uuid
from asyncio.subprocess import Process
from time import time

import psutil
from loguru import logger
from rich.console import Console
from rich.syntax import Syntax

from app.errors import LeanError, ReplError
from app.schemas import CheckResponse, Command, CommandResponse, Diagnostics, Snippet
from app.settings import settings
from app.utils import is_blank

log_lock = asyncio.Lock()
console = Console(log_time_format="[%m/%d/%y %H:%M:%S]", force_terminal=True)


async def log_snippet(uuid: uuid.UUID, snippet_id: str, code: str) -> None:
    header = (
        f"\\[{uuid.hex[:8]}] Running snippet [bold magenta]{snippet_id}[/bold magenta]:"
    )
    syntax = Syntax(
        code or "<empty>",
        "lean",
        theme="solarized-dark",
        line_numbers=False,
        word_wrap=False,
    )

    async with log_lock:
        logger.info(header)
        console.log(syntax)


class Repl:
    def __init__(
        self,
        header: str = "",
        *,
        max_mem: int = settings.MAX_MEM,
        max_uses: int = settings.MAX_USES,
    ) -> None:
        # TODO: Change error file to PIPE
        self.header = header
        self.created_at: float = time()
        self.proc: Process | None = None
        self.error_file = tempfile.TemporaryFile("w+")
        self.use_count = 0
        self.max_memory_bytes = max_mem * 1024 * 1024
        self.max_uses = max_uses
        self.uuid = uuid.uuid4()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._cpu_max: float = 0.0
        self._mem_max: int = 0
        # TODO: Implement cpu at repl level
        self._cpu_task: asyncio.Task[None] | None = None
        self._ps_proc: psutil.Process | None = None

    @property
    def exhausted(self) -> bool:
        if self.header and not is_blank(self.header):  # todo: fix this header part
            return self.use_count >= self.max_uses + 1

        return self.use_count >= self.max_uses

    async def start(self) -> None:
        # TODO: try/catch this bit and raise as REPL startup error.
        self._loop = asyncio.get_running_loop()

        def _preexec() -> None:
            import resource

            # Memory limit
            if platform.system() != "Darwin":  # Only for Linux
                resource.setrlimit(
                    resource.RLIMIT_AS, (self.max_memory_bytes, self.max_memory_bytes)
                )

            # No CPU limit on REPL, most Lean proofs take up to one core.
            # The adjustment variable is the maximum number of REPLs / timeout.
            # See https://github.com/leanprover-community/repl/issues/91
            # TODO: Run CPU usage stats on Goedel.

            os.setsid()

        self.proc = await asyncio.create_subprocess_exec(
            "lake",
            "env",
            settings.repl_bin_path,
            cwd=settings.path_to_mathlib,
            env=os.environ,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=self.error_file,
            preexec_fn=_preexec,
        )

        self._ps_proc = psutil.Process(self.proc.pid)
        self._cpu_max = 0.0
        self._cpu_task = self._loop.create_task(self._cpu_monitor())
        self._mem_task = self._loop.create_task(self._mem_monitor())

        logger.info(f"\\[{self.uuid.hex[:8]}] Started")

    async def _cpu_monitor(self) -> None:
        while self.is_running and self._ps_proc:
            await asyncio.sleep(1)
            usage = self._ps_proc.cpu_percent(None)
            for child in self._ps_proc.children(recursive=True):
                usage += child.cpu_percent(None)

            self._cpu_max = max(self._cpu_max, usage)

    async def _mem_monitor(self) -> None:
        while self.is_running and self._ps_proc:
            await asyncio.sleep(1)
            total = self._ps_proc.memory_info().rss
            for child in self._ps_proc.children(recursive=True):
                total += child.memory_info().rss
            self._mem_max = max(self._mem_max, total)

    @property
    def is_running(self) -> bool:
        if not self.proc:
            return False
        return self.proc.returncode is None

    async def send_timeout(
        self, snippet: Snippet, timeout: float, debug: bool, is_header: bool = False
    ) -> CheckResponse:
        error = None
        cmd_response = None
        elapsed_time = 0.0
        diagnostics = Diagnostics(repl_uuid=str(self.uuid))

        try:
            cmd_response, elapsed_time, diagnostics = await asyncio.wait_for(
                self.send(snippet, debug=debug, is_header=is_header), timeout=timeout
            )
        except TimeoutError:
            elapsed_time = timeout
            error = f"Lean REPL command timed out in {timeout} seconds"
            logger.error(error)
        except LeanError as e:
            logger.exception("Lean REPL error: %s", e)
            raise e
        except ReplError as e:
            logger.exception("REPL error: %s", e)
            raise e

        return CheckResponse(
            custom_id=snippet.custom_id,
            error=error,
            response=cmd_response,
            time=elapsed_time,
            diagnostics=diagnostics if len(diagnostics) > 0 else None,
        )

    async def send(
        self, snippet: Snippet, debug: bool, is_header: bool = False
    ) -> tuple[CommandResponse, float, Diagnostics]:
        await log_snippet(self.uuid, snippet.custom_id, snippet.code)

        self._cpu_max = 0.0
        self._mem_max = 0

        if not self.proc or self.proc.returncode is not None:
            logger.error("REPL process not started or shut down")
            raise ReplError("REPL process not started or shut down")

        loop = self._loop or asyncio.get_running_loop()

        if self.proc.stdin is None:
            raise ReplError("stdin pipe not initialized")
        if self.proc.stdout is None:
            raise ReplError("stdout pipe not initialized")

        input: Command = {"cmd": snippet.code}

        if self.use_count != 0 and not is_header:  # remove is_header
            input["env"] = 0

        payload = (
            json.dumps(input, ensure_ascii=False) + "\n\n"  # TODO: add the gc feature
        ).encode("utf-8")

        start = loop.time()
        logger.debug("Sending payload to REPL")

        try:
            self.proc.stdin.write(payload)
            await self.proc.stdin.drain()
        except BrokenPipeError:
            logger.error("Broken pipe while writing to REPL stdin")
            raise LeanError("Lean process broken pipe")
        except Exception as e:
            logger.error("Failed to write to REPL stdin: %s", e)
            raise LeanError("Failed to write to REPL stdin")

        logger.debug("Reading response from REPL stdout")
        raw = await self._read_response()
        elapsed = loop.time() - start

        logger.debug("Raw response from REPL: %r", raw)
        try:
            resp: CommandResponse = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("JSON decode error: %r", raw)
            raise ReplError("JSON decode error")

        self.error_file.seek(0)
        err = self.error_file.read().strip()
        self.error_file.seek(0)
        self.error_file.truncate(0)
        if err:
            logger.error("Stderr: %s", err)
            raise LeanError(err)

        elapsed_time = round(elapsed, 6)
        diagnostics: Diagnostics = {
            "repl_uuid": str(self.uuid),
            "cpu_max": self._cpu_max,
            "memory_max": self._mem_max,
        }

        self.use_count += 1
        return resp, elapsed_time, (diagnostics if debug else {})

    async def _read_response(self) -> bytes:
        if not self.proc or self.proc.stdout is None:
            logger.error("REPL process not started or stdout pipe not initialized")
            raise ReplError("REPL process not started or stdout pipe not initialized")

        lines: list[bytes] = []
        try:
            while True:
                chunk = await self.proc.stdout.readline()
                # EOF or blank line as terminator
                if not chunk or not chunk.strip():
                    break
                lines.append(chunk)
        except Exception as e:
            logger.error("Failed to read from REPL stdout: %s", e)
            raise LeanError("Failed to read from REPL stdout")
        return b"".join(lines)

    async def close(self) -> None:
        if self.proc:
            assert self.proc.stdin is not None, "stdin pipe not initialized"
            self.proc.stdin.close()
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            await self.proc.wait()
            if self._cpu_task:
                self._cpu_task.cancel()
            if self._mem_task:
                self._mem_task.cancel()
