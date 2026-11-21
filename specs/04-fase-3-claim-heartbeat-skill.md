# Spec 04: Fase 3, claim, heartbeat y skill `/factory`

## Objetivo
El dev ejecuta `/factory` y el hub le asigna trabajo pendiente del proyecto; el cliente reporta estado.

## API
- `GET /api/v1/projects/{id}/queue`: pendientes.
- `POST /api/v1/work/{id}/claim`: el primero gana; el segundo recibe 409 "ya cogido por X".
- `POST /api/v1/work/{id}/heartbeat`: último estado + mensaje.
- `POST /api/v1/work/{id}/release`: devolver con motivo (por ejemplo sin crédito).
- `POST /api/v1/work/{id}/events`: eventos y logs.

## Reglas
- Heartbeat sin reporte durante 30 min (configurable) -> vuelve a `QUEUED`.
- Sin crédito o límite: el cliente hace `release` con motivo; el item queda sin asignar hasta renovarse.
- Autenticación: token por dev.

## Skill `/factory` (en `.claude/skills/factory/`)
Lee `.factory/config.yaml` (`projectId`, `hubUrl`), consulta la cola, hace claim y reporta. Si no hay trabajo, solo informa.

## Success Criteria
1. Dos devs, un item: solo uno lo toma.
2. Heartbeat caducado reencola.
3. `/factory` en meme-demo muestra pendientes y hace claim.
4. La etiqueta "taken" aparece en dashboard y remoto.

## Tareas
- [ ] Endpoints claim/heartbeat/release con bloqueo. Verify: test de concurrencia.
- [ ] Job de caducidad. Verify: test con reloj simulado.
- [ ] Skill `/factory` mínimo (cola + claim). Verify: ejecución manual.
- [ ] Tokens por dev. Verify: test de auth.

## Preguntas abiertas
- Instalación del skill en cada máquina (copia o repo compartido).
