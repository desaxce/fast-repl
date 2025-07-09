from typing import List, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field


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


class CheckRequest(BaseModel):
    # TODO: ensure users can call with single snippet without having to pass array as arg in body
    snippets: List[Snippet] = Field(
        ..., description="List of snippets to validate (batch or single element)"
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

    # TODO: change info tree enum
    infotree: Literal["none", "short", "full"] = Field(
        "none",
        description="Level of detail for the InfoTree: 'none' | 'short' | 'full'",
    )

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
                "infotree": "full",
            }
        }
    )
