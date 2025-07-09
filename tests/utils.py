from typing import Any, Iterable


def _strip_keys(obj: Any, ignore: Iterable[str]) -> Any:
    """Recursively remove any dict keys in `ignore` from obj."""
    if isinstance(obj, dict):
        return {k: _strip_keys(v, ignore) for k, v in obj.items() if k not in ignore}
    if isinstance(obj, list):
        return [_strip_keys(v, ignore) for v in obj]
    return obj


def assert_json_equal(
    actual: Any, expected: Any, *, ignore_keys: Iterable[str] = ()
) -> None:
    """
    Assert that two JSON-like structures are equal, ignoring any keys in ignore_keys.
    Usage:
        assert_json_equal(resp.json(), expected, ignore_keys=["time", "cpu_max"])
    """
    a = _strip_keys(actual, ignore_keys)
    e = _strip_keys(expected, ignore_keys)
    assert a == e, f"\n=== ACTUAL ===\n{a!r}\n=== EXPECTED ===\n{e!r}"
