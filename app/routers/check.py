from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger  # ADD nice looking json logs

from app.errors import PoolError
from app.repl import Repl
from app.repl_pool import ReplManager
from app.schemas import CheckRequest
from app.split import split_snippet

router = APIRouter()


def get_pool(request: Request) -> ReplManager:
    """Dependency: retrieve the REPL pool from app state"""
    return cast(ReplManager, request.app.state.pool)


# TODO: summary, and description (tags set during include_router)
@router.get("/")
async def read_root() -> dict[str, str]:
    """Health check or welcome endpoint"""
    return {"message": "Hello, World!"}


@router.post("/check")
async def check(  # type: ignore[reportUnusedFunction]
    request: CheckRequest, repl_manager: ReplManager = Depends(get_pool)
) -> Any:  # TODO: fix Any typing use checkresponse | throw
    assert len(request.snippets) == 1, "Batch mode not implemented yet"
    timeout: float = request.timeout or 30.0
    header, body = split_snippet(request.snippets[0].code)

    logger.info(f"header: {header}, body: {body}")
    try:
        repl: Repl = await repl_manager.get_repl(header)
        # TODO: maybe put this repl bit in a pool API
        if not repl.is_running:
            try:
                await repl.start()
            except Exception as e:
                logger.error(f"Failed to start REPL: {e}")
                await repl_manager.destroy_repl(repl)
                raise HTTPException(500, str(e)) from e
            else:
                if header and header != "":
                    try:
                        logger.debug(
                            f"Using timeout {timeout} for REPL {repl.uuid.hex[:8]}"
                        )
                        await repl.send_timeout({"cmd": header}, timeout=timeout)
                    except Exception as e:
                        logger.error(f"Failed to run header to REPL: {e}")
                        await repl_manager.destroy_repl(repl)
                        raise HTTPException(500, str(e)) from e
    except PoolError:
        raise HTTPException(429, "Unable to acquire a REPL")

    try:
        result = await repl.send_timeout({"cmd": body}, timeout)
    except Exception as e:
        await repl_manager.destroy_repl(repl)
        raise HTTPException(500, str(e)) from e
    else:
        await repl_manager.release_repl(repl)
        return result
