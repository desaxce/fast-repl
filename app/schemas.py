from typing import Any, List, Literal, NotRequired, Type, TypedDict

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Snippet(BaseModel):
    custom_id: str = Field(
        ..., description="Identifier to trace the snippet"
    )  # TODO: Rename to id
    code: str = Field(..., description="Lean 4 snippet or proof attempt")


# The classes below map to the REPL/JSON.lean in the Lean REPL repository:
# see https://github.com/leanprover-community/repl


class Command(TypedDict):
    cmd: str
    env: NotRequired[int | None]


class Pos(TypedDict):
    line: int
    column: int


class Sorry(TypedDict):
    pos: Pos
    endPos: Pos
    goal: str
    proofState: NotRequired[int | None]


class Message(TypedDict):
    severity: Literal["trace", "info", "warning", "error"]
    pos: Pos
    endPos: NotRequired[Pos | None]
    data: str


class ProofStep(TypedDict):
    proofState: int
    tactic: str


class Tactic(TypedDict):
    pos: int
    endPos: int
    goals: str
    tactic: str
    proofState: NotRequired[int | None]
    usedConstants: NotRequired[list[str]]


class Diagnostics(TypedDict, total=False):
    repl_uuid: str
    cpu_max: float
    memory_max: float


class CommandResponse(TypedDict):
    env: int
    messages: NotRequired[List[Message]]
    sorries: NotRequired[List[Sorry]]
    tactics: NotRequired[List[Tactic]]
    infotree: NotRequired[dict[str, Any] | None]


from typing import TypeVar

T = TypeVar("T", bound="CheckRequest")
TS = TypeVar("TS", bound="ChecksRequest")
U = TypeVar("U", bound="CheckResponse")


# TODO: Check what REPL-level parallelism means - also check repl-level timeout
class CheckResponse(BaseModel):
    custom_id: str = Field(..., description="Identifier to trace the snippet")
    time: float = 0.0
    error: str | None = None
    response: CommandResponse | None = None
    diagnostics: Diagnostics | None = None

    @model_validator(mode="before")
    @classmethod
    def require_error_or_response(
        cls: Type[U], values: dict[str, Any]
    ) -> dict[str, Any]:
        if not (values.get("error") or values.get("response")):
            raise ValueError("either `error` or `response` must be set")
        return values


# Useful class for compatibility with the old API
class CompatibleCheckResponse(BaseModel):
    results: List[CheckResponse]


class BaseRequest(BaseModel):
    timeout: int = Field(
        30, description="Maximum time in seconds before aborting the check", ge=0
    )
    debug: bool = Field(
        False, description="Include CPU/RAM usage and REPL instance ID in the response"
    )
    reuse: bool = Field(
        True, description="Whether to attempt using a REPL if available"
    )
    infotree: Literal["none", "original", "synthetic"] = Field(
        "none",
        description="Level of detail for the InfoTree: 'none' | 'original' | 'synthetic'",
    )


class ChecksRequest(BaseRequest):
    snippets: List[Snippet] = Field(
        description="List of snippets to validate (batch or single element)"
    )

    @model_validator(mode="before")
    @classmethod
    def check_snippets(cls: Type[TS], values: dict[str, Any]) -> dict[str, Any]:
        arr = values.get("snippets")
        if not arr or len(arr) == 0:
            raise ValueError("`snippets` must be provided and non empty")

        ids = set({s["custom_id"] for s in arr})
        if len(ids) != len(arr):
            raise ValueError("`snippets` must have unique ids")
        return values

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "snippets": [
                    {
                        "custom_id": "mathlib-import-def",
                        "code": "import Mathlib\ndef f := 1",
                    },
                ],
                "timeout": 20,
                "debug": False,
                "reuse": True,
                "infotree": "original",
            },
        }
    )


class CheckRequest(BaseRequest):
    snippet: Snippet = Field(description="Single snippet to validate")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "snippet": {
                    "custom_id": "mathlib-import-def",
                    "code": "import Mathlib\ndef f := 1",
                },
                "timeout": 20,
                "debug": False,
                "reuse": True,
                "infotree": "original",
            },
        }
    )
