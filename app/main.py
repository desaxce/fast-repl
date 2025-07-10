from fastapi import FastAPI
from loguru import logger
from rich.logging import RichHandler

from app.manager import Manager
from app.routers.check import router as check_router
from app.settings import Settings

# @asynccontextmanager  # type: ignore
# async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
#     await app.state.pool.init_pool()
#     logger.info("Initialized pool!")
#     yield
#     await app.state.pool.cleanup()
#     logger.info("Cleaned up pool!")

# @app.on_event("startup")
# def on_startup():
#     seed_key()


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title="Lean 4 Proof-Check API",
        description="Submit Lean 4 snippets to be checked/validated via REPL",
        version="0.1.0",  # use same version as in pyproject.toml
        openapi_url="/api/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        logger=logger,
    )

    pool = Manager(
        max_repls=settings.MAX_REPLS,
        max_uses=settings.MAX_USES,
        max_mem=settings.MAX_MEM,
    )
    app.state.pool = pool
    app.include_router(
        check_router,
        prefix="/api",
        tags=["check"],
    )
    return app

    # # TODO: make it a health endpoint + add stats
    # @router.get("/")  # type: ignore
    # def read_root() -> dict[str, str]:  # type: ignore[reportUnusedFunction]
    #     return {"message": "Hello, World!"}


settings = Settings()

logger.remove()
logger.add(
    RichHandler(show_time=True, markup=True),
    colorize=True,
    level=settings.LOG_LEVEL,
    format="{message}",
    backtrace=True,
    diagnose=True,
)

app = create_app(settings)
