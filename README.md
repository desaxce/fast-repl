# Fast REPL

Server to check Lean proofs, via API.
Resource limits only work on Linux.

## Usage

```python
uv run uvicorn src.fast_repl.main:app
```

And test with:
```
curl -X POST http://localhost:8000/repl/ \
  -H "Content-Type: application/json" \
  -d '{"cmd":"#check 1 + 1"}'
```

Environment variables to configure the REPL pool:

```
REPL_POOL_MAX_REPLS   # Maximum number of concurrently running REPLs
REPL_POOL_MAX_REUSE   # Maximum number of times to reuse a REPL
REPL_POOL_MEMORY_GB   # Memory limit for each REPL
REPL_POOL_INIT_REPLS  # Number of REPLs created at startup
```

## Contribute

Run `uv run pre-commit install` so that typing/linting run on commit.
Run `uv run pre-commit install --install-hooks`
And `uv run pre-commit install --hook-type pre-push` for tests to run on git push.

To run performance tests: `uv run pytest -m "performance"`. Use -s to view logs.

## Dependencies

- [REPL](https://github.com/leanprover-community/repl)
- [Mathlib](https://github.com/leanprover-community/mathlib4) library
