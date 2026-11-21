"""Interfaces de tracker y repo. Un adapter nuevo = una clase que las implemente."""

import re
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

REF_RE = re.compile(r"^[\w.\-]+$")


@dataclass(frozen=True)
class RemoteItem:
    remote_id: str
    title: str
    body: str
    url: str | None
    labels: tuple[str, ...]


class TrackerAdapter(Protocol):
    def fetch_new_items(self) -> list[RemoteItem]: ...
    def get_item(self, remote_id: str) -> RemoteItem: ...
    def comment(self, remote_id: str, text: str) -> None: ...
    def set_labels(self, remote_id: str, labels: list[str]) -> None:
        """Reemplaza el conjunto completo de etiquetas del remoto."""


class RepoAdapter(Protocol):
    def create_branch(self, name: str, base: str) -> None: ...
    def open_pr(self, head: str, base: str, title: str, body: str) -> str: ...
    def merge_pr(self, pr_id: str) -> None: ...
    def get_diff(self, pr_id: str) -> str: ...


def required(config: dict[str, Any], key: str) -> str:
    value = config.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"config.{key} requerido")
    return value.strip()


def require_token(token: str | None) -> str:
    if not token:
        raise ValueError("token requerido para este proveedor")
    return token


def client_for(base_url: str, headers: dict[str, str], transport: httpx.BaseTransport | None) -> httpx.Client:
    return httpx.Client(base_url=base_url, headers=headers, timeout=20, transport=transport)
