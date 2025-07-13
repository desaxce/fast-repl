from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from loguru import logger
from pydantic.json_schema import GenerateJsonSchema
from rich.logging import RichHandler

from app.manager import Manager
from app.prisma_client import prisma
from app.routers.backward import router as backward_router
from app.routers.check import router as check_router
from app.routers.health import router as health_router
from app.settings import Settings

try:
    __version__ = version("fast-repl")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for local dev


def no_sort(self: GenerateJsonSchema, value: Any, parent_key: Any = None) -> Any:
    return value


setattr(GenerateJsonSchema, "sort", no_sort)


# @app.on_event("startup")
# def on_startup():
#     seed_key()


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        if settings.DATABASE_URL:
            await prisma.connect()
        logger.info("Connected to database")
        manager = Manager(
            max_repls=settings.MAX_REPLS,
            max_uses=settings.MAX_USES,
            max_mem=settings.MAX_MEM,
            init_repls=settings.INIT_REPLS,
        )
        app.state.manager = manager
        await app.state.manager.initialize_repls()

        yield

        await app.state.manager.cleanup()
        await prisma.disconnect()
        logger.info("Disconnected from database")

    app = FastAPI(
        lifespan=lifespan,
        title="Lean 4 Proof-Check API",
        description="Submit Lean 4 snippets to be checked/validated via REPL",
        version=__version__,
        openapi_url="/api/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        logger=logger,
    )

    app.include_router(
        check_router,
        prefix="/api",
        tags=["check"],
    )
    app.include_router(
        health_router,
        tags=["health"],
    )
    app.include_router(
        backward_router,
        tags=["backward"],
    )
    return app


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
