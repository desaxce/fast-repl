from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request

from app.errors import PoolError, ReplError
from app.repl import Command, Repl
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
    request: CheckRequest, pool: ReplManager = Depends(get_pool)
) -> Any:  # TODO: fix Any typing use checkresponse | throw
    assert len(request.snippets) == 1, "Batch mode not implemented yet"
    command: Command = {"cmd": request.snippets[0].code}
    timeout: float = request.timeout or 30.0

    header, body = split_snippet(request.snippets[0].code)

    try:
        # It's a bit annoying to do a get_repl with header and receive
        # a REPL that's not started.
        repl: Repl = await pool.get_repl(header)
        # TODO: maybe put this repl bit in a pool API
        if not repl.is_running:
            try:
                await repl.start()  # here add header and include timeout
            except ReplError:
                await pool.release_repl(repl)
                raise HTTPException(500, "Error occurred: failed to start REPL")
    except PoolError:
        raise HTTPException(429, "REPL pool exhausted")

    command = {"cmd": body}

    try:
        result = await repl.send_timeout(command, timeout)
    except Exception as e:
        await pool.destroy_repl(repl)
        raise HTTPException(500, str(e)) from e
    else:
        await pool.release_repl(repl)
        return result
