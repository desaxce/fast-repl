from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from loguru import logger

from fast_repl.errors import PoolError
from fast_repl.repl import Command
from fast_repl.repl_pool import ReplPoolManager


@asynccontextmanager  # type: ignore
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await app.state.pool.init_pool()
    logger.info("Initialized pool!")
    yield
    await app.state.pool.cleanup()
    logger.info("Cleaned up pool!")


app = FastAPI()
app.state.pool = ReplPoolManager()


# TODO: make it a health endpoint + add stats
@app.get("/")  # type: ignore
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}


@app.post("/repl/")  # type: ignore
async def send_repl(command: Command) -> Any:  # TODO: fix Any typing
    try:
        repl = await app.state.pool.get_repl()
    except PoolError:
        raise HTTPException(429, "REPL pool exhausted")

    try:
        return await repl.send(command)
    except Exception as e:
        raise HTTPException(500, str(e)) from e
    finally:
        await app.state.pool.release_repl(repl)
        logger.info("DONE releasing")
