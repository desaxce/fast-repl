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


def get_manager(request: Request) -> Manager:
    """Dependency: retrieve the REPL manager from app state"""
    return cast(Manager, request.app.state.manager)


@router.post("/check", response_model=CheckResponse, response_model_exclude_none=True)
@router.post(
    "/check/",
    include_in_schema=False,  # To not clutter OpenAPI spec.
    response_model=CheckResponse,
    response_model_exclude_none=True,
)
async def check(
    request: CheckRequest, manager: Manager = Depends(get_manager)
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
    except Exception as e:
        logger.exception("Failed to get REPL: %s", e)
        raise HTTPException(500, str(e)) from e

    try:
        check_response = await manager.prep(repl, snippet.id, timeout, debug)
        if check_response is not None:
            res = check_response.model_dump()
            if "error" in check_response.model_dump() and res["error"]:
                return check_response
    except Exception as e:
        logger.exception("Failed to prepare REPL: %s", e)
        raise HTTPException(500, str(e)) from e

    try:
        result = await repl.send_timeout(
            Snippet(id=snippet.id, code=body), timeout, debug
        )
    except Exception as e:
        await manager.destroy_repl(repl)
        logger.exception("Failed to send snippet to REPL: %s", e)
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
