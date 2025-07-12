import glob
import json
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette import status

INPUT_DIR = os.path.join("tests", "match", "input")
OUTPUT_DIR = os.path.join("tests", "match", "output")


def _collect_test_cases() -> list[pytest.param]:
    inputs = sorted(glob.glob(os.path.join(INPUT_DIR, "*.lean")))
    cases = []
    for inp in inputs:
        name = os.path.splitext(os.path.basename(inp))[0]
        expected = os.path.join(OUTPUT_DIR, f"{name}.json")
        if os.path.exists(expected):
            cases.append(pytest.param(inp, expected, id=name))
    return cases


def assert_eq_mod_time(expected: object, actual: object) -> None:
    """
    Assert that two objects are equal, ignoring the 'time' key in the actual object.
    """
    expected = prune(expected, {"time", "env", "custom_id"})
    actual = prune(actual, {"time", "env", "custom_id"})
    assert (
        expected == actual
    ), f"Expected {json.dumps(expected, indent=2)}, got {json.dumps(actual, indent=2)}"


def prune(obj: object, ignore_keys: set[str]) -> object:
    if isinstance(obj, dict):
        return {
            k: prune(v, ignore_keys) for k, v in obj.items() if k not in ignore_keys
        }
    if isinstance(obj, list):
        return [prune(i, ignore_keys) for i in obj]
    return obj


TEST_CASES = _collect_test_cases()


@pytest.mark.match
@pytest.mark.parametrize("input_file, expected_file", TEST_CASES)
def test_match(client: TestClient, input_file: str, expected_file: str) -> None:
    with open(input_file, "r") as f:
        proof_code = f.read()

    with open(expected_file, "r", encoding="utf-8") as f:
        expected_response = json.load(f)["results"][0]

    if "response" not in expected_response or expected_response["response"] is None:
        pytest.skip(
            f"Expected response does not contain 'response' key in {expected_file}"
        )
    problem_id = os.path.splitext(os.path.basename(input_file))[0]

    data = {
        "snippets": [{"id": problem_id, "code": proof_code}],
        "timeout": 60,
    }

    response = client.post("/check", json=data)
    assert response.status_code == status.HTTP_200_OK
    response = response.json()

    assert "error" not in response, "Response should not contain 'error' key"
    assert "response" in response, "Response should contain 'response' key"
    assert_eq_mod_time(expected_response["response"], response["response"])
