from typing import Any

from fastapi import FastAPI, HTTPException

from fast_repl.errors import LeanError
from fast_repl.repl import Command, Repl

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


# TODO: make it a health endpoint + add stats
@app.get("/")  # type: ignore
def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}


@app.post("/repl/")  # type: ignore
async def send_repl(command: Command) -> Any:  # TODO: fix Any typing
    repl = Repl()
    try:
        await repl.start()
        return await repl.send(command)
    except LeanError as e:
        raise HTTPException(500, str(e))
    finally:
        await repl.close()
