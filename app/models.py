from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel


class Repl(BaseModel):
    uuid: UUID
    created_at: datetime
    max_uses: int
    max_mem: int
    header: str
    # TODO: include status for repl


class Proof(BaseModel):
    uuid: UUID
    id: str
    code: str
    diagnostics: Optional[dict[str, Any]] = None
    response: Optional[dict[str, Any]] = None
    repl_uuid: UUID
