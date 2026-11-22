"""Tests del pipeline con git real (origin bare local), checks.sh real y un agente simulado.

No llama a Claude ni a GitHub: el runner y el publicador son falsos, y el transporte del hub también.
Ejecutar: python -m unittest discover -s .claude/skills/factory/scripts
"""

import re
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path

import pipeline as pl
import pr as pr_mod
from hub import HubClient, HubError

PR_URL = "https://github.com/maavcrusoe/meme-demo/pull/9"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


class FakeTransport:
    """Sustituye `HubClient._request`. Registra llamadas; puede simular cortes de red en subidas."""

    def __init__(self, item_id: int = 1):
        self.item_id = item_id
        self.calls: list[tuple[str, str, dict | None]] = []
        self.network_failures = 0  # subidas que fallan por red antes de volver
        self.heartbeat_status: int | None = None  # p. ej. 409 para simular claim perdido
        self.claim_status: int | None = None  # 409 = el item lo tiene otro dev
        self.item_status = "QUEUED"  # estado que devuelve GET /inputs/{id}
        self.lost_claim_on_heartbeat = False

    def __call__(self, method: str, path: str, body: dict | None = None):
        self.calls.append((method, path, body))
        if method == "GET" and path.endswith("/queue"):
            return [{"id": self.item_id}]
        if method == "POST" and path.endswith("/claim"):
            if self.claim_status:
                raise HubError(self.claim_status, "ya cogido por otro")
            return {
                "id": self.item_id,
                "title": "Añade un botón de limpiar",
                "body": "Un botón que vacía el texto.",
                "tracker": {"provider": "github", "remote_id": "5", "remote_url": None},
            }
        if path.endswith("/heartbeat") and self.heartbeat_status:
            raise HubError(self.heartbeat_status, "ya cogido por otro")
        if (path.endswith("/events") or path.endswith("/artifacts")) and self.network_failures > 0:
            self.network_failures -= 1
            raise urllib.error.URLError("corte de red simulado")
        if path.endswith("/complete") and body is not None:
            return {"status": "PR_OPEN"}
        if method == "GET" and path.startswith("/api/v1/inputs/"):
            return {"status": self.item_status}
        return {}

    def paths(self, suffix: str) -> list[dict | None]:
        return [b for m, p, b in self.calls if p.endswith(suffix)]


class ScriptedRunner:
    """Agente simulado. `script[agente](cwd, prompt, nº de llamada a ese agente) -> salida`."""

    def __init__(self, script: dict):
        self.script = script
        self.calls: list[str] = []

    def __call__(self, agent: str, prompt: str, cwd: Path, log: Path) -> str:
        self.calls.append(agent)
        n = self.calls.count(agent)
        output = self.script[agent](cwd, prompt, n)
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(output, encoding="utf-8")
        return output


def _item_id(prompt: str) -> int:
    return int(re.search(r"Petición #(\d+)", prompt).group(1))


def planner(cwd: Path, prompt: str, _n: int) -> str:
    spec = cwd / ".factory" / "specs" / str(_item_id(prompt)) / "spec.md"
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("# Spec\n- botón limpiar vacía el campo\n", encoding="utf-8")
    return "spec escrita"


def approve(_cwd: Path, _prompt: str, _n: int) -> str:
    return "todo bien\nVERDICT: APPROVE"


def builder_fixes_on(round_no: int):
    """El builder crea ok.flag (gate verde) solo en la ronda indicada."""

    def _builder(cwd: Path, _prompt: str, n: int) -> str:
        if n == round_no:
            (cwd / "ok.flag").write_text("1", encoding="utf-8")
        return "cambios hechos"

    return _builder


class PipelineFlowTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        origin = root / "origin.git"
        repo = root / "meme-demo"
        subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
        subprocess.run(["git", "clone", str(origin), str(repo)], check=True, capture_output=True)
        (repo / ".factory").mkdir()
        (repo / ".factory" / "config.yaml").write_text(
            "projectId: meme-demo\nhubUrl: http://hub.test\n", encoding="utf-8"
        )
        (repo / "checks.sh").write_text("#!/usr/bin/env bash\ntest -f ok.flag && echo ok\n", encoding="utf-8")
        _git(repo, "checkout", "-b", "main")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "base")
        _git(repo, "push", "-u", "origin", "main")
        self.repo = repo
        self.home = root / "meme-demo.factory"
        self.cfg = pl.Config.load(repo, self.home)
        self.published: list[tuple[str, str]] = []

    def tearDown(self):
        self._tmp.cleanup()

    def _publisher(self, worktree: Path, branch: str, title: str, body_file: Path):
        pr_mod.push_branch(worktree, branch)  # push real a origin local; la PR es simulada
        self.published.append((branch, body_file.read_text(encoding="utf-8")))
        return PR_URL, 9

    def _pipeline(self, transport: FakeTransport, runner: ScriptedRunner) -> pl.Pipeline:
        hub = HubClient("http://hub.test", "fct_test", self.home / "runs" / "1" / "outbox.jsonl")
        hub._request = transport  # type: ignore[method-assign]
        return pl.Pipeline(self.cfg, hub, runner=runner, publisher=self._publisher, heartbeat_seconds=60)

    # --- escenarios -----------------------------------------------------------------
    def test_red_then_green_gate_opens_draft_pr_and_completes(self):
        transport = FakeTransport()
        runner = ScriptedRunner(
            {"planner": planner, "builder": builder_fixes_on(2), "code-reviewer": approve, "test-reviewer": approve}
        )
        code = self._pipeline(transport, runner).run(1)

        self.assertEqual(code, 0)
        self.assertEqual(runner.calls.count("builder"), 2)  # ronda 1 roja, ronda 2 verde
        self.assertEqual(len(self.published), 1)
        self.assertIn("Closes #5", self.published[0][1])
        complete = transport.paths("/complete")
        self.assertEqual(complete[-1], {"pr_url": PR_URL, "pr_number": 9})
        gate_uploads = [b for b in transport.paths("/artifacts") if b and b["stage"] == "gate"]
        self.assertEqual([b["round"] for b in gate_uploads], [1, 2])
        self.assertIn("FAIL", gate_uploads[0]["content"])
        self.assertIn("PASS", gate_uploads[1]["content"])
        self.assertTrue(any(b and b["kind"] == "diff" for b in transport.paths("/artifacts")))

    def test_gate_never_green_releases_as_needs_human_after_three_rounds(self):
        transport = FakeTransport()
        runner = ScriptedRunner(
            {"planner": planner, "builder": builder_fixes_on(99), "code-reviewer": approve, "test-reviewer": approve}
        )
        code = self._pipeline(transport, runner).run(1)

        self.assertEqual(code, 2)
        self.assertEqual(runner.calls.count("builder"), pl.rounds.MAX_BUILD_ROUNDS)
        release = transport.paths("/release")[-1]
        self.assertTrue(release["reason"].startswith("necesita humano"))
        self.assertIn("gate rojo tras 3 rondas", release["reason"])
        failure = [b for b in transport.paths("/artifacts") if b and b["kind"] == "failure_report"]
        self.assertEqual(len(failure), 1)
        self.assertEqual(self.published, [])  # sin PR si no hay gate verde

    def test_spec_problem_from_builder_goes_back_to_planner_once(self):
        transport = FakeTransport()

        def builder(cwd: Path, prompt: str, n: int) -> str:
            if n == 1:
                return "no encaja\nSPEC_PROBLEM: el spec pide borrar sin confirmar"
            (cwd / "ok.flag").write_text("1", encoding="utf-8")
            return "hecho"

        runner = ScriptedRunner(
            {"planner": planner, "builder": builder, "code-reviewer": approve, "test-reviewer": approve}
        )
        code = self._pipeline(transport, runner).run(1)

        self.assertEqual(code, 0)
        self.assertEqual(runner.calls.count("planner"), 2)
        self.assertEqual(len(self.published), 1)

    def test_reviewer_changes_requested_counts_as_a_build_round(self):
        transport = FakeTransport()

        def reviewer_asks_once(_cwd: Path, _prompt: str, n: int) -> str:
            return "falta un test\nVERDICT: REQUEST_CHANGES" if n == 1 else "VERDICT: APPROVE"

        runner = ScriptedRunner(
            {
                "planner": planner,
                "builder": builder_fixes_on(1),
                "code-reviewer": approve,
                "test-reviewer": reviewer_asks_once,
            }
        )
        code = self._pipeline(transport, runner).run(1)
        self.assertEqual(code, 0)
        self.assertEqual(runner.calls.count("builder"), 2)  # ronda 1 + vuelta por el revisor de tests

    def test_network_cut_on_uploads_is_spooled_and_flushed_later(self):
        transport = FakeTransport()
        transport.network_failures = 3
        runner = ScriptedRunner(
            {"planner": planner, "builder": builder_fixes_on(1), "code-reviewer": approve, "test-reviewer": approve}
        )
        pipeline = self._pipeline(transport, runner)
        code = pipeline.run(1)

        self.assertEqual(code, 0)
        self.assertEqual(pipeline.hub.pending(), 0)  # todo lo caído se reenvió
        self.assertEqual(transport.network_failures, 0)  # los cortes sí ocurrieron
        sent_stages = {b["stage"] for b in transport.paths("/artifacts") if b}
        self.assertIn("plan", sent_stages)
        self.assertIn("gate", sent_stages)
        self.assertEqual(len(self.published), 1)

    def test_crash_mid_run_resumes_from_local_state_without_second_claim(self):
        transport = FakeTransport()

        def crash(*_args):
            raise RuntimeError("proceso caído a mitad de builder")

        first = self._pipeline(transport, ScriptedRunner(
            {"planner": planner, "builder": crash, "code-reviewer": approve, "test-reviewer": approve}
        ))
        self.assertEqual(first.run(1), 1)
        self.assertEqual(first._load(1)["phase"], "build")

        transport.calls.clear()
        second = self._pipeline(transport, ScriptedRunner(
            {"planner": planner, "builder": builder_fixes_on(1), "code-reviewer": approve, "test-reviewer": approve}
        ))
        self.assertEqual(second.run(1), 0)
        self.assertEqual([c for c in transport.calls if c[1].endswith("/claim")], [])  # no reclama
        self.assertTrue(any(p.endswith("/heartbeat") for _, p, _ in transport.calls))
        self.assertEqual(len(self.published), 1)

    def test_no_credit_releases_with_needs_human_reason(self):
        transport = FakeTransport()

        def no_credit(*_args):
            raise pl.CreditError("builder: sin crédito o límite de uso")

        runner = ScriptedRunner({"planner": planner, "builder": no_credit})
        code = self._pipeline(transport, runner).run(1)

        self.assertEqual(code, 2)
        reason = transport.paths("/release")[-1]["reason"]
        self.assertIn("necesita humano", reason)
        self.assertIn("sin crédito", reason)

    def test_lost_claim_on_resume_stops_without_running_agents(self):
        transport = FakeTransport()

        def crash(*_args):
            raise RuntimeError("proceso caído a mitad de builder")

        first = self._pipeline(transport, ScriptedRunner(
            {"planner": planner, "builder": crash, "code-reviewer": approve, "test-reviewer": approve}
        ))
        first.run(1)

        transport.heartbeat_status = 409
        transport.claim_status = 409  # otro dev ya lo tiene
        runner = ScriptedRunner({"planner": planner})
        code = self._pipeline(transport, runner).run(1)
        self.assertEqual(code, 1)
        self.assertEqual(runner.calls, [])

    def test_expired_claim_is_reclaimed_on_resume_when_item_is_free(self):
        transport = FakeTransport()

        def crash(*_args):
            raise RuntimeError("proceso caído a mitad de builder")

        self._pipeline(transport, ScriptedRunner(
            {"planner": planner, "builder": crash, "code-reviewer": approve, "test-reviewer": approve}
        )).run(1)

        transport.heartbeat_status = 409  # caducó mientras estaba parado
        runner = ScriptedRunner(
            {"planner": planner, "builder": builder_fixes_on(1), "code-reviewer": approve, "test-reviewer": approve}
        )
        code = self._pipeline(transport, runner).run(1)
        self.assertEqual(code, 0)
        self.assertEqual(runner.calls.count("planner"), 0)  # reanuda en build, no replanifica
        self.assertEqual(len(self.published), 1)


class AgentFilesTest(unittest.TestCase):
    def test_every_agent_used_by_the_pipeline_has_a_definition_file(self):
        for agent in pl.AGENT_TOOLS:
            self.assertTrue((pl.AGENT_DIR / f"{agent}.md").exists(), agent)


class PrGuardTest(unittest.TestCase):
    def test_only_factory_branches_can_be_pushed_or_opened(self):
        for branch in ("main", "master", "feature/x", "factory/"):
            with self.assertRaises(pr_mod.PrError):
                pr_mod.check_branch(branch)
        pr_mod.check_branch("factory/12")

    def test_body_closes_the_linked_issue(self):
        body = pr_mod.build_body(12, "Resumen", 5)
        self.assertIn("Closes #5", body)
        self.assertNotIn("Closes #", pr_mod.build_body(12, "Resumen", None))


if __name__ == "__main__":
    unittest.main()
