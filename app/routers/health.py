from fastapi import APIRouter

router = APIRouter()


# TODO: add stats endpoint


# TODO: summary, and description
@router.get("/health")  # type: ignore
@router.get("/health/", include_in_schema=False)  # type: ignore
async def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}
