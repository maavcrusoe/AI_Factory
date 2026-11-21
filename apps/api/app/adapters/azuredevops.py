import base64
import html
import json
import re
from urllib.parse import quote

import httpx

from app.adapters.base import REF_RE, RemoteItem, client_for, required, require_token

# Versiones de API sin verificar contra una organización real (pendiente, ver PR).
API_VERSION = "7.1"
COMMENTS_API_VERSION = "7.0-preview.3"
FIELDS = "System.Title,System.Description,System.Tags"
NULL_SHA = "0" * 40


def _split_tags(tags: str | None) -> tuple[str, ...]:
    return tuple(t.strip() for t in (tags or "").split(";") if t.strip())


def _plain(description: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", description or "")).strip()


class AzureDevOpsAdapter:
    """Work items y repos de Azure DevOps por REST con PAT. Config: organization, project, repo, label."""

    default_poll_seconds = 300

    def __init__(self, config: dict, token: str | None, transport: httpx.BaseTransport | None = None):
        self.organization = required(config, "organization")
        self.project = required(config, "project")
        self.repo = config.get("repo", self.project)
        self.label = config.get("label", "factory")
        if not REF_RE.match(self.label):
            raise ValueError("config.label solo admite letras, números, guion, punto y guion bajo")
        basic = base64.b64encode(f":{require_token(token)}".encode()).decode()
        self._client = client_for(
            f"https://dev.azure.com/{quote(self.organization)}/{quote(self.project)}/_apis",
            {"Authorization": f"Basic {basic}", "Accept": "application/json"},
            transport,
        )

    def __repr__(self) -> str:
        return f"AzureDevOpsAdapter(organization={self.organization!r}, project={self.project!r})"

    @staticmethod
    def _to_item(raw: dict) -> RemoteItem:
        fields = raw.get("fields", {})
        return RemoteItem(
            remote_id=str(raw["id"]),
            title=fields.get("System.Title", ""),
            body=_plain(fields.get("System.Description")),
            url=raw.get("_links", {}).get("html", {}).get("href"),
            labels=_split_tags(fields.get("System.Tags")),
        )

    def fetch_new_items(self) -> list[RemoteItem]:
        wiql = (
            "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = @project "
            f"AND [System.Tags] CONTAINS '{self.label}' AND [System.State] <> 'Closed'"
        )
        resp = self._client.post(f"/wit/wiql?api-version={API_VERSION}", json={"query": wiql})
        resp.raise_for_status()
        ids = [str(w["id"]) for w in resp.json().get("workItems", [])][:200]
        if not ids:
            return []
        resp = self._client.get(f"/wit/workitems?ids={','.join(ids)}&fields={FIELDS}&api-version={API_VERSION}")
        resp.raise_for_status()
        return [self._to_item(w) for w in resp.json().get("value", [])]

    def get_item(self, remote_id: str) -> RemoteItem:
        resp = self._client.get(f"/wit/workitems/{remote_id}?fields={FIELDS}&api-version={API_VERSION}")
        resp.raise_for_status()
        return self._to_item(resp.json())

    def comment(self, remote_id: str, text: str) -> None:
        resp = self._client.post(
            f"/wit/workItems/{remote_id}/comments?api-version={COMMENTS_API_VERSION}", json={"text": text}
        )
        resp.raise_for_status()

    def set_labels(self, remote_id: str, labels: list[str]) -> None:
        patch = [{"op": "add", "path": "/fields/System.Tags", "value": "; ".join(labels)}]
        resp = self._client.patch(
            f"/wit/workitems/{remote_id}?api-version={API_VERSION}",
            content=json.dumps(patch).encode(),
            headers={"Content-Type": "application/json-patch+json"},
        )
        resp.raise_for_status()

    def create_branch(self, name: str, base: str) -> None:
        ref = self._client.get(f"/git/repositories/{self.repo}/refs?filter=heads/{base}&api-version={API_VERSION}")
        ref.raise_for_status()
        sha = ref.json()["value"][0]["objectId"]
        resp = self._client.post(
            f"/git/repositories/{self.repo}/refs?api-version={API_VERSION}",
            json=[{"name": f"refs/heads/{name}", "oldObjectId": NULL_SHA, "newObjectId": sha}],
        )
        resp.raise_for_status()

    def open_pr(self, head: str, base: str, title: str, body: str) -> str:
        resp = self._client.post(
            f"/git/repositories/{self.repo}/pullrequests?api-version={API_VERSION}",
            json={
                "sourceRefName": f"refs/heads/{head}",
                "targetRefName": f"refs/heads/{base}",
                "title": title,
                "description": body,
            },
        )
        resp.raise_for_status()
        return str(resp.json()["pullRequestId"])

    def merge_pr(self, pr_id: str) -> None:
        pr = self._client.get(f"/git/repositories/{self.repo}/pullrequests/{pr_id}?api-version={API_VERSION}")
        pr.raise_for_status()
        commit = pr.json()["lastMergeSourceCommit"]["commitId"]
        resp = self._client.patch(
            f"/git/repositories/{self.repo}/pullrequests/{pr_id}?api-version={API_VERSION}",
            json={"status": "completed", "lastMergeSourceCommit": {"commitId": commit}},
        )
        resp.raise_for_status()

    def get_diff(self, pr_id: str) -> str:
        # Pendiente: AzDO no tiene endpoint de diff directo; se decide con una organización real.
        raise NotImplementedError("AzureDevOps get_diff: pendiente")
