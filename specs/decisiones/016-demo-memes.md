# 016: Demo de memes (auto-merge y espera humana)

Fecha: 2026-11-22. Estado: ejecutado.

## Qué se hizo
Hub local (Postgres 5440, API 8140, dashboard 3140: 8010/3010 y 8000 los usaban otros worktrees), `meme-demo` con política v1 por proyecto y dos peticiones por `POST /api/v1/inputs` (form). Receta en `docs/demo-memes.md` y `scripts/demo-memes-seed.sh`.
- **A**: item #7, título de la página → `index.html`. Intake: low. Gate verde, `touched_paths` = spec + `index.html`, política sin motivos → `READY_TO_MERGE` → `system:policy` mergeó el PR #8 solo.
- **B**: item #3, selector de plantilla + chistes. Toca `meme.js` → "ruta sensible: meme.js" → `WAITING_HUMAN_MERGE`, PR #9 en borrador. **Sin aprobar.**
- **#1** (PR #7, borrador): primer intento de A. El builder añadió asserts a `checks.sh` (ruta sensible) y quedó en humano: la política funcionó. Se deja pendiente como ejemplo; si se mergea, no choca con #8.
- Items #2, #4, #5, #6: duplicados rechazados (intake con timeout).

## Decisiones y desviaciones
1. **`.factory/*` en vez de `.factory/**`.** El planner commitea `.factory/specs/<id>/spec.md` en cada PR; con `**` ningún cambio podría ir sin humano. `*` (un nivel) protege `.factory/config.yaml` y no el spec.
2. **"Tipo cosmético" no existe en el motor** (el intake emite `feature|bug|refactor|docs|other`). Se aproxima con `human_if_difficulty:[medium,high]` + significado + no planificado + rutas sensibles. Mejora posible: regla `human_unless_types`.
3. **Rutas sensibles son ficheros enteros**: "núcleo `drawMeme`" = `meme.js` completo.
4. **Intake lento**: con Ollama compartido, 4 de 6 intakes superaron 60 s. Se subió `INTAKE_DEADLINE_SECONDS` a 240 y `OLLAMA_TIMEOUT_SECONDS` a 230 (runbook `ollama-no-disponible.md`). No se aceptó nada a mano: un item aceptado a mano no tiene dificultad y siempre va a humano.
5. **Resultado del LLM no controlado**: A salió `low` y B también `low`; B va a humano por ruta, no por dificultad.
6. **Credencial de merge = mismo token de `gh`** (punto abierto de 014).
7. Playwright MCP no conectó; verificación con `playwright-core` (caché npx) y Chromium local. Capturas fuera del repo.
8. Efectos en meme-demo: PRs #7, #8 (mergeado), #9. Sin issues ni etiquetas nuevas (items `form`, sin enlace de tracker).
