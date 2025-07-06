from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from app.errors import PoolError, ReplError
from app.repl import Command, Repl
from app.repl_pool import ReplPoolManager

router = APIRouter()


def get_pool(request: Request) -> ReplPoolManager:
    """Dependency: retrieve the REPL pool from app state"""
    return cast(ReplPoolManager, request.app.state.pool)


# TODO: summary, and description (tags set during include_router)
@router.get("/")
async def read_root() -> dict[str, str]:
    """Health check or welcome endpoint"""
    return {"message": "Hello, World!"}


@router.post("/check")
async def check(  # type: ignore[reportUnusedFunction]
    command: Command, timeout: float = 10, pool: ReplPoolManager = Depends(get_pool)
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

    try:
        result = await repl.send_timeout(command, timeout)
    except Exception as e:
        await pool.destroy_repl(repl)
        raise HTTPException(500, str(e)) from e
    else:
        await pool.release_repl(repl)
        return result
