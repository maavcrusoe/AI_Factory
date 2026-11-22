"""Cliente HTTP del hub para el pipeline. Solo stdlib.

- Los errores 4xx se lanzan como HubError (no se reintentan).
- Las subidas (eventos y artefactos) que fallan por red se guardan en un outbox local
  (`outbox.jsonl`) y se reenvían con `flush_outbox()` al reanudar o al empezar cada etapa.
- El token se lee de FACTORY_TOKEN y nunca se escribe en disco ni en logs.
"""

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class HubError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(f"hub respondió {status}: {detail}")
        self.status = status
        self.detail = detail


class HubClient:
    def __init__(self, base_url: str, token: str, outbox: Path, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.outbox = outbox
        self.timeout = timeout

    def __repr__(self) -> str:  # nunca mostrar el token
        return f"HubClient(base_url={self.base_url!r})"

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = None
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        req = urllib.request.Request(f"{self.base_url}{path}", data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise HubError(exc.code, detail) from None

    # --- lectura y control del claim -------------------------------------------------
    def queue(self, project_id: str) -> list[dict[str, Any]]:
        return self._request("GET", f"/api/v1/projects/{project_id}/queue")

    def item(self, item_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/inputs/{item_id}")

    def claim(self, item_id: int) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/work/{item_id}/claim")

    def heartbeat(self, item_id: int, state: str, message: str) -> dict[str, Any]:
        return self._request(
            "POST", f"/api/v1/work/{item_id}/heartbeat", {"state": state, "message": message[:1000]}
        )

    def release(self, item_id: int, reason: str) -> dict[str, Any]:
        return self._request("POST", f"/api/v1/work/{item_id}/release", {"reason": reason[:500]})

    def complete(self, item_id: int, pr_url: str, pr_number: int) -> dict[str, Any]:
        return self._request(
            "POST", f"/api/v1/work/{item_id}/complete", {"pr_url": pr_url, "pr_number": pr_number}
        )

    def gate_report(
        self,
        item_id: int,
        *,
        sha: str,
        passed: bool,
        meaning: str,
        planned: bool,
        touched_paths: list[str],
        review_findings: list[str],
    ) -> dict[str, Any]:
        """Gate final sobre el SHA del PR. Sin outbox: si falla, la reanudación lo repite."""
        return self._request(
            "POST",
            f"/api/v1/work/{item_id}/gate-report",
            {
                "sha": sha,
                "result": "passed" if passed else "failed",
                "meaning_change": meaning,
                "planned": planned,
                "touched_paths": touched_paths[:500],
                "review_findings": [f[:1000] for f in review_findings][:50],
            },
        )

    # --- subidas: pasan por el outbox si la red corta -------------------------------
    def event(self, item_id: int, kind: str, message: str, detail: dict[str, Any] | None = None) -> None:
        self._upload(f"/api/v1/work/{item_id}/events", {"kind": kind, "message": message[:2000], "detail": detail})

    def artifact(
        self, item_id: int, *, stage: str, round_no: int, kind: str, client_key: str, content: str
    ) -> None:
        self._upload(
            f"/api/v1/work/{item_id}/artifacts",
            {
                "stage": stage,
                "round": round_no,
                "kind": kind,
                "client_key": client_key,
                "content": content,
            },
        )

    def _upload(self, path: str, body: dict[str, Any]) -> None:
        try:
            self._request("POST", path, body)
        except HubError:
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            self._spool(path, body)

    def _spool(self, path: str, body: dict[str, Any]) -> None:
        self.outbox.parent.mkdir(parents=True, exist_ok=True)
        with self.outbox.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"path": path, "body": body}, ensure_ascii=False) + "\n")

    def pending(self) -> int:
        if not self.outbox.exists():
            return 0
        return sum(1 for line in self.outbox.read_text(encoding="utf-8").splitlines() if line.strip())

    def flush_outbox(self) -> int:
        """Reenvía lo pendiente en orden. Se para ante un fallo de red y deja el resto. Devuelve enviados."""
        if not self.outbox.exists():
            return 0
        lines = [line for line in self.outbox.read_text(encoding="utf-8").splitlines() if line.strip()]
        sent = 0
        for index, line in enumerate(lines):
            entry = json.loads(line)
            try:
                self._request("POST", entry["path"], entry["body"])
            except HubError as exc:
                if exc.status >= 500:
                    self._keep(lines[index:])
                    return sent
                # 4xx: el hub ya no lo acepta (p. ej. perdimos el claim). Se descarta.
                continue
            except (urllib.error.URLError, TimeoutError, OSError):
                self._keep(lines[index:])
                return sent
            sent += 1
        self._keep([])
        return sent

    def _keep(self, lines: list[str]) -> None:
        if lines:
            self.outbox.write_text("\n".join(lines) + "\n", encoding="utf-8")
        elif self.outbox.exists():
            self.outbox.unlink()
