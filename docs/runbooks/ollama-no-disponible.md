# Ollama no disponible

El intake clasifica cada petición con Ollama (`OLLAMA_URL`, modelo `OLLAMA_MODEL`, por defecto
`qwen3.5:4b`). Si Ollama no responde, **el hub no acepta ni rechaza nada por su cuenta**: el item pasa a
`WAITING_HUMAN_TRIAGE` con un evento `intake_failed` y el motivo. La decisión la toma una persona.

Lo que sí sigue funcionando: entrada de peticiones (webhooks, formulario, API), la cola, los claims, el
dashboard y el merge. Solo se para la valoración automática.

## Síntomas

- Items nuevos quedan en `WAITING_HUMAN_TRIAGE` con `intake_failed` (motivo: timeout o conexión).
- `factory_errors_total{kind="intake_failed"}` sube en `/metrics` (ver `metricas-y-logs.md`).
- En logs: eventos de la API con el fallo del intake.

## Diagnóstico

1. Desde el servidor, ¿responde Ollama?
   ```sh
   curl -s -m 5 http://192.168.100.6:11434/api/tags | head -c 300; echo
   ```
2. Desde el contenedor de la API (es el que llama; comprueba la ruta de red de Docker):
   ```sh
   docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://192.168.100.6:11434/api/tags', timeout=5).status)"
   ```
   Si (1) funciona y (2) no, revisa la red: el servicio `api` sale por la red `edge`.
3. ¿Está el modelo cargado? `curl -s http://<ollama>:11434/api/tags` debe listar `qwen3.5:4b`.
4. ¿La URL es la correcta? `OLLAMA_URL` en `.env`; tras cambiarla, `docker compose up -d api`.

## Qué hacer

- **Ollama caído**: reiniciar el servicio de Ollama en su host. No hace falta tocar el hub.
- **Modelo no descargado**: `ollama pull qwen3.5:4b` en el host de Ollama.
- **Lentitud**: el plazo total del intake es `INTAKE_DEADLINE_SECONDS` (60 s). Subirlo solo si el modelo
  responde bien pero tarda más de lo normal; un valor alto retrasa la revisión humana.

## Items que quedaron en revisión humana

Cuando Ollama vuelve, **los items ya pasados a `WAITING_HUMAN_TRIAGE` no se reintentan solos**. Hay dos
caminos, ambos humanos:

- Decidir en `/inbox`: aceptar (pasa a `QUEUED`) o rechazar.
- Si la petición original sigue en el origen (GitHub, Azure DevOps), reenviarla con una clave de
  idempotencia nueva: el hub la trata como petición nueva y pasa por el intake otra vez.

Nunca se acepta por defecto. Si un item de Ollama caído lleva días sin decidir, es una cola de humanos,
no un fallo del hub.
