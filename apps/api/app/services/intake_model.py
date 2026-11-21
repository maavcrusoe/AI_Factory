"""Interfaz del modelo de intake y su salida validada.

Cambiar de modelo = nueva clase que cumpla `IntakeModel`. La salida del LLM
nunca se usa sin pasar por `IntakeAssessment`.
"""

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class IntakeModelError(Exception):
    """Fallo del modelo (timeout, HTTP, JSON inválido, esquema incumplido)."""


@dataclass(frozen=True)
class IntakeInput:
    project_slug: str
    title: str
    body: str


class IntakeAssessment(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")

    decision: Literal["accept", "needs_info", "reject"]
    confidence: float = Field(ge=0, le=1)
    work_type: Literal["feature", "bug", "refactor", "docs", "other"] = Field(alias="type")
    difficulty: Literal["low", "medium", "high"]
    risk: Literal["low", "medium", "high"]
    summary: str = Field(min_length=1, max_length=1000)
    suggested_labels: list[str] = Field(default_factory=list, max_length=5)
    valuation: str = Field(min_length=1, max_length=1000)
    expanded_body: str | None = Field(default=None, max_length=8000)


class IntakeModel(Protocol):
    def assess(self, item: IntakeInput) -> IntakeAssessment:
        """Devuelve la valoración o lanza IntakeModelError."""
        ...
