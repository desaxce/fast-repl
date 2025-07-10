from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from loguru import logger
from pydantic.json_schema import GenerateJsonSchema
from rich.logging import RichHandler

from app.manager import Manager
from app.routers.check import router as check_router
from app.settings import Settings


def no_sort(self: GenerateJsonSchema, value: Any, parent_key: Any = None) -> Any:
    return value


setattr(GenerateJsonSchema, "sort", no_sort)


# @app.on_event("startup")
# def on_startup():
#     seed_key()


def create_app(settings: Settings) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        manager = Manager(
            max_repls=settings.MAX_REPLS,
            max_uses=settings.MAX_USES,
            max_mem=settings.MAX_MEM,
        )
        app.state.manager = manager
        # await app.state.mana.init_manager()
        logger.info("Initialized manager!")
        yield
        # await app.state.manager.cleanup()
        logger.info("Cleaned up REPL manager!")

    app = FastAPI(
        lifespan=lifespan,
        title="Lean 4 Proof-Check API",
        description="Submit Lean 4 snippets to be checked/validated via REPL",
        version="0.1.0",  # use same version as in pyproject.toml
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
