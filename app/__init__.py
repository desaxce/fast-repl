from starlette.datastructures import State

from app.repl_pool import ReplPoolManager

State.pool: ReplPoolManager  # type: ignore
