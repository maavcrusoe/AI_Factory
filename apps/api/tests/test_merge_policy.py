"""Reglas de la política de merge (Fase 5). Motor puro: sin BD ni red."""

from app.services.merge_policy import MergeFacts, MergePolicyBody, evaluate, glob_to_regex

SHA = "a" * 40
TRIVIAL = MergeFacts(
    difficulty="low",
    touched_paths=["src/button.tsx"],
    planned=True,
    meaning_change="none",
    gate_result="passed",
    gate_sha=SHA,
)
# Política relajada: solo las reglas explícitas exigen humano.
RELAXED = MergePolicyBody(
    require_human_always=False,
    human_if_difficulty=["high"],
    sensitive_paths=["auth/**", "migrations/*.sql"],
    human_if_unplanned=True,
    human_if_meaning=["major", "dubious"],
)


def _facts(**changes) -> MergeFacts:
    values = {**TRIVIAL.__dict__, **changes}
    return MergeFacts(**values)


def test_default_policy_requires_human_even_for_trivial_change() -> None:
    verdict = evaluate(MergePolicyBody(), TRIVIAL)
    assert verdict.human_required is True
    assert verdict.reasons == ["política: todo merge requiere humano"]


def test_relaxed_policy_lets_trivial_change_through() -> None:
    verdict = evaluate(RELAXED, TRIVIAL)
    assert verdict.human_required is False
    assert verdict.reasons == []


def test_high_difficulty_requires_human() -> None:
    assert evaluate(RELAXED, _facts(difficulty="high")).human_required is True


def test_sensitive_path_requires_human_and_names_the_path() -> None:
    verdict = evaluate(RELAXED, _facts(touched_paths=["src/a.py", "auth/login.py"]))
    assert verdict.human_required is True
    assert verdict.reasons == ["ruta sensible: auth/login.py"]


def test_unplanned_feature_requires_human() -> None:
    assert evaluate(RELAXED, _facts(planned=False)).human_required is True


def test_meaning_change_major_or_dubious_requires_human() -> None:
    assert evaluate(RELAXED, _facts(meaning_change="major")).human_required is True
    assert evaluate(RELAXED, _facts(meaning_change="dubious")).human_required is True
    assert evaluate(RELAXED, _facts(meaning_change="minor")).human_required is False


def test_missing_facts_always_require_human() -> None:
    # Un item aceptado a mano no tiene dificultad: nunca pasa solo.
    verdict = evaluate(RELAXED, _facts(difficulty=None))
    assert verdict.human_required is True
    assert verdict.reasons == ["faltan datos: dificultad"]


def test_failed_or_stale_gate_requires_human() -> None:
    assert evaluate(RELAXED, _facts(gate_result="failed")).human_required is True
    assert evaluate(RELAXED, _facts(gate_sha=None)).human_required is True


def test_glob_double_star_crosses_directories_and_single_star_does_not() -> None:
    assert glob_to_regex("auth/**").match("auth/login/token.py")
    assert glob_to_regex("auth/**").match("auth/x.py")
    assert not glob_to_regex("auth/**").match("myauth/x.py")
    assert glob_to_regex("migrations/*.sql").match("migrations/0001.sql")
    assert not glob_to_regex("migrations/*.sql").match("migrations/old/0001.sql")
    assert glob_to_regex("a/**/b").match("a/b")
    assert glob_to_regex("a/**/b").match("a/x/y/b")
