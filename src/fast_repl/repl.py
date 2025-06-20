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
from fast_repl.settings import LOG_LEVEL, PATH_TO_MATHLIB, PATH_TO_REPL


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
    def __init__(self) -> None:
        # TODO: Change error file to PIPE
        self.proc: Process | None = None
        self.error_file = tempfile.TemporaryFile("w+")

    async def start(self) -> None:
        # TODO: try/catch this bit and raise as REPL startup error.
        self.proc = await asyncio.create_subprocess_exec(
            "lake",
            "env",
            PATH_TO_REPL,
            cwd=PATH_TO_MATHLIB,
            env=os.environ,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=self.error_file,
            preexec_fn=os.setsid,
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
        return resp

    async def close(self) -> None:
        if self.proc:
            assert self.proc.stdin is not None, "stdin pipe not initialized"
            self.proc.stdin.close()
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            await self.proc.wait()
