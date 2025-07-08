from typing import List, Literal, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class Snippet(BaseModel):
    id: str = Field(..., description="Identifier to trace the snippet")
    code: str = Field(..., description="Lean 4 snippet or proof attempt")


class Command(TypedDict):
    cmd: str
    env: NotRequired[int]


class _Pos(TypedDict):
    line: int
    column: int


class _Sorry(TypedDict):
    pos: _Pos
    endPos: _Pos
    goal: str
    proofState: int


class _Message(TypedDict):
    severity: Literal["error", "warning", "info"]
    pos: _Pos
    endPos: _Pos
    data: str


class Diagnostics(TypedDict, total=False):
    repl_uuid: str
    cpu_max: float
    memory_max: float


# TODO: Move some of those to schemas or next to it
class Response(TypedDict, total=False):  # TODO: rename checkresponse
    sorries: List[_Sorry]
    messages: List[_Message]
    env: int
    time: float
    diagnostics: NotRequired[Diagnostics]


# TODO: ensure users can call with single snippet without having to pass array as arg in body
class CheckRequest(BaseModel):
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
