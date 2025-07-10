import json
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app.errors import NoAvailableReplError
from app.manager import Manager
from app.repl import Repl
from app.schemas import CheckRequest, CheckResponse, Snippet
from app.split import split_snippet

router = APIRouter()


def get_pool(request: Request) -> Manager:
    """Dependency: retrieve the REPL pool from app state"""
    return cast(Manager, request.app.state.pool)


# TODO: summary, and description (tags set during include_router)
@router.get("/")  # type: ignore
async def read_root() -> dict[str, str]:
    """Health check or welcome endpoint"""
    return {"message": "Hello, World!"}


@router.post("/check", response_model_exclude_none=True)  # type: ignore
async def check(  # type: ignore[reportUnusedFunction]
    request: CheckRequest, manager: Manager = Depends(get_pool)
) -> CheckResponse:
    if not request.snippets:
        raise HTTPException(400, "No snippets provided")

    # TODO: Handle multiple snippets.
    assert len(request.snippets) == 1, "Batch mode not implemented yet"
    snippet = request.snippets[0]
    header, body = split_snippet(snippet.code)

    timeout: float = request.timeout or 30.0
    debug = request.debug

    try:
        repl: Repl = await manager.get_repl(header, snippet.id)
    except NoAvailableReplError:
        raise HTTPException(429, "Unable to acquire a REPL")

    try:
        await manager.prep(repl, header, snippet.id, timeout, debug)
    except NoAvailableReplError as e:
        raise HTTPException(500, str(e)) from e

    try:
        result = await repl.send_timeout(
            Snippet(id=snippet.id, code=body), timeout, debug
        )
    except Exception as e:
        await manager.destroy_repl(repl)
        raise HTTPException(500, str(e)) from e
    else:
        logger.info(
            "[{}] Result for [bold magenta]{}[/bold magenta] body: \n{}",
            repl.uuid.hex[:8],
            snippet.id,
            json.dumps(result.model_dump(exclude_none=True), indent=2),
        )
        await manager.release_repl(repl)
        return result
