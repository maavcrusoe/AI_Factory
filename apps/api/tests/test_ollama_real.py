"""Prueba opcional contra el Ollama real del hub. Se salta salvo OLLAMA_REAL=1.

Ejecutar: OLLAMA_REAL=1 uv run pytest -m ollama_real -s
"""

import os

import pytest

from app.config import get_settings
from app.services.intake_model import IntakeAssessment, IntakeInput
from app.services.llm_ollama import OllamaIntakeModel

pytestmark = [
    pytest.mark.ollama_real,
    pytest.mark.skipif(os.environ.get("OLLAMA_REAL") != "1", reason="requiere OLLAMA_REAL=1"),
]


def test_real_ollama_returns_valid_assessment() -> None:
    settings = get_settings()
    model = OllamaIntakeModel(settings.ollama_url, settings.ollama_model, settings.ollama_timeout_seconds)
    result = model.assess(
        IntakeInput(
            project_slug="meme-demo",
            title="Añadir botón de modo oscuro",
            body="En el dashboard, un botón en la cabecera para cambiar entre tema claro y oscuro.",
        )
    )
    assert isinstance(result, IntakeAssessment)
    assert result.decision in {"accept", "needs_info", "reject"}
    assert 0 <= result.confidence <= 1
