# 014: E2E local con meme-demo y merge real del PR #6

Fecha: 2026-11-22. Estado: ejecutado. (El brief pedía `012-e2e-merge-meme-demo.md`; el 012 ya existe, es de la Fase 6, por eso este es el 014.)

## Qué se hizo
- Hub local: Postgres 16 en Docker (`docker-compose.dev.yml`), `alembic upgrade head`, API con `uvicorn` y dashboard con `next dev`, ambos en el host. Admin sembrado por `.env`; usuarios `reviewer` y `developer` creados por la API.
- Proyecto `meme-demo` con integración GitHub (`maavcrusoe/meme-demo`). El token salió de `gh auth token` solo en tiempo de ejecución, por la API; queda cifrado (Fernet) en la base. No está en git ni en logs.
- La base original del hub ya no existía. Se re-registró el PR #6 en un item nuevo (#1): input, intake, claim, enlace al issue #5, artefactos (spec, diff, log del gate, nota de revisión), `complete` con PR #6 y `gate-report`.
- Gate re-ejecutado: `bash checks.sh` sobre el SHA `f2ef306aec4f4d3187a3b55e258af63e96a20a20` (head del PR) da `ok ok`, salida 0. Se informó ese SHA exacto.
- Hallazgos de revisores: los originales no se conservan. El item lo dice en `review_findings` y en el artefacto de revisión.
- Playwright como `reviewer`: `/approvals` → detalle (gate, política, diff) → "Aprobar cambio" → "Mergear PR".

## Resultado
- PR #6 `MERGED` (commit `74a3aeadda4c2954a205006ece2f048aaaa05ef3`), y ya no era borrador: `mark_ready` (GraphQL `markPullRequestReadyForReview`) funcionó con el adapter existente.
- `main` de meme-demo contiene el botón `#clear`; `checks.sh` sobre `main` da `ok ok`. Issue #5 cerrado por `Closes #5`.
- Dashboard: item en `MERGED` ("Mergeada"). Auditoría: received, normalized, triage_started, intake_assessed, claimed, tracker_linked, pr_opened, gate_reported, policy_evaluated, approved, merge_started, merged.
- No se tocó nada más de meme-demo.

## Hallazgos
1. **`localhost` en Windows (arreglado).** Resuelve primero a `::1`; Docker publica solo `127.0.0.1`, y cada conexión tarda 15 s. La API colgaba en el arranque y `pytest` no terminaba. Causa raíz: `localhost` en `conftest.py` (`DEFAULT_TEST_DB`) y `.env.example`. Ahora usan `127.0.0.1`. CI no se toca: allí `localhost` resuelve bien.
2. **Hueco de test (arreglado).** Faltaba cubrir que GitHub responde 200 con `errors` en GraphQL y `mark_ready` lanza `ValueError` (el merge controller lo convierte en 502 y el item sigue `READY_TO_MERGE`). Tests en `apps/api/tests/test_github_ready.py`.
3. **Credencial de merge = token del tracker (punto abierto).** Solo hay un login de `gh`, así que ambas credenciales de la integración llevan el mismo valor. El diseño las guarda separadas y el cliente (builder) no recibe ninguna, pero nada obliga a que sean distintas. Para producción, usar un token propio para merge con permiso solo de PRs.
4. Puerto 8000 ocupado por otro proceso de la máquina: se usó 8010 (API) y 3010 (dashboard).
5. El intake con Ollama pasó a `QUEUED` en ~35 s sin intervención.
