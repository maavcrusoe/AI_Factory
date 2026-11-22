"""Política de merge (Fase 5): qué cambios exigen humano. Motor puro: sin BD ni red.

La política es por proyecto y versionada (`merge_policies`). Sin filas, rige la versión 0 por defecto:
todo merge requiere humano. Relajar la política es cambiar datos, no código.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MergePolicy

Difficulty = Literal["low", "medium", "high"]
Meaning = Literal["none", "minor", "major", "dubious"]
DEFAULT_VERSION = 0
MAX_SENSITIVE_PATHS = 200


class MergePolicyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Valor inicial: todo merge requiere humano. Se relaja con datos reales.
    require_human_always: bool = True
    human_if_difficulty: list[Difficulty] = Field(default_factory=lambda: ["high"])
    # Globs con `**` (p. ej. `auth/**`). Cualquier ruta tocada que casa exige humano.
    sensitive_paths: list[str] = Field(default_factory=list, max_length=MAX_SENSITIVE_PATHS)
    human_if_unplanned: bool = True
    # `dubious`: el revisor del dev no está seguro. Es humano aunque el significado sea "minor".
    human_if_meaning: list[Meaning] = Field(default_factory=lambda: ["major", "dubious"])


@dataclass(frozen=True)
class MergeFacts:
    """Datos del item. `None` = dato que falta; con datos faltantes siempre decide un humano."""

    difficulty: str | None
    touched_paths: list[str] | None
    planned: bool | None
    meaning_change: str | None
    gate_result: str | None
    gate_sha: str | None


@dataclass(frozen=True)
class Verdict:
    human_required: bool
    reasons: list[str] = field(default_factory=list)


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """`**` cruza directorios, `*` y `?` no. Sin soporte de `[...]`: los globs de rutas son simples."""
    out = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
            if pattern[i : i + 1] == "/":
                # `a/**/b` también casa `a/b`
                out.append("/?")
                i += 1
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def evaluate(policy: MergePolicyBody, facts: MergeFacts) -> Verdict:
    reasons: list[str] = []
    if policy.require_human_always:
        reasons.append("política: todo merge requiere humano")

    missing = [
        name
        for name, value in (
            ("dificultad", facts.difficulty),
            ("rutas", facts.touched_paths),
            ("planificado", facts.planned),
            ("significado", facts.meaning_change),
            ("gate", facts.gate_result),
            ("sha", facts.gate_sha),
        )
        if value is None
    ]
    if missing:
        reasons.append(f"faltan datos: {', '.join(missing)}")
    elif facts.gate_result != "passed":
        reasons.append(f"gate no pasado ({facts.gate_result})")

    if facts.difficulty in policy.human_if_difficulty:
        reasons.append(f"dificultad {facts.difficulty}")
    if facts.touched_paths:
        patterns = [glob_to_regex(p) for p in policy.sensitive_paths]
        hits = sorted({path for path in facts.touched_paths for rx in patterns if rx.match(path)})
        if hits:
            reasons.append(f"ruta sensible: {', '.join(hits)}")
    if policy.human_if_unplanned and facts.planned is False:
        reasons.append("funcionalidad no planificada")
    if facts.meaning_change in policy.human_if_meaning:
        reasons.append(f"significado del texto: {facts.meaning_change}")

    return Verdict(human_required=bool(reasons), reasons=reasons)


def active_policy(db: Session, project_id: int) -> tuple[int, MergePolicyBody]:
    """Devuelve (versión, política) vigente. La versión más alta gana."""
    row = db.scalar(
        select(MergePolicy).where(MergePolicy.project_id == project_id).order_by(MergePolicy.version.desc()).limit(1)
    )
    if row is None:
        return DEFAULT_VERSION, MergePolicyBody()
    return row.version, MergePolicyBody.model_validate(row.body)
