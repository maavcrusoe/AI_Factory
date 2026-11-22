"""Pipeline del cliente (Fase 4). Corre en la máquina del dev; el hub nunca ejecuta agentes.

claim -> worktree factory/<id> -> planner -> builder -> gate (checks.sh) -> revisores -> diff
      -> push -> PR en borrador (Closes #N) -> complete

- Gate rojo o revisor con cambios pedidos: vuelve al builder (máx. 3 rondas).
- SPEC_PROBLEM del builder: vuelve al planner (máx. 1 vez).
- Tope alcanzado o sin crédito: release con motivo "necesita humano: ...".
- Estado en disco tras cada etapa: un corte se reanuda con el mismo comando.
- Latido en un hilo cada 60 s. Si el hub responde 409, el claim se perdió y paramos.

Uso (desde la raíz de AI_Factory):
  python .claude/skills/factory/scripts/pipeline.py --repo <clon-del-proyecto> [--item N]
Requiere FACTORY_TOKEN y <clon>/.factory/config.yaml (projectId, hubUrl).
"""

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
AGENT_DIR = HERE.parents[2] / "agents"  # .claude/agents del repo de AI_Factory, nunca del worktree
MAX_CONTENT_CHARS = 190_000
HEARTBEAT_SECONDS = 60
CREDIT_RE = re.compile(r"credit|cr[eé]dito|rate limit|usage limit|l[ií]mite de uso|quota", re.I)

sys.path.insert(0, str(HERE))
import gate as gate_mod  # noqa: E402
import pr as pr_mod  # noqa: E402
import rounds  # noqa: E402
from hub import HubClient, HubError  # noqa: E402

AGENT_TOOLS: dict[str, list[str]] = {
    "planner": ["Read", "Write", "Edit", "Glob", "Grep", "Bash(git status:*)", "Bash(git log:*)"],
    "builder": [
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "Bash(git status:*)",
        "Bash(git diff:*)",
        "Bash(node:*)",
        "Bash(bash checks.sh)",
    ],
    "code-reviewer": ["Read", "Glob", "Grep", "Bash(git diff:*)", "Bash(git log:*)"],
    "test-reviewer": ["Read", "Glob", "Grep", "Bash(git diff:*)", "Bash(bash checks.sh)", "Bash(node:*)"],
}


class ClaudeError(Exception):
    pass


class CreditError(ClaudeError):
    pass


class NeedsHuman(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class LostClaim(Exception):
    pass


Runner = Callable[[str, str, Path, Path], str]  # (agente, prompt, cwd, log) -> salida
Publisher = Callable[[Path, str, str, Path], tuple[str, int]]  # (wt, rama, título, cuerpo) -> (url, nº)


@dataclass
class Config:
    project_id: str
    hub_url: str
    repo: Path
    home: Path

    @classmethod
    def load(cls, repo: Path, home: Path | None = None) -> "Config":
        values: dict[str, str] = {}
        cfg_file = repo / ".factory" / "config.yaml"
        if not cfg_file.exists():
            raise SystemExit(f"falta {cfg_file} (ver config.example.yaml)")
        for line in cfg_file.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" in line:
                key, _, value = line.partition(":")
                values[key.strip()] = value.strip()
        if not values.get("projectId") or not values.get("hubUrl"):
            raise SystemExit("config.yaml necesita projectId y hubUrl")
        home = home or repo.parent / f"{repo.name}.factory"
        hub_url = os.environ.get("FACTORY_HUB_URL") or values["hubUrl"]  # override local, sin tocar el repo
        return cls(values["projectId"], hub_url, repo, home)


def run_agent(agent: str, prompt: str, cwd: Path, log_path: Path) -> str:
    """Ejecuta `claude -p` con el agente. Usa FACTORY_CLAUDE_BIN si está definido."""
    binary = os.environ.get("FACTORY_CLAUDE_BIN", "claude")
    cmd = [
        binary,
        "-p",
        "--permission-mode",
        "acceptEdits",
        "--output-format",
        "text",
        "--append-system-prompt-file",
        str(AGENT_DIR / f"{agent}.md"),
        "--allowedTools",
        *AGENT_TOOLS[agent],
    ]
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=3600,
    )
    output = proc.stdout + (f"\n[stderr]\n{proc.stderr}" if proc.stderr.strip() else "")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    if proc.returncode != 0:
        if CREDIT_RE.search(output):
            raise CreditError(f"{agent}: sin crédito o límite de uso")
        raise ClaudeError(f"{agent} salió con rc={proc.returncode}")
    return proc.stdout


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.name=AI Factory", "-c", "user.email=factory@localhost", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise ClaudeError(f"git {args[0]} falló: {proc.stderr.strip()[:300]}")
    return proc.stdout


def commit_all(worktree: Path, message: str) -> None:
    git(worktree, "add", "-A")
    if git(worktree, "status", "--porcelain").strip():
        git(worktree, "commit", "-m", message)


def setup_worktree(repo: Path, worktree: Path, branch: str) -> None:
    """Idempotente: si el worktree ya existe, no hace nada."""
    if worktree.exists():
        return
    git(repo, "fetch", "origin", "main")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    exists = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=repo, capture_output=True
    ).returncode == 0
    if exists:
        git(repo, "worktree", "add", str(worktree), branch)
    else:
        git(repo, "worktree", "add", "-b", branch, str(worktree), "origin/main")


def _truncate(text: str) -> str:
    if len(text) <= MAX_CONTENT_CHARS:
        return text
    return text[:MAX_CONTENT_CHARS] + f"\n[truncado: {len(text)} caracteres]\n"


class Heartbeat:
    def __init__(self, hub: HubClient, item_id: int, interval: float = HEARTBEAT_SECONDS):
        self.hub = hub
        self.item_id = item_id
        self.interval = interval
        self.message = "arrancando"
        self.lost = False
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> "Heartbeat":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            try:
                self.hub.heartbeat(self.item_id, "working", self.message)
            except HubError as exc:
                if exc.status == 409:
                    self.lost = True
                    return
            except OSError:
                pass  # corte de red: el siguiente latido lo intenta de nuevo


class Pipeline:
    def __init__(
        self,
        cfg: Config,
        hub: HubClient,
        runner: Runner = run_agent,
        publisher: Publisher | None = None,
        heartbeat_seconds: float = HEARTBEAT_SECONDS,
    ):
        self.cfg = cfg
        self.hub = hub
        self.runner = runner
        self.publisher = publisher or self._default_publisher
        self.heartbeat_seconds = heartbeat_seconds

    # --- rutas ----------------------------------------------------------------------
    def _runs(self, item_id: int) -> Path:
        return self.cfg.home / "runs" / str(item_id)

    def _state_file(self, item_id: int) -> Path:
        return self._runs(item_id) / "state.json"

    def _load(self, item_id: int) -> dict[str, Any] | None:
        path = self._state_file(item_id)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None

    def _save(self, state: dict[str, Any]) -> None:
        path = self._state_file(state["itemId"])
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)  # atómico: un corte no deja el estado a medias

    @staticmethod
    def _default_publisher(worktree: Path, branch: str, title: str, body_file: Path) -> tuple[str, int]:
        pr_mod.push_branch(worktree, branch)
        return pr_mod.create_draft_pr(worktree, branch, title, body_file)

    # --- entrada --------------------------------------------------------------------
    def run(self, item_id: int | None = None) -> int:
        state = self._load(item_id) if item_id is not None else None
        if state is not None and state["phase"] == "released":
            state = None  # liberado antes: el hub lo devolvió a la cola y esta es una reclamación nueva
        if state is None:
            state = self._claim_new(item_id)
            if state is None:
                return 0
        else:
            # Reanudar: primero latido. Un 409 significa que el hub ya no nos da el trabajo.
            try:
                self.hub.heartbeat(state["itemId"], "resuming", f"reanudando {state['phase']}")
            except HubError as exc:
                if exc.status == 409:
                    print(f"#{state['itemId']}: ya no tienes este trabajo; no reanudo")
                    return 1
                raise
            self.hub.flush_outbox()
        if state["phase"] in ("done", "released"):
            print(f"#{state['itemId']}: ya terminado ({state['phase']})")
            return 0 if state["phase"] == "done" else 2
        hb = Heartbeat(self.hub, state["itemId"], self.heartbeat_seconds).start()
        try:
            return self._drive(state, hb)
        finally:
            hb.stop()

    def _claim_new(self, item_id: int | None) -> dict[str, Any] | None:
        if item_id is None:
            queue = self.hub.queue(self.cfg.project_id)
            if not queue:
                print(f"no hay trabajo pendiente en {self.cfg.project_id}")
                return None
            item_id = queue[0]["id"]
        try:
            detail = self.hub.claim(item_id)
        except HubError as exc:
            print(f"no se pudo reclamar #{item_id}: {exc}")
            raise SystemExit(1) from None
        tracker = detail.get("tracker") or {}
        state = {
            "itemId": item_id,
            "title": detail["title"],
            "body": detail["body"],
            "issue": int(tracker["remote_id"]) if tracker.get("provider") == "github" else None,
            "branch": f"factory/{item_id}",
            "worktree": str(self.cfg.home / "worktrees" / str(item_id)),
            "phase": "worktree",
            "round": 1,
            "planRuns": 0,
            "feedback": "",
            "prUrl": None,
            "prNumber": None,
        }
        self._runs(item_id).mkdir(parents=True, exist_ok=True)
        self._save(state)
        print(f"reclamado #{item_id}: {detail['title']}")
        return state

    def _drive(self, state: dict[str, Any], hb: Heartbeat) -> int:
        try:
            while state["phase"] not in ("done", "released"):
                if hb.lost:
                    raise LostClaim()
                hb.message = f"{state['phase']} ronda {state['round']}"
                self._step(state)
                self._save(state)
        except LostClaim:
            print(f"#{state['itemId']}: el hub ya no nos asigna este trabajo; paro sin liberar")
            return 1
        except NeedsHuman as exc:
            return self._release(state, exc.reason)
        except CreditError as exc:
            return self._release(state, f"sin crédito o límite de uso en {state['phase']}: {exc}")
        except ClaudeError as exc:
            return self._release(state, f"fallo en {state['phase']}: {exc}")
        except (OSError, HubError) as exc:
            print(f"#{state['itemId']}: corte o error ({type(exc).__name__}); vuelve a ejecutar el mismo comando para reanudar")
            self._save(state)
            return 1
        except Exception:  # noqa: BLE001 - cualquier fallo no esperado queda en el estado
            traceback.print_exc()
            self._save(state)
            return 1
        print(f"#{state['itemId']}: PR en borrador {state['prUrl']}")
        return 0

    # --- etapas ---------------------------------------------------------------------
    def _step(self, state: dict[str, Any]) -> None:
        phase = state["phase"]
        getattr(self, f"_do_{phase.replace('-', '_')}")(state)

    def _stage_event(self, state: dict[str, Any], stage: str, message: str) -> None:
        self.hub.event(
            state["itemId"], "stage", message, {"stage": stage, "round": state["round"]}
        )

    def _upload(self, state: dict[str, Any], stage: str, round_no: int, kind: str, text: str) -> None:
        self.hub.artifact(
            state["itemId"],
            stage=stage,
            round_no=round_no,
            kind=kind,
            client_key=f"{stage}-{round_no}-{kind}",
            content=_truncate(text),
        )

    def _do_worktree(self, state: dict[str, Any]) -> None:
        self.hub.flush_outbox()
        setup_worktree(self.cfg.repo, Path(state["worktree"]), state["branch"])
        self._stage_event(state, "worktree", f"worktree {state['branch']} listo")
        state["phase"] = "plan"

    def _do_plan(self, state: dict[str, Any]) -> None:
        worktree = Path(state["worktree"])
        item_id = state["itemId"]
        self.hub.flush_outbox()
        feedback = f"\n\nMotivo de esta nueva planificación:\n{state['feedback']}" if state["feedback"] else ""
        prompt = (
            f"Petición #{item_id}: {state['title']}\n\n{state['body']}\n\n"
            f"Escribe la especificación en .factory/specs/{item_id}/spec.md dentro de este repositorio.{feedback}"
        )
        log = self._runs(item_id) / f"plan-{state['planRuns']}.log"
        self.runner("planner", prompt, worktree, log)
        spec = worktree / ".factory" / "specs" / str(item_id) / "spec.md"
        if not spec.exists():
            raise ClaudeError("el planner no escribió spec.md")
        commit_all(worktree, f"factory({item_id}): especificación")
        self._upload(state, "plan", 0, "log", log.read_text(encoding="utf-8"))
        self._stage_event(state, "plan", "especificación lista")
        state["feedback"] = ""
        state["phase"] = "build"

    def _do_build(self, state: dict[str, Any]) -> None:
        worktree = Path(state["worktree"])
        item_id = state["itemId"]
        self.hub.flush_outbox()
        feedback = (
            f"\n\nLa ronda anterior no pasó. Corrige esto:\n{state['feedback']}" if state["feedback"] else ""
        )
        prompt = (
            f"Implementa la especificación .factory/specs/{item_id}/spec.md. Cambios mínimos.{feedback}\n\n"
            "Si la especificación es incorrecta o imposible, no la adivines: termina con una línea "
            "'SPEC_PROBLEM: <motivo>' y para."
        )
        log = self._runs(item_id) / f"round-{state['round']}" / "builder.log"
        output = self.runner("builder", prompt, worktree, log)
        problem = rounds.parse_spec_problem(output)
        if problem:
            nxt = rounds.after_spec_problem(state["planRuns"], problem)
            self._upload(state, "build", state["round"], "log", log.read_text(encoding="utf-8"))
            self._stage_event(state, "build", f"problema de spec: {problem}")
            if nxt.phase == "human":
                raise NeedsHuman(nxt.reason)
            state["planRuns"] += 1
            state["feedback"] = problem
            state["phase"] = "plan"
            return
        commit_all(worktree, f"factory({item_id}): builder ronda {state['round']}")
        self._upload(state, "build", state["round"], "log", log.read_text(encoding="utf-8"))
        state["phase"] = "gate"

    def _do_gate(self, state: dict[str, Any]) -> None:
        round_no = state["round"]
        # El gate es determinista (checks.sh del proyecto), no un agente.
        gate_result = gate_mod.run_gate(
            Path(state["worktree"]), self._runs(state["itemId"]) / f"round-{round_no}" / "gate.log", round_no
        )
        self._upload(state, "gate", round_no, "log", gate_result.log_path.read_text(encoding="utf-8"))
        verdict = "PASS" if gate_result.passed else "FAIL"
        self._stage_event(state, "gate", f"gate ronda {round_no}: {verdict}")
        nxt = rounds.after_gate(round_no, gate_result.passed)
        state["feedback"] = gate_result.output[-4000:]
        self._apply(state, nxt)

    def _do_review(self, state: dict[str, Any]) -> None:
        worktree = Path(state["worktree"])
        item_id = state["itemId"]
        round_no = state["round"]
        self.hub.flush_outbox()
        prompt = (
            f"Revisa la rama contra origin/main (git diff origin/main...HEAD) y la especificación "
            f".factory/specs/{item_id}/spec.md. No edites ficheros. Termina con una línea "
            "'VERDICT: APPROVE' o 'VERDICT: REQUEST_CHANGES'."
        )
        reviews: list[str] = []
        all_approved = True
        for reviewer, stage in (("code-reviewer", "review-code"), ("test-reviewer", "review-test")):
            log = self._runs(item_id) / f"round-{round_no}" / f"{stage}.log"
            output = self.runner(reviewer, prompt, worktree, log)
            approved = rounds.parse_verdict(output) is True
            self._upload(state, stage, round_no, "log", log.read_text(encoding="utf-8"))
            self._stage_event(state, stage, "aprobado" if approved else "cambios pedidos")
            if not approved:
                all_approved = False
                reviews.append(f"[{reviewer}]\n{output[-3000:]}")
        state["feedback"] = "\n\n".join(reviews)
        self._apply(state, rounds.after_review(round_no, all_approved))

    def _apply(self, state: dict[str, Any], nxt: rounds.Next) -> None:
        if nxt.phase == "human":
            raise NeedsHuman(nxt.reason)
        state["phase"] = nxt.phase
        if nxt.round:
            state["round"] = nxt.round

    def _do_diff(self, state: dict[str, Any]) -> None:
        worktree = Path(state["worktree"])
        diff = git(worktree, "diff", "origin/main...HEAD")
        self._upload(state, "diff", state["round"], "diff", diff)
        self._stage_event(state, "diff", f"diff de {len(diff.splitlines())} líneas")
        state["phase"] = "pr"

    def _do_pr(self, state: dict[str, Any]) -> None:
        worktree = Path(state["worktree"])
        item_id = state["itemId"]
        summary = (
            f"Pipeline AI Factory para la petición #{item_id}: {state['title']}.\n\n"
            f"Rondas de builder: {state['round']}. Gate verde y revisores aprobados.\n"
            f"Especificación: .factory/specs/{item_id}/spec.md"
        )
        body_file = self._runs(item_id) / "pr-body.md"
        body_file.write_text(pr_mod.build_body(item_id, summary, state["issue"]), encoding="utf-8")
        title = f"Factory #{item_id}: {state['title']}"[:250]
        url, number = self.publisher(worktree, state["branch"], title, body_file)
        state["prUrl"], state["prNumber"] = url, number
        self._stage_event(state, "pr", f"PR en borrador {url}")
        state["phase"] = "complete"

    def _do_complete(self, state: dict[str, Any]) -> None:
        try:
            self.hub.complete(state["itemId"], state["prUrl"], state["prNumber"])
        except HubError as exc:
            # Si un corte pasó después de que el hub aceptara el complete, ya está hecho.
            if exc.status != 409 or self.hub.item(state["itemId"])["status"] != "PR_OPEN":
                raise
        report = (
            f"Petición #{state['itemId']}: {state['title']}\n"
            f"PR en borrador: {state['prUrl']}\n"
            f"Rama: {state['branch']}. Rondas de builder: {state['round']}. Planificaciones: {state['planRuns'] + 1}.\n"
            "Gate verde, revisores aprobados. El cliente no hace merge."
        )
        self._upload(state, "report", state["round"], "report", report)
        print(report)
        state["phase"] = "done"

    def _release(self, state: dict[str, Any], reason: str) -> int:
        item_id = state["itemId"]
        text = (
            f"Fallo: {reason}\nRondas de builder: {state['round']}, planificaciones: {state['planRuns']}\n"
            f"Último feedback:\n{state['feedback']}"
        )
        try:
            self._upload(state, state["phase"], state["round"], "failure_report", text)
        except (OSError, HubError):
            pass  # el motivo también va en el release
        try:
            self.hub.release(item_id, f"necesita humano: {reason}")
        except HubError as exc:
            print(f"#{item_id}: no se pudo liberar: {exc}")
        state["phase"] = "released"
        self._save(state)
        print(f"#{item_id}: liberado, necesita humano: {reason}")
        return 2


def _hub_from_env(cfg: Config) -> HubClient:
    token = os.environ.get("FACTORY_TOKEN", "")
    if not token:
        raise SystemExit("falta FACTORY_TOKEN (token personal fct_...)")
    return HubClient(cfg.hub_url, token, cfg.home / "outbox.jsonl")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(errors="replace")  # una consola cp1252 no debe tumbar la ejecución
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="clon del proyecto (con .factory/)")
    parser.add_argument("--item", type=int, help="id de la petición; sin esto toma la primera de la cola")
    parser.add_argument("--home", type=Path, help="carpeta de worktrees y estado (por defecto <repo>.factory)")
    args = parser.parse_args(argv)
    cfg = Config.load(args.repo.resolve(), args.home.resolve() if args.home else None)
    hub = _hub_from_env(cfg)
    return Pipeline(cfg, hub).run(args.item)


if __name__ == "__main__":
    sys.exit(main())
