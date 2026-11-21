"""Prueba real contra github.com/maavcrusoe/meme-demo. Opt-in: GITHUB_REAL=1.

El token sale de `gh auth token` y vive solo en memoria durante el test: no se escribe ni se imprime.
Crea un issue temporal con la etiqueta de fábrica y lo cierra (y borra la etiqueta de prueba) al terminar.
"""

import os
import subprocess
import time
from urllib.parse import quote

import httpx
import pytest

from app.adapters.github import GitHubAdapter

REPO = "maavcrusoe/meme-demo"
TEST_LABEL = "taken by fase2-test"

pytestmark = [
    pytest.mark.github_real,
    pytest.mark.skipif(os.environ.get("GITHUB_REAL") != "1", reason="prueba real: define GITHUB_REAL=1"),
]


def _gh_token() -> str:
    out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True, timeout=30)
    return out.stdout.strip()


def test_round_trip_on_meme_demo():
    token = _gh_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    with httpx.Client(base_url="https://api.github.com", headers=headers, timeout=20) as http:
        created = http.post(
            f"/repos/{REPO}/issues",
            json={"title": "[fase2-test] borrar", "body": "Prueba automática de Fase 2", "labels": ["factory"]},
        )
        created.raise_for_status()
        number = str(created.json()["number"])
        try:
            adapter = GitHubAdapter({"repo": REPO}, token)
            # La lista de GitHub tarda unos segundos en reflejar un issue nuevo (medido: ~6 s).
            deadline = time.monotonic() + 45
            while number not in {item.remote_id for item in adapter.fetch_new_items()}:
                assert time.monotonic() < deadline, "el issue de prueba no aparece en el sondeo"
                time.sleep(2)

            adapter.set_labels(number, ["factory", TEST_LABEL])
            assert TEST_LABEL in adapter.get_item(number).labels

            adapter.comment(number, "Comentario de prueba del hub")
            comments = http.get(f"/repos/{REPO}/issues/{number}/comments")
            comments.raise_for_status()
            assert any("Comentario de prueba del hub" in c["body"] for c in comments.json())
        finally:
            http.patch(f"/repos/{REPO}/issues/{number}", json={"state": "closed"})
            http.delete(f"/repos/{REPO}/labels/{quote(TEST_LABEL)}")
