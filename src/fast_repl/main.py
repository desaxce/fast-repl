from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from loguru import logger

from fast_repl.errors import PoolError, ReplError
from fast_repl.repl import Command, Repl, Response
from fast_repl.repl_pool import ReplPoolManager
from fast_repl.settings import Settings

# @asynccontextmanager  # type: ignore
# async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
#     await app.state.pool.init_pool()
#     logger.info("Initialized pool!")
#     yield
#     await app.state.pool.cleanup()
#     logger.info("Cleaned up pool!")


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title="Lean 4 Proof-Check API",
        description="Submit Lean 4 snippets to be checked/validated via REPL",
        version="0.1.0",
        openapi_url="/api/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        logger=logger,
    )  # TODO: Make logger aligned on timestamp.

    pool: ReplPoolManager = ReplPoolManager(
        max_repls=settings.MAX_REPLS,
        max_reuse=settings.MAX_REUSE,
        memory_gb=settings.REPL_MEMORY_GB,
    )

    router = APIRouter(prefix="/api")

    # TODO: make it a health endpoint + add stats
    @router.get("/")  # type: ignore
    def read_root() -> dict[str, str]:  # type: ignore[reportUnusedFunction]
        return {"message": "Hello, World!"}

    @router.post("/check")  # type: ignore
    async def check(  # type: ignore[reportUnusedFunction]
        command: Command, timeout: float = 10
    ) -> Any:  # TODO: fix Any typing
        try:
            repl: Repl = await pool.get_repl()
            # TODO: maybe put this repl bit in a pool API
            if not repl.is_running:
                try:
                    await repl.start()  # here add header and include timeout
                except ReplError:
                    await pool.release_repl(repl)
                    raise HTTPException(500, "Error occurred: failed to start REPL")
        except PoolError:
            raise HTTPException(429, "REPL pool exhausted")

        result: Response = {}
        try:
            result = await repl.send_timeout(command, timeout)
        except Exception as e:
            await pool.destroy_repl(repl)
            raise HTTPException(500, str(e)) from e
        else:
            await pool.release_repl(repl)
            return result

    app.include_router(router)
    return app


settings = Settings()
app = create_app(settings)
