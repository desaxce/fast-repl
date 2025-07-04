import asyncio
import json
import os
import platform
import signal
import tempfile
import uuid
from asyncio.subprocess import Process
from typing import List, Literal, NotRequired, TypedDict

import psutil

# TODO: Check alternatives to loguru add json nice print
from loguru import logger

from fast_repl.errors import LeanError, ReplError
from fast_repl.settings import settings


class Command(TypedDict):
    cmd: str
    env: NotRequired[int]


class _Pos(TypedDict):
    line: int
    column: int


class _Sorry(TypedDict):
    pos: _Pos
    endPos: _Pos
    goal: str
    proofState: int


class _Message(TypedDict):
    severity: Literal["error", "warning", "info"]
    pos: _Pos
    endPos: _Pos
    data: str


class Response(TypedDict, total=False):
    sorries: List[_Sorry]
    messages: List[_Message]
    env: int
    time: float
    cpu_max: float


class Repl:
    def __init__(
        self,
        *,
        max_memory_gb: int = settings.REPL_MEMORY_GB,
        max_reuse: int = settings.MAX_REUSE,
    ) -> None:
        # TODO: Change error file to PIPE
        self.proc: Process | None = None
        self.error_file = tempfile.TemporaryFile("w+")
        self.use_count = 0
        self.max_memory_bytes = max_memory_gb * 1024 * 1024 * 1024
        self.max_reuse = max_reuse
        self.uuid = uuid.uuid4()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._cpu_max: float = 0.0
        # TODO: Implement cpu at repl level
        self._cpu_task: asyncio.Task[None] | None = None
        self._ps_proc: psutil.Process | None = None

    @property
    def exhausted(self) -> bool:
        return self.use_count >= self.max_reuse

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
        self._ps_proc.cpu_percent(None)
        self._cpu_max = 0.0
        self._cpu_task = self._loop.create_task(self._cpu_monitor())

        logger.info(f"Started REPL {self.uuid.hex[:8]}")

    async def _cpu_monitor(self) -> None:
        while self.is_running and self._ps_proc:
            await asyncio.sleep(1)
            usage = self._ps_proc.cpu_percent(None)
            for child in self._ps_proc.children(recursive=True):
                usage += child.cpu_percent(None)

            self._cpu_max = max(self._cpu_max, usage)

    @property
    def is_running(self) -> bool:
        if not self.proc:
            return False
        return self.proc.returncode is None

    async def send(self, command: Command) -> Response:
        self._cpu_max = 0.0
        if not self.proc or self.proc.returncode is not None:
            # TODO: Don't make it a Lean error.
            raise LeanError("Process not started")

        loop = self._loop or asyncio.get_running_loop()

        assert self.proc.stdin is not None, "stdin pipe not initialized"
        assert self.proc.stdout is not None, "stdout pipe not initialized"

        payload = (json.dumps(command, ensure_ascii=False) + "\n\n").encode("utf-8")
        start = loop.time()
        try:
            self.proc.stdin.write(payload)
            await self.proc.stdin.drain()
        except BrokenPipeError:
            logger.error("Broken pipe when writing to REPL stdin")
            raise LeanError("Lean process broken pipe")
        except Exception as e:
            logger.error("Failed to write to REPL stdin: {}", e)
            raise LeanError("Failed to write to REPL stdin")

        lines: list[bytes] = []
        try:
            while True:
                line = await self.proc.stdout.readline()
                if not line.strip():
                    break
                lines.append(line)
        except Exception as e:
            logger.error("Failed to read from REPL stdout: {}", e)
            # TODO: When raw = b'', REPL process likely dead.
            raise LeanError("Failed to read from REPL stdout")

        elapsed = loop.time() - start

        raw = b"".join(lines)
        try:
            resp: Response = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("JSON decode error: {}", raw)
            raise ReplError("JSON decode error")

        self.error_file.seek(0)
        err = self.error_file.read().strip()
        self.error_file.truncate(0)
        self.error_file.seek(0)
        if err:
            logger.error("Stderr: {}", err)
            raise LeanError(err)

        resp["time"] = elapsed
        resp["cpu_max"] = self._cpu_max
        self.use_count += 1
        return resp

    async def close(self) -> None:
        if self.proc:
            assert self.proc.stdin is not None, "stdin pipe not initialized"
            self.proc.stdin.close()
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            await self.proc.wait()
            if self._cpu_task:
                self._cpu_task.cancel()
