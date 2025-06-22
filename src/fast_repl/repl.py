import asyncio
import json
import os
import signal
import sys
import tempfile
from asyncio.subprocess import Process
from typing import List, Literal, NotRequired, TypedDict

# TODO: Check alternatives to loguru add json nice print
from loguru import logger

from fast_repl.errors import LeanError, ReplError
from fast_repl.settings import (
    LOG_LEVEL,
    MAX_REUSE,
    PATH_TO_MATHLIB,
    PATH_TO_REPL,
    REPL_MEMORY_GB,
)


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


logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL)


class Repl:
    def __init__(self, *, max_memory_gb: int = REPL_MEMORY_GB, max_reuse: int = MAX_REUSE) -> None:
        # TODO: Change error file to PIPE
        self.proc: Process | None = None
        self.error_file = tempfile.TemporaryFile("w+")
        self.use_count = 0
        self.max_memory_bytes = max_memory_gb * 1024 * 1024 * 1024
        self.max_reuse = max_reuse

    @property
    def exhausted(self) -> bool:
        return self.use_count >= self.max_reuse

    async def start(self) -> None:
        # TODO: try/catch this bit and raise as REPL startup error.
        def _preexec() -> None:
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (self.max_memory_bytes, self.max_memory_bytes))
            os.setsid()

        self.proc = await asyncio.create_subprocess_exec(
            "lake",
            "env",
            PATH_TO_REPL,
            cwd=PATH_TO_MATHLIB,
            env=os.environ,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=self.error_file,
            preexec_fn=_preexec,
        )

    async def send(self, command: Command) -> Response:
        if not self.proc:
            # TODO: Don't make it a Lean error.
            raise LeanError("Process not started")

        assert self.proc.stdin is not None, "stdin pipe not initialized"
        assert self.proc.stdout is not None, "stdout pipe not initialized"

        payload = (json.dumps(command, ensure_ascii=False) + "\n\n").encode("utf-8")
        start = asyncio.get_event_loop().time()
        try:
            self.proc.stdin.write(payload)
            await self.proc.stdin.drain()
        except BrokenPipeError:
            raise LeanError("Lean process broken pipe")

        lines: list[bytes] = []
        while True:
            line = await self.proc.stdout.readline()
            if not line.strip():
                break
            lines.append(line)
        elapsed = asyncio.get_event_loop().time() - start

        raw = b"".join(lines)
        try:
            resp: Response = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("JSON decode error: {}", raw)
            raise ReplError("JSON decode error")

        self.error_file.seek(0)
        err = self.error_file.read().strip()
        if err:
            logger.error("Stderr: {}", err)
            raise LeanError(err)

        resp["time"] = elapsed
        self.use_count += 1
        return resp

    async def close(self) -> None:
        if self.proc:
            assert self.proc.stdin is not None, "stdin pipe not initialized"
            self.proc.stdin.close()
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            await self.proc.wait()
