from typing import Any, List, Literal, NotRequired, Type, TypedDict

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Snippet(BaseModel):
    id: str = Field(..., description="Identifier to trace the snippet")
    code: str = Field(..., description="Lean 4 snippet or proof attempt")


class Command(TypedDict):
    cmd: str
    env: NotRequired[int]


class Pos(TypedDict):
    line: int
    column: int


class Sorry(TypedDict):
    pos: Pos
    endPos: Pos
    goal: str
    proofState: int


class Message(TypedDict):
    severity: Literal[
        "error", "warning", "info"
    ]  # TODO: check what type of Message severity we can get
    pos: Pos
    endPos: Pos | None
    data: str


class Diagnostics(TypedDict, total=False):
    repl_uuid: str
    cpu_max: float
    memory_max: float


class CheckResponse(TypedDict, total=False):
    env: int
    messages: List[Message]
    sorries: List[Sorry]
    time: float
    diagnostics: NotRequired[Diagnostics]


from typing import TypeVar

T = TypeVar("T", bound="CheckRequest")


class CheckRequest(BaseModel):
    snippets: List[Snippet] | None = Field(
        None, description="List of snippets to validate (batch or single element)"
    )
    snippet: Snippet | None = Field(
        default=None, description="Single snippet to validate"
    )
    timeout: int = Field(
        30, description="Maximum time in seconds before aborting the check", ge=0
    )
    debug: bool = Field(
        False, description="Include CPU/RAM usage and REPL instance ID in the response"
    )
    reuse: bool = Field(
        True, description="Whether to attempt using a pooled REPL if available"
    )
    infotree: Literal["none", "original", "synthetic"] = Field(
        "none",
        description="Level of detail for the InfoTree: 'none' | 'original' | 'synthetic'",
    )

    @model_validator(mode="before")
    @classmethod
    def unify_snippets(cls: Type[T], values: dict[str, Any]) -> dict[str, Any]:
        arr = values.get("snippets")
        one = values.get("snippet")
        logger.info(f"Received snippets: {arr}, single snippet: {one}")
        if not arr and not one:
            raise ValueError("Either `snippet` or `snippets` must be provided")
        if arr and one:
            raise ValueError("Only one of `snippet` or `snippets` allowed")
        if one:
            values["snippets"] = [one]
            values.pop("snippet", None)
        return values

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "snippets": [
                    {"id": "a1", "code": "# Lean 4 code..."},
                    {"id": "b2", "code": "# Another snippet..."},
                ],
                "timeout": 5,
                "debug": False,
                "reuse": True,
                "infotree": "original",
            }
        }
    )
