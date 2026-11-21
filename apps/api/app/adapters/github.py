import httpx

from app.adapters.base import RemoteItem, client_for, required, require_token

API = "https://api.github.com"


class GitHubAdapter:
    """Tracker y repo sobre la API REST de GitHub con token. Config: repo (owner/name), label."""

    default_poll_seconds = 60

    def __init__(self, config: dict, token: str | None, transport: httpx.BaseTransport | None = None):
        self.repo = required(config, "repo")
        if self.repo.count("/") != 1:
            raise ValueError("config.repo debe ser owner/name")
        self.label = config.get("label", "factory")
        self._client = client_for(
            API,
            {
                "Authorization": f"Bearer {require_token(token)}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            transport,
        )

    def __repr__(self) -> str:
        return f"GitHubAdapter(repo={self.repo!r})"

    def _path(self, suffix: str) -> str:
        return f"/repos/{self.repo}{suffix}"

    @staticmethod
    def _to_item(raw: dict) -> RemoteItem:
        return RemoteItem(
            remote_id=str(raw["number"]),
            title=raw["title"],
            body=raw.get("body") or "",
            url=raw.get("html_url"),
            labels=tuple(label["name"] for label in raw.get("labels", [])),
        )

    def fetch_new_items(self) -> list[RemoteItem]:
        resp = self._client.get(
            self._path("/issues"), params={"labels": self.label, "state": "open", "per_page": 100}
        )
        resp.raise_for_status()
        # ponytail: una página de 100; paginar cuando haya más. /issues también devuelve PRs: se descartan.
        return [self._to_item(i) for i in resp.json() if "pull_request" not in i]

    def get_item(self, remote_id: str) -> RemoteItem:
        resp = self._client.get(self._path(f"/issues/{remote_id}"))
        resp.raise_for_status()
        return self._to_item(resp.json())

    def comment(self, remote_id: str, text: str) -> None:
        resp = self._client.post(self._path(f"/issues/{remote_id}/comments"), json={"body": text})
        resp.raise_for_status()

    def set_labels(self, remote_id: str, labels: list[str]) -> None:
        resp = self._client.put(self._path(f"/issues/{remote_id}/labels"), json={"labels": labels})
        resp.raise_for_status()

    def create_branch(self, name: str, base: str) -> None:
        ref = self._client.get(self._path(f"/git/ref/heads/{base}"))
        ref.raise_for_status()
        sha = ref.json()["object"]["sha"]
        resp = self._client.post(self._path("/git/refs"), json={"ref": f"refs/heads/{name}", "sha": sha})
        resp.raise_for_status()

    def open_pr(self, head: str, base: str, title: str, body: str) -> str:
        resp = self._client.post(
            self._path("/pulls"), json={"head": head, "base": base, "title": title, "body": body}
        )
        resp.raise_for_status()
        return str(resp.json()["number"])

    def merge_pr(self, pr_id: str) -> None:
        resp = self._client.put(self._path(f"/pulls/{pr_id}/merge"))
        resp.raise_for_status()

    def get_diff(self, pr_id: str) -> str:
        resp = self._client.get(self._path(f"/pulls/{pr_id}"), headers={"Accept": "application/vnd.github.diff"})
        resp.raise_for_status()
        return resp.text
