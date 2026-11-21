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
- **Fuera de este PR**: entrada webhook con firma HMAC y adapters de GitHub / Azure DevOps. No están en `tasks/todo.md` de Fase 1; quedan para cuando se asignen.

## Verificación
- `pytest`: 26 pasan, 1 se salta (Ollama real).
- Ollama real (`OLLAMA_REAL=1 pytest -m ollama_real`): pasa.
- Migración `0002_work_items`: upgrade, downgrade, upgrade y `alembic check` sin diferencias.
- Playwright: login, creación desde formulario, detalle con auditoría, decisión manual y actualización por SSE.

## Pendiente / conocido
- Latencia de Ollama compartido: en el servidor, algunos items tardaron 2 min en salir de `TRIAGE` (item 7). El timeout de 60 s de httpx no cortó esa espera de forma visible. Pendiente: deadline total explícito alrededor de la llamada.
- `BackgroundTasks` no sobrevive a un reinicio: un item en `RECEIVED`/`TRIAGE` queda colgado. Pendiente: barrido al arrancar (Fase 5 o 7).
- Webhook HMAC y adapters GitHub / Azure DevOps: fuera de esta fase.
