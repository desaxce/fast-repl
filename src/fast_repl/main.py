from typing import Any

from fastapi import FastAPI, HTTPException
from loguru import logger

from fast_repl.errors import PoolError, ReplError
from fast_repl.repl import Command, Repl
from fast_repl.repl_pool import ReplPoolManager

# @asynccontextmanager  # type: ignore
# async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
#     await app.state.pool.init_pool()
#     logger.info("Initialized pool!")
#     yield
#     await app.state.pool.cleanup()
#     logger.info("Cleaned up pool!")

app = FastAPI(logger=logger)
pool: ReplPoolManager = ReplPoolManager()
# TODO: make fastapi server fail to launch if repl can't initialize


# TODO: make it a health endpoint + add stats
@app.get("/")  # type: ignore
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}


@app.post("/repl")  # type: ignore
async def send_repl(command: Command) -> Any:  # TODO: fix Any typing
    try:
        repl: Repl = await pool.get_repl()
        if not repl.is_running:
            try:
                await repl.start()  # here add header
            except ReplError:
                await pool.release_repl(repl)
                raise HTTPException(500, "Error occurred: failed to start REPL")
    except PoolError:
        raise HTTPException(429, "REPL pool exhausted")

    try:
        return await repl.send(command)
    except Exception as e:
        raise HTTPException(500, str(e)) from e
    finally:
        await pool.release_repl(repl)
