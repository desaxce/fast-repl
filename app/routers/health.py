from fastapi import APIRouter

router = APIRouter()


# TODO: add stats endpoint


# TODO: summary, and description
@router.get("/health")
@router.get("/health/", include_in_schema=False)
async def read_root() -> dict[str, str]:
    return {"message": "Hello, World!"}
