"""mark_ready contra GraphQL: GitHub responde 200 con `errors` cuando no puede quitar el borrador."""

import httpx
import pytest

from app.adapters.github import GitHubAdapter


def _adapter(graphql_body: dict, calls: list[str]) -> GitHubAdapter:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == "/graphql":
            return httpx.Response(200, json=graphql_body)
        return httpx.Response(200, json={"node_id": "PR_x", "draft": True, "head": {"sha": "a" * 40}})

    return GitHubAdapter({"repo": "o/r"}, "token", transport=httpx.MockTransport(handler))


def test_mark_ready_raises_when_graphql_returns_errors():
    calls: list[str] = []
    adapter = _adapter({"errors": [{"message": "Resource not accessible by personal access token"}]}, calls)
    with pytest.raises(ValueError):
        adapter.mark_ready("6")
    assert "/graphql" in calls


def test_mark_ready_posts_mutation_for_draft():
    calls: list[str] = []
    _adapter({"data": {"markPullRequestReadyForReview": {"pullRequest": {"isDraft": False}}}}, calls).mark_ready("6")
    assert calls == ["/repos/o/r/pulls/6", "/graphql"]
