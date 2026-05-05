"""Mock-based unit tests for scripts/linear.py.

These never hit Linear. They use respx to intercept httpx calls.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx
import pytest
import respx

# Make `scripts/linear.py` importable as `linear`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import linear  # noqa: E402


@pytest.fixture
def api_key() -> str:
    return "lin_api_test_key"


@respx.mock
def test_post_graphql_happy_path(api_key: str, capsys: pytest.CaptureFixture[str]) -> None:
    route = respx.post(linear.DEFAULT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"data": {"viewer": {"id": "u_1", "name": "Andy"}}},
            headers={
                "x-ratelimit-requests-remaining": "4998",
                "x-complexity": "3",
            },
        )
    )

    body = linear.post_graphql("query { viewer { id name } }", {}, api_key)

    assert route.called
    assert body == {"data": {"viewer": {"id": "u_1", "name": "Andy"}}}
    err = capsys.readouterr().err
    assert "x-ratelimit-requests-remaining=4998" in err
    assert "x-complexity=3" in err


@respx.mock
def test_post_graphql_raises_on_429(api_key: str) -> None:
    respx.post(linear.DEFAULT_URL).mock(
        return_value=httpx.Response(429, json={}, headers={"retry-after": "12"})
    )
    with pytest.raises(linear.LinearError, match="rate limited"):
        linear.post_graphql("query { __typename }", {}, api_key)


@respx.mock
def test_post_graphql_raises_on_graphql_errors(api_key: str) -> None:
    respx.post(linear.DEFAULT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"errors": [{"message": "bad field"}], "data": None},
        )
    )
    with pytest.raises(linear.LinearError, match="GraphQL errors"):
        linear.post_graphql("query { nope }", {}, api_key)


@respx.mock
def test_post_graphql_sends_authorization_header(api_key: str) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth"] = request.headers.get("authorization", "")
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"data": {"ok": True}})

    respx.post(linear.DEFAULT_URL).mock(side_effect=handler)
    linear.post_graphql("query Q { ok }", {"x": 1}, api_key)

    assert captured["auth"] == api_key  # personal key sent raw, no "Bearer"
    sent = json.loads(captured["body"])
    assert sent["query"] == "query Q { ok }"
    assert sent["variables"] == {"x": 1}


def test_load_document_reads_file(tmp_path: Path) -> None:
    f = tmp_path / "q.graphql"
    f.write_text("query X { __typename }")
    assert linear.load_document(str(f)) == "query X { __typename }"


def test_load_document_passthrough_for_inline_string() -> None:
    assert linear.load_document("query { __typename }") == "query { __typename }"


def test_load_variables_inline() -> None:
    assert linear.load_variables('{"a": 1}') == {"a": 1}


def test_load_variables_from_file(tmp_path: Path) -> None:
    f = tmp_path / "v.json"
    f.write_text('{"a": 2}')
    assert linear.load_variables(f"@{f}") == {"a": 2}


def test_load_variables_none() -> None:
    assert linear.load_variables(None) == {}


def test_auth_header_personal_key_is_raw() -> None:
    assert linear.auth_header("lin_api_abc") == "lin_api_abc"


def test_auth_header_oauth_uses_bearer() -> None:
    assert linear.auth_header("lin_oauth_xyz") == "Bearer lin_oauth_xyz"


def test_auth_header_already_bearer_passthrough() -> None:
    assert linear.auth_header("Bearer foo") == "Bearer foo"
