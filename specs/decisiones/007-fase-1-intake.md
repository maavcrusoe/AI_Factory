# 007: Fase 1, entrada e intake (2026-11-21)

## Decisiones
- **Entrada**: `POST /api/v1/inputs` con cabecera `X-Idempotency-Key` obligatoria (422 si falta). Misma clave en el mismo proyecto devuelve el item existente (200), sin duplicar trabajo. Carrera entre dos peticiones iguales: la restricción única de BD gana y la segunda recibe 200.
- **Proyecto**: debe existir por `slug` (404 si no). Se siembra el proyecto de demo `meme-demo` al arrancar la API.
- **Autor**: la petición requiere token válido de usuario activo (ya lo exige `current_user`).
- **Intake asíncrono**: el POST responde al crear el item (estado `RECEIVED`) y el intake corre en `BackgroundTasks`. El dashboard ve el resultado por SSE.
- **Modelo**: interfaz `IntakeModel` (`services/intake_model.py`). Implementación `OllamaIntakeModel` (`services/llm_ollama.py`) con `httpx`, `POST /api/chat`, `think: false`, `format` = JSON schema de `IntakeAssessment`, `temperature: 0`, timeout 60 s. URL, modelo y timeout en `.env` (`OLLAMA_URL`, `OLLAMA_MODEL`, `OLLAMA_TIMEOUT_SECONDS`).
- **Salida del LLM**: validada con Pydantic. Cualquier fallo (timeout, HTTP, JSON inválido, esquema incumplido) deja el item en `WAITING_HUMAN_TRIAGE` con el motivo. Nunca auto-acepta.
- **Umbrales** (propuesta de specs/02, aún sin cambiar): 0.80 para automatismo; 0.65 solo cambia el motivo mostrado. Por debajo de 0.80 decide un humano.
- **Decisión automática**: `accept` con confianza ≥ 0.80 → `QUEUED` con etiqueta `factory:auto`. `needs_info` con confianza ≥ 0.80 → `NEEDS_INFO`. `reject` con confianza ≥ 0.80 → `REJECTED`. Pendiente: confirmar si el rechazo automático debe pasar siempre por humano.
- **Texto original vs ampliado**: `body` guarda el original y `expanded_body` la versión ampliada por el modelo. El payload recibido se guarda en `original_payload`.
- **Decisión manual**: `accept` / `reject` / `request_info` solo desde `WAITING_HUMAN_TRIAGE` o `NEEDS_INFO` (409 en otro caso). `accept` acepta etiqueta opcional, por defecto `factory:human`.
- **Auditoría**: cada cambio de estado o decisión escribe una fila en `work_item_events`.
- **SSE**: `GET /api/v1/inputs/stream` sondea `work_item_events` cada 1 s y emite un frame por evento nuevo (ping cada ~15 s). El dashboard lo consume por un route handler de Next (`/api/inputs/stream`) que lleva el token desde la cookie httpOnly; el navegador nunca ve el token.
- **Webhook genérico**: `POST /api/v1/webhooks/generic`. Autoridad = firma `X-Hub-Signature-256: sha256=<hex>` (HMAC-SHA256 del cuerpo crudo, comparación en tiempo constante). Sin firma válida: 401. `X-Idempotency-Key` obligatoria (422). El secreto es global (`WEBHOOK_SECRET`); sin valor, el webhook rechaza todo. Ceiling: secreto por proyecto cuando lleguen los adapters. Audita con actor `webhook`.
- **Plazo total del intake**: `INTAKE_DEADLINE_SECONDS` (60 por defecto) acota la espera al modelo con `future.result(timeout)`. Pasado el plazo: `WAITING_HUMAN_TRIAGE` con motivo "plazo ... superado". El timeout de httpx no basta, porque no cubre toda la espera.
- **Barrido al arrancar**: los items en `RECEIVED`, `NORMALIZING` o `TRIAGE` pasan a `WAITING_HUMAN_TRIAGE` (evento `startup_sweep`, actor `system`). Nunca se reanuda el intake automáticamente. Ceiling: un solo proceso de API; con varios workers habría que bloquear.
- **Fuera de este PR**: adapters de GitHub y Azure DevOps.

## Verificación
- `pytest`: 26 pasan, 1 se salta (Ollama real).
- Ollama real (`OLLAMA_REAL=1 pytest -m ollama_real`): pasa.
- Migración `0002_work_items`: upgrade, downgrade, upgrade y `alembic check` sin diferencias.
- Playwright: login, creación desde formulario, detalle con auditoría, decisión manual y actualización por SSE.

## Pendiente
- Adapters GitHub y Azure DevOps (Fase 2).
