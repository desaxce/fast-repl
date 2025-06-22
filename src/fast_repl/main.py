from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from loguru import logger

from fast_repl.errors import LeanError, PoolError
from fast_repl.repl import Command
from fast_repl.repl_pool import ReplPoolManager


@asynccontextmanager  # type: ignore
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await pool.init_pool()
    logger.info("Initialized pool!")
    yield
    await pool.cleanup()
    logger.info("Cleaned up pool!")


app = FastAPI()
pool = ReplPoolManager()


# TODO: make it a health endpoint + add stats
@app.get("/")  # type: ignore
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}


@app.post("/repl/")  # type: ignore
async def send_repl(command: Command) -> Any:  # TODO: fix Any typing
    try:
        repl = await pool.get_repl()
    except PoolError:
        raise HTTPException(429, "REPL pool exhausted")

    try:
        return await repl.send(command)
    except LeanError as e:
        raise HTTPException(500, str(e))
    finally:
        await pool.release_repl(repl)
