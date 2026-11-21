import logging
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import delete, func, select

from app.adapters import ADAPTERS
from app.adapters.base import RemoteItem
from app.db import SessionLocal
from app.models import Project, ProjectIntegration, TrackerLink, WorkItem, WorkItemEvent
from app.services.crypto import decrypt_token, encrypt_token
from app.services.poller import poll_due
from app.services.tracker_sync import poll_integration, reconcile_labels, set_taken_by
from tests.fakes import FakeAzureDevOps, FakeGitHub

SLUG = "fase2-demo"


@pytest.fixture
def db():
    with SessionLocal() as session:
        project = session.scalar(select(Project).where(Project.slug == SLUG))
        if project is None:
            project = Project(slug=SLUG, name="Fase 2")
            session.add(project)
            session.commit()
        _clean(session, project.id)
        yield session
        _clean(session, project.id)


def _clean(session, project_id: int) -> None:
    item_ids = select(WorkItem.id).where(WorkItem.project_id == project_id)
    session.execute(delete(WorkItemEvent).where(WorkItemEvent.work_item_id.in_(item_ids)))
    session.execute(delete(TrackerLink).where(TrackerLink.project_id == project_id))
    session.execute(delete(WorkItem).where(WorkItem.project_id == project_id))
    session.execute(delete(ProjectIntegration).where(ProjectIntegration.project_id == project_id))
    session.commit()


def _integration(db, provider: str, config: dict, token: str | None = "ghp_TOKEN_SECRETO") -> ProjectIntegration:
    project = db.scalar(select(Project).where(Project.slug == SLUG))
    integ = ProjectIntegration(
        project_id=project.id,
        provider=provider,
        config=config,
        token_encrypted=encrypt_token(token) if token else None,
    )
    db.add(integ)
    db.commit()
    return integ


def _patch_github(monkeypatch, transport: httpx.MockTransport) -> None:
    """Sustituye el GitHubAdapter por una subclase que usa el transporte falso."""
    from app.adapters.github import GitHubAdapter

    class Patched(GitHubAdapter):
        def __init__(self, config, token, transport_=None):
            super().__init__(config, token, transport=transport)

    monkeypatch.setitem(ADAPTERS, "github", Patched)


def _github(monkeypatch, fake: FakeGitHub) -> None:
    _patch_github(monkeypatch, httpx.MockTransport(fake.handler))


def _starts(calls: list[int]):
    return lambda item_id: calls.append(item_id)


def _count_items(db, project_slug: str = SLUG) -> int:
    project = db.scalar(select(Project).where(Project.slug == project_slug))
    return db.scalar(select(func.count()).select_from(WorkItem).where(WorkItem.project_id == project.id))


def test_poll_ingests_issue_once_and_skips_pull_requests(db, monkeypatch):
    fake = FakeGitHub()
    fake.add_issue(1, "Meme nuevo", ["factory"], "Texto del issue")
    fake.add_pull_request(2, ["factory"])
    _github(monkeypatch, fake)
    integ = _integration(db, "github", {"repo": "maavcrusoe/meme-demo"})
    started: list[int] = []

    poll_integration(db, integ, _starts(started))
    poll_integration(db, integ, _starts(started))  # segundo sondeo: nada nuevo

    assert _count_items(db) == 1
    item = db.scalar(select(WorkItem).where(WorkItem.idempotency_key == "github:1"))
    assert item.source == "github"
    assert item.original_payload["projectId"] == SLUG
    assert started == [item.id]
    link = db.scalar(select(TrackerLink).where(TrackerLink.work_item_id == item.id))
    assert (link.provider, link.remote_id) == ("github", "1")


def test_hub_wins_reverts_manual_remote_label_and_keeps_others(db, monkeypatch):
    fake = FakeGitHub()
    fake.add_issue(1, "Meme", ["factory"])
    _github(monkeypatch, fake)
    integ = _integration(db, "github", {"repo": "maavcrusoe/meme-demo"})
    poll_integration(db, integ, lambda _: None)
    item = db.scalar(select(WorkItem).where(WorkItem.idempotency_key == "github:1"))

    set_taken_by(db, item, "alice", actor="test")
    reconcile_labels(db, integ, _adapter_for(integ, fake))
    assert sorted(fake.issues[1]["labels"]) == ["factory", "taken by alice"]

    # Cambio manual en el remoto: se añade "taken by bob" y una etiqueta ajena.
    fake.issues[1]["labels"] = ["factory", "taken by alice", "taken by bob", "bug"]
    reconcile_labels(db, integ, _adapter_for(integ, fake))

    assert sorted(fake.issues[1]["labels"]) == ["bug", "factory", "taken by alice"]
    kinds = [e.kind for e in db.scalars(select(WorkItemEvent).where(WorkItemEvent.work_item_id == item.id))]
    assert "label_reverted" in kinds
    reverted = db.scalar(
        select(WorkItemEvent).where(WorkItemEvent.work_item_id == item.id, WorkItemEvent.kind == "label_reverted")
    )
    assert reverted.actor == "hub-sync"


def test_broken_link_does_not_stop_sync_of_other_links(db, monkeypatch, caplog):
    fake = FakeGitHub()
    fake.add_issue(1, "Roto", ["factory"])
    fake.add_issue(2, "Sano", ["factory"])
    _github(monkeypatch, fake)
    integ = _integration(db, "github", {"repo": "maavcrusoe/meme-demo"})
    poll_integration(db, integ, lambda _: None)
    del fake.issues[1]  # el issue 1 existe al enlazar y luego desaparece del remoto
    fake.issues[2]["labels"] = ["factory", "taken by bob"]  # cambio manual en el issue sano

    with caplog.at_level(logging.WARNING):
        assert reconcile_labels(db, integ, _adapter_for(integ, fake)) == 1

    assert fake.issues[2]["labels"] == ["factory"]
    assert "sincronización de etiquetas fallida provider=github" in caplog.text


def test_manual_removal_of_factory_label_is_restored(db, monkeypatch):
    fake = FakeGitHub()
    fake.add_issue(1, "Meme", ["factory"])
    _github(monkeypatch, fake)
    integ = _integration(db, "github", {"repo": "maavcrusoe/meme-demo"})
    poll_integration(db, integ, lambda _: None)

    fake.issues[1]["labels"] = []
    reconcile_labels(db, integ, _adapter_for(integ, fake))

    assert fake.issues[1]["labels"] == ["factory"]


def test_origin_marker_stops_repeated_writes_and_events(db, monkeypatch):
    fake = FakeGitHub()
    fake.add_issue(1, "Meme", ["factory"])
    _github(monkeypatch, fake)
    integ = _integration(db, "github", {"repo": "maavcrusoe/meme-demo"})
    poll_integration(db, integ, lambda _: None)
    item = db.scalar(select(WorkItem).where(WorkItem.idempotency_key == "github:1"))
    set_taken_by(db, item, "alice", actor="test")
    reconcile_labels(db, integ, _adapter_for(integ, fake))
    writes, events = len(fake.label_writes), db.scalar(select(func.count()).select_from(WorkItemEvent))

    assert reconcile_labels(db, integ, _adapter_for(integ, fake)) == 0
    assert len(fake.label_writes) == writes
    assert db.scalar(select(func.count()).select_from(WorkItemEvent)) == events


def test_new_adapter_is_one_class_and_plugs_into_poller(db, monkeypatch):
    class EchoTracker:
        default_poll_seconds = 60
        seen: list[str] = []

        def __init__(self, config, token, transport=None):
            self.config = config

        def fetch_new_items(self):
            return [RemoteItem("T-1", "Desde eco", "cuerpo", None, ("factory",))]

        def get_item(self, remote_id):
            return RemoteItem(remote_id, "Desde eco", "cuerpo", None, ("factory",))

        def comment(self, remote_id, text):
            EchoTracker.seen.append(text)

        def set_labels(self, remote_id, labels):
            EchoTracker.seen.append(",".join(labels))

    monkeypatch.setitem(ADAPTERS, "echo", EchoTracker)
    _integration(db, "echo", {}, token=None)
    started: list[int] = []

    assert poll_due(db, datetime.now(UTC), _starts(started)) == 1
    item = db.scalar(select(WorkItem).where(WorkItem.idempotency_key == "echo:T-1"))
    assert item.source == "echo"
    assert started == [item.id]


def test_poll_respects_interval_and_failure_logs_no_token(db, monkeypatch, caplog):
    token = "ghp_TOKEN_QUE_NO_DEBE_SALIR"
    transport = httpx.MockTransport(lambda request: httpx.Response(500, json={"message": "boom"}))
    _patch_github(monkeypatch, transport)
    integ = _integration(db, "github", {"repo": "maavcrusoe/meme-demo"}, token=token)
    integ.last_polled_at = datetime.now(UTC) - timedelta(seconds=5)
    db.commit()

    with caplog.at_level(logging.DEBUG):
        assert poll_due(db, datetime.now(UTC)) == 0  # 5 s < 60 s: no toca
        integ.last_polled_at = None
        db.commit()
        assert poll_due(db, datetime.now(UTC)) == 0  # falla: se registra y sigue

    assert "sondeo fallido provider=github" in caplog.text
    assert token not in caplog.text
    raw = db.execute(select(ProjectIntegration.token_encrypted)).scalars().all()
    assert all(token not in value for value in raw if value)


def test_stored_token_is_ciphertext_and_roundtrips(db):
    integ = _integration(db, "github", {"repo": "maavcrusoe/meme-demo"}, token="ghp_SECRETO_123")
    db.refresh(integ)
    assert integ.token_encrypted != "ghp_SECRETO_123"
    assert "ghp_SECRETO_123" not in integ.token_encrypted
    assert decrypt_token(integ.token_encrypted) == "ghp_SECRETO_123"
    assert "ghp_SECRETO" not in repr(integ)


def test_azuredevops_adapter_maps_wiql_tags_and_patches_with_json_patch(monkeypatch):
    from app.adapters.azuredevops import AzureDevOpsAdapter

    fake = FakeAzureDevOps()
    fake.add(7, "Meme AzDO", "factory; urgente", "<p>Hola &amp; adiós</p>")
    fake.add(8, "Otro", "bug")
    adapter = AzureDevOpsAdapter(
        {"organization": "org", "project": "proj"}, "pat-token", transport=httpx.MockTransport(fake.handler)
    )

    items = adapter.fetch_new_items()
    assert [(i.remote_id, i.title, i.labels) for i in items] == [("7", "Meme AzDO", ("factory", "urgente"))]
    assert items[0].body == "Hola & adiós"

    adapter.set_labels("7", ["factory", "taken by alice"])
    patch = fake.requests[-1]
    assert patch.headers["Content-Type"] == "application/json-patch+json"
    assert fake.patches[-1][0]["value"] == "factory; taken by alice"


def test_github_pr_operations_hit_expected_endpoints():
    from app.adapters.github import GitHubAdapter

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "abc"}})
        if request.url.path.endswith("/pulls") and request.method == "POST":
            return httpx.Response(201, json={"number": 9})
        if request.url.path.endswith("/pulls/9"):
            return httpx.Response(200, text="diff --git a/x b/x")
        return httpx.Response(200, json={})

    adapter = GitHubAdapter(
        {"repo": "maavcrusoe/meme-demo"}, "tok", transport=httpx.MockTransport(handler)
    )
    adapter.create_branch("factory/x", "main")
    assert adapter.open_pr("factory/x", "main", "t", "b") == "9"
    assert adapter.get_diff("9") == "diff --git a/x b/x"
    assert seen[-1].headers["Accept"] == "application/vnd.github.diff"


def _adapter_for(integ: ProjectIntegration, fake: FakeGitHub):
    from app.adapters.github import GitHubAdapter

    return GitHubAdapter(integ.config, "x", transport=httpx.MockTransport(fake.handler))
