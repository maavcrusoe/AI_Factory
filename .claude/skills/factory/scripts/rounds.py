"""Reglas de rondas del pipeline (sin E/S). Decide qué etapa sigue tras cada resultado.

- Gate rojo o revisor con cambios pedidos -> builder, máx. MAX_BUILD_ROUNDS rondas.
- SPEC_PROBLEM del builder -> planner, máx. MAX_PLAN_RUNS veces.
- Tope alcanzado -> necesita humano.
"""

import re
from dataclasses import dataclass

MAX_BUILD_ROUNDS = 3
MAX_PLAN_RUNS = 1

SPEC_PROBLEM_RE = re.compile(r"^SPEC_PROBLEM:\s*(.+)$", re.MULTILINE)
VERDICT_RE = re.compile(r"^VERDICT:\s*(APPROVE|REQUEST_CHANGES)\s*$", re.MULTILINE)
MEANING_RE = re.compile(r"^MEANING:\s*(none|minor|major|dubious)\s*$", re.MULTILINE)
PLANNED_RE = re.compile(r"^PLANNED:\s*(yes|no)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Next:
    phase: str  # plan | build | review | diff | human
    round: int = 0
    reason: str = ""


def after_gate(round_no: int, passed: bool) -> Next:
    if passed:
        return Next("review", round_no)
    if round_no >= MAX_BUILD_ROUNDS:
        return Next("human", round_no, f"gate rojo tras {MAX_BUILD_ROUNDS} rondas")
    return Next("build", round_no + 1)


def after_review(round_no: int, approved: bool) -> Next:
    if approved:
        return Next("diff", round_no)
    if round_no >= MAX_BUILD_ROUNDS:
        return Next("human", round_no, f"revisión con cambios pedidos tras {MAX_BUILD_ROUNDS} rondas")
    return Next("build", round_no + 1)


def after_spec_problem(plan_runs: int, problem: str) -> Next:
    if plan_runs >= MAX_PLAN_RUNS:
        return Next("human", 0, f"problema de spec sin replanificación: {problem}")
    return Next("plan", 0)


def parse_spec_problem(builder_output: str) -> str | None:
    match = SPEC_PROBLEM_RE.search(builder_output)
    return match.group(1).strip() if match else None


def parse_verdict(reviewer_output: str) -> bool | None:
    """True = APPROVE, False = REQUEST_CHANGES, None = sin veredicto (cuenta como cambios pedidos)."""
    matches = VERDICT_RE.findall(reviewer_output)
    if not matches:
        return None
    return matches[-1] == "APPROVE"


def parse_review_facts(reviewer_output: str) -> dict[str, object]:
    """Significado del texto y planificación según el code-reviewer (Fase 5).
    Sin línea, lo prudente: significado `dubious` y no planificado. Ambos piden humano en la política."""
    meanings = MEANING_RE.findall(reviewer_output)
    planned = PLANNED_RE.findall(reviewer_output)
    return {
        "meaning": meanings[-1] if meanings else "dubious",
        "planned": planned[-1] == "yes" if planned else False,
    }
