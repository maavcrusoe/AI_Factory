# Plan de implementación

Specs aprobadas por el owner (2026-11-21). Fuente: `specs/00`–`08`.

## Valores por defecto asumidos (cambiar si no valen)
- Postgres 16 en Docker solo para la DB; API y dashboard corren con `npm run dev`/uvicorn.
- Umbrales de confianza del intake: 0.65 / 0.80.
- Polling de Azure DevOps cada 5 min. Org/proyecto de pruebas: pendiente.
- Skill `/factory`: copia desde este repo.
- 2 reviewers al empezar (code, test).
- Paths sensibles: definidos por proyecto en `.factory/config.yaml`.
- Retención de logs: 30 días. Servidor y SO de despliegue: pendiente (Fase 7).

## Orden y dependencias
F0 -> F1 -> F2 -> F3 -> F4 -> F5 -> F6 -> F7. F6 (dashboard) puede avanzar en paralelo a F4/F5 sobre los eventos ya existentes.

## Riesgos
- qwen3.5:4b puede dar JSON inválido o decisiones flojas: mitigado con validación Pydantic y revisión humana ante duda.
- Heartbeat/claim con concurrencia: bloqueo en Postgres y test de concurrencia.
- Sync de etiquetas con el remoto: el hub gana; evitar bucles con marca de origen del cambio.

## Puntos de verificación
Al final de cada fase: tests verdes, la pantalla verificada con Playwright, memoria actualizada, aprobación del owner.
