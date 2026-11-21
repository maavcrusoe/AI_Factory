"""Remotos falsos en memoria para tests: GitHub y Azure DevOps por httpx.MockTransport."""

import json

import httpx


class FakeGitHub:
    """Repo GitHub mínimo: issues con etiquetas, un PR que no debe ingerirse, comentarios."""

    def __init__(self) -> None:
        self.issues: dict[int, dict] = {}
        self.comments: list[tuple[int, str]] = []
        self.label_writes: list[tuple[int, list[str]]] = []
        self.requests: list[httpx.Request] = []

    def add_issue(self, number: int, title: str, labels: list[str], body: str = "") -> None:
        self.issues[number] = {"number": number, "title": title, "body": body, "labels": labels, "state": "open"}

    def add_pull_request(self, number: int, labels: list[str]) -> None:
        self.issues[number] = {
            "number": number,
            "title": "PR",
            "body": "",
            "labels": labels,
            "state": "open",
            "pull_request": {"url": "x"},
        }

    def _view(self, issue: dict) -> dict:
        view = {k: v for k, v in issue.items() if k != "labels"}
        view["labels"] = [{"name": name} for name in issue["labels"]]
        view["html_url"] = f"https://github.com/maavcrusoe/meme-demo/issues/{issue['number']}"
        return view

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        parts = request.url.path.strip("/").split("/")  # repos/o/r/issues/...
        if request.method == "GET" and parts[-1] == "issues":
            wanted = request.url.params.get("labels")
            found = [
                self._view(i)
                for i in self.issues.values()
                if i["state"] == "open" and (wanted is None or wanted in i["labels"])
            ]
            return httpx.Response(200, json=found)
        number = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
        if request.method == "GET" and number is not None and len(parts) == 5:
            return httpx.Response(200, json=self._view(self.issues[number]))
        if request.method == "PUT" and parts[-1] == "labels":
            labels = json.loads(request.content)["labels"]
            self.issues[number]["labels"] = list(labels)
            self.label_writes.append((number, list(labels)))
            return httpx.Response(200, json=[{"name": n} for n in labels])
        if request.method == "POST" and parts[-1] == "comments":
            self.comments.append((number, json.loads(request.content)["body"]))
            return httpx.Response(201, json={"id": 1})
        return httpx.Response(404, json={"message": "Not Found"})


class FakeAzureDevOps:
    """Work items de AzDO: WIQL devuelve ids con la etiqueta; PATCH reemplaza System.Tags."""

    def __init__(self) -> None:
        self.items: dict[int, dict] = {}
        self.patches: list[list[dict]] = []
        self.requests: list[httpx.Request] = []

    def add(self, item_id: int, title: str, tags: str, description: str = "") -> None:
        self.items[item_id] = {"id": item_id, "title": title, "tags": tags, "description": description}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if request.method == "POST" and path.endswith("/wit/wiql"):
            query = json.loads(request.content)["query"]
            tag = query.split("CONTAINS '")[1].split("'")[0]
            ids = [{"id": i} for i, it in self.items.items() if tag in _split(it["tags"])]
            return httpx.Response(200, json={"workItems": ids})
        if request.method == "GET" and path.endswith("/wit/workitems"):
            ids = [int(x) for x in request.url.params["ids"].split(",")]
            return httpx.Response(200, json={"value": [self._view(self.items[i]) for i in ids]})
        if path.split("/")[-1].split("?")[0].isdigit() or "/wit/workitems/" in path:
            item_id = int(path.rstrip("/").split("/")[-1])
            if request.method == "GET":
                return httpx.Response(200, json=self._view(self.items[item_id]))
            if request.method == "PATCH":
                ops = json.loads(request.content)
                self.patches.append(ops)
                self.items[item_id]["tags"] = ops[0]["value"]
                return httpx.Response(200, json=self._view(self.items[item_id]))
        return httpx.Response(404, json={"message": "not found"})

    @staticmethod
    def _view(item: dict) -> dict:
        return {
            "id": item["id"],
            "fields": {
                "System.Title": item["title"],
                "System.Description": item["description"],
                "System.Tags": item["tags"],
            },
            "_links": {"html": {"href": f"https://dev.azure.com/org/proj/_workitems/edit/{item['id']}"}},
        }


def _split(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(";") if t.strip()]
