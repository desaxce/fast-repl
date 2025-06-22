from typing import Any

from fastapi import FastAPI, HTTPException

from fast_repl.errors import LeanError, PoolError
from fast_repl.repl import Command
from fast_repl.repl_pool import ReplPoolManager

# TODO: perform initialization if ReplPoolManager instead
# @asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
#     await repl.start()
#     logger.info("Lean REPL started")
#     yield
#     await repl.close()
#     logger.info("Lean REPL closed")


# app = FastAPI(lifespan=lifespan)
# repl = Repl()
app = FastAPI()
pool = ReplPoolManager()


@app.on_event("startup")
async def startup() -> None:
    await pool.init_pool()


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
