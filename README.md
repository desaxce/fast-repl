# Fast REPL

Server to check Lean proofs, via API.

## Usage

```python
uv run python src/fast_repl/repl.py
```

## Contribute

Run `uv run pre-commit install` so that typing/linting run on commit.
Run `uv run pre-commit install --install-hooks`
And `uv run pre-commit install --hook-type pre-push` for tests to run on git push.

To run performance tests: `uv run pytest -m "performance"`. Use -s to view logs.

## Dependencies

- [REPL](https://github.com/leanprover-community/repl)
- [Mathlib](https://github.com/leanprover-community/mathlib4) library
