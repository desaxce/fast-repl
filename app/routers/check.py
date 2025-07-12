import asyncio
import json
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from app.errors import NoAvailableReplError
from app.manager import Manager
from app.schemas import (
    CheckRequest,
    CheckResponse,
    ChecksRequest,
    CompatibleCheckResponse,
    Snippet,
)
from app.split import split_snippet

router = APIRouter()


def get_manager(request: Request) -> Manager:
    """Dependency: retrieve the REPL manager from app state"""
    return cast(Manager, request.app.state.manager)


async def _run_checks(
    snippets: list[Snippet], timeout: float, debug: bool, manager: Manager
) -> (
    CompatibleCheckResponse
):  # TODO: Deprecate with EOL then switch to list[CheckResponse]
    async def run_one(snippet: Snippet) -> CheckResponse:
        header, body = split_snippet(snippet.code)
        try:
            repl = await manager.get_repl(header, snippet.custom_id)
        except NoAvailableReplError:
            logger.exception("No available REPLs")
            raise HTTPException(429, "No available REPLs") from None
        except Exception as e:
            logger.exception("Failed to get REPL: %s", e)
            raise HTTPException(500, str(e)) from e

        try:
            prep = await manager.prep(repl, snippet.custom_id, timeout, debug)
            if prep and prep.error:
                return prep
        except Exception as e:
            logger.exception("REPL prep failed")
            await manager.destroy_repl(repl)
            raise HTTPException(500, str(e)) from e

        try:
            resp = await repl.send_timeout(
                Snippet(custom_id=snippet.custom_id, code=body), timeout, debug
            )
        except Exception as e:
            logger.exception("Snippet execution failed")
            await manager.destroy_repl(repl)
            raise HTTPException(500, str(e)) from e
        else:
            logger.info(
                "[{}] Result for [bold magenta]{}[/bold magenta] body: →\n{}",
                repl.uuid.hex[:8],
                snippet.custom_id,
                json.dumps(resp.model_dump(exclude_none=True), indent=2),
            )
            await manager.release_repl(repl)
            return resp

    return CompatibleCheckResponse(
        results=await asyncio.gather(*(run_one(s) for s in snippets))
    )


@router.post(
    "/checks",
    response_model=CompatibleCheckResponse,
    response_model_exclude_none=True,
)
@router.post(
    "/checks/",
    response_model=CompatibleCheckResponse,
    response_model_exclude_none=True,
    include_in_schema=False,  # To not clutter OpenAPI spec.
)
async def check_batch(
    request: ChecksRequest, manager: Manager = Depends(get_manager)
) -> CompatibleCheckResponse:
    return await _run_checks(
        request.snippets, float(request.timeout), request.debug, manager
    )


@router.post(
    "/check",
    response_model=CheckResponse,
    response_model_exclude_none=True,
)
@router.post(
    "/check/",
    response_model=CheckResponse,
    response_model_exclude_none=True,
    include_in_schema=False,  # To not clutter OpenAPI spec.
)
async def check_single(
    request: CheckRequest, manager: Manager = Depends(get_manager)
) -> CheckResponse:
    resp_list = await _run_checks(
        [request.snippet], float(request.timeout), request.debug, manager
    )
    return resp_list.results[0]
