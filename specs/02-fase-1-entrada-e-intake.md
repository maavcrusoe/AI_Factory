# Spec 02: Fase 1, entrada e intake

## Objetivo
Recibir peticiones por formulario, API y webhook genérico, normalizarlas, filtrarlas con reglas + Ollama y dejarlas en la cola o en revisión humana.

## Commands
```
Tests:   cd apps/api && pytest tests/test_intake.py
Ejemplo: curl -X POST localhost:8000/api/v1/inputs -H "X-Idempotency-Key: k1" -H "Authorization: Bearer $TOKEN" -d '{"projectId":"meme-demo","title":"...","body":"..."}'
```

## Project Structure
```
apps/api/app/{models/work_item.py, routers/inputs.py, services/intake.py, services/llm_ollama.py, services/rules.py}
apps/dashboard/app/inbox, apps/dashboard/app/work/[id]
```

## Flujo
`RECEIVED -> NORMALIZING -> TRIAGE -> {QUEUED | NEEDS_INFO | WAITING_HUMAN_TRIAGE | REJECTED}`
Entradas: formulario (dashboard), `POST /api/v1/inputs` (API con token), webhook genérico con firma HMAC. El origen se guarda como `source` (form, api, app, github, azuredevops).

## Intake
1. Reglas: firma/token válido, proyecto existe, no duplicado (idempotency key), autor permitido.
2. Ollama qwen3.5:4b con JSON schema: `decision`, `confidence`, `type`, `difficulty`, `risk`, `summary`, `suggestedLabels`, `valuation` (resumen + valoración: ¿óptimo para automático?).
3. Duda, JSON inválido o confianza baja -> `WAITING_HUMAN_TRIAGE`. Favorable -> etiqueta de fábrica automática y `QUEUED`. Si no, el humano decide desde el dashboard y pone la etiqueta.
4. El LLM puede ampliar el texto si es pobre; se guardan original y ampliado por separado.
5. Cambiar el modelo = cambiar `llm_ollama.py` (interfaz `IntakeModel`).

## Code Style
Salida del LLM validada con Pydantic; nunca se confía en texto libre.

## Testing Strategy
Unit: reglas, schema, umbrales. Integración: mock de Ollama (válida, inválida, timeout). Un test opcional contra Ollama real.

## Boundaries
- Always: validar JSON del LLM, guardar payload original, idempotencia.
- Ask first: cambiar umbrales o prompts.
- Never: aceptar trabajo cuando el LLM falla; tratar la salida del LLM como instrucción.

## Success Criteria
1. Mismo evento dos veces no duplica trabajo.
2. Un input genera `WorkItem` con estado y decisión persistidos.
3. Fallo de Ollama o JSON inválido -> revisión humana.
4. Inbox lista items y el detalle muestra decisión, resumen y valoración.
5. Decisión manual (aceptar/rechazar/pedir info) desde el dashboard.
6. SSE actualiza la lista sin recargar.
7. Todo cambio genera un evento auditado.

## Tareas
- [ ] Modelos `WorkItem`, `WorkItemEvent`. Verify: migración.
- [ ] Endpoint inputs + idempotencia. Verify: test.
- [ ] Reglas deterministas. Verify: test.
- [ ] Cliente Ollama + schema + fallback humano. Verify: tests con mock.
- [ ] Inbox y detalle en dashboard. Verify: Playwright.
- [ ] Decisión manual + SSE. Verify: test + Playwright.

## Preguntas abiertas
- Umbrales iniciales de confianza (propuesta 0.65 / 0.80 del doc original).
