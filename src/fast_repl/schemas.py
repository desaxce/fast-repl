from typing import List, Literal

from pydantic import BaseModel, Field


class Snippet(BaseModel):
    id: str = Field(..., description="Opaque identifier for tracing the snippet")
    code: str = Field(..., description="Lean 4 snippet or proof attempt text")


class CheckRequest(BaseModel):
    snippets: List[Snippet] = Field(
        ..., description="List of snippets to validate (batch or single element)"
    )
    timeout: int = Field(
        5, description="Maximum time in seconds before aborting the check", ge=0
    )
    debug: bool = Field(
        False, description="Include CPU/RAM usage and REPL instance ID in the response"
    )
    reuse: bool = Field(
        True, description="Whether to attempt using a pooled REPL if available"
    )
    infotree: Literal["none", "short", "full"] = Field(
        "none",
        description="Level of detail for the InfoTree: 'none' | 'short' | 'full'",
    )

    class Config:
        schema_extra = {
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
