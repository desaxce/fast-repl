from typing import Any

from fastapi import APIRouter, Depends

from app.manager import Manager
from app.routers.check import get_manager, run_checks
from app.schemas import Snippet, VerifyRequestBody

router = APIRouter()


@router.post("/one_pass_verify_batch")
@router.post("/verify")
async def one_pass_verify_batch(
    body: VerifyRequestBody,
    manager: Manager = Depends(get_manager),
    # access: require_access_dep, # TODO: later implement authentication
) -> dict[str, Any]:
    """Backward compatible endpoint: accepts both 'proof' / 'code' fields."""

    codes = body.codes
    snippets = [
        Snippet(custom_id=str(code.custom_id), code=code.get_proof_content() or "no-id")
        for code in codes
    ]

    timeout = body.timeout
    debug = False

    compatible_check_response = await run_checks(
        snippets, float(timeout), debug, manager
    )
    results_with_time_in_response: list[dict[str, Any]] = []
    for result in compatible_check_response.results:
        resp = None
        if result.response is not None:
            resp = dict(result.response)
        result_with_time_in_response = {
            "custom_id": result.custom_id,
            "error": result.error,
        }
        if resp is not None:
            resp["time"] = result.time
        results_with_time_in_response.append(result_with_time_in_response)

    return {"results": results_with_time_in_response}
