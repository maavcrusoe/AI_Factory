---
name: factory
description: Toma trabajo pendiente del hub de AI Factory para este proyecto, lo reclama y reporta el latido. Usar cuando el dev escribe /factory o pide ver o coger la cola del hub.
---

# /factory

Cliente mínimo de la cola del hub (Fase 3): lista, reclama y reporta. Sin build ni PR todavía (Fase 4).

## Requisitos
- `.factory/config.yaml` en la raíz del repo con `projectId` y `hubUrl` (ver `config.example.yaml`).
- Variable de entorno `FACTORY_TOKEN` con tu token personal (`fct_...`). Nunca va en `config.yaml` ni en el repo.
- `curl` disponible.

## Pasos
1. Leer `.factory/config.yaml`; exporta `PROJECT_ID` (de `projectId`) y `HUB_URL` (de `hubUrl`). Si falta, dile al dev que lo cree a partir del ejemplo y para.
2. Comprobar `FACTORY_TOKEN`. Si falta, dile al dev que cree un token (ver README, sección "Skill /factory") y para.
3. Consultar la cola:
   ```sh
   curl -sS -H "Authorization: Bearer $FACTORY_TOKEN" "$HUB_URL/api/v1/projects/$PROJECT_ID/queue"
   ```
4. Si la lista está vacía, informa "no hay trabajo pendiente en <projectId>" y para. No reclames nada.
5. Si hay items, reclama el más antiguo (primero de la lista, orden por id):
   ```sh
   curl -sS -X POST -H "Authorization: Bearer $FACTORY_TOKEN" "$HUB_URL/api/v1/work/$ID/claim"
   ```
   - `200`: el item es tuyo. Muestra id, título y cuerpo.
   - `409` con `"ya cogido por X"`: otro dev lo tiene. Informa de quién y para. No insistas en bucle.
6. Reporta el latido con el estado actual:
   ```sh
   curl -sS -X POST -H "Authorization: Bearer $FACTORY_TOKEN" -H "Content-Type: application/json" \
     -d '{"state":"working","message":"<qué estás haciendo>"}' "$HUB_URL/api/v1/work/$ID/heartbeat"
   ```
7. Si no puedes seguir (por ejemplo, sin crédito o límite de uso), libera el item con motivo. Queda sin asignar y vuelve a la cola:
   ```sh
   curl -sS -X POST -H "Authorization: Bearer $FACTORY_TOKEN" -H "Content-Type: application/json" \
     -d '{"reason":"sin crédito"}' "$HUB_URL/api/v1/work/$ID/release"
   ```

## Reglas
- Si el motivo o el mensaje tienen tildes y el shell no envía UTF-8, el hub responde `There was an error parsing the body`. Usa `--data-binary @fichero.json` con el JSON guardado en UTF-8, o escribe texto sin tildes.
- Un claim por invocación. Si el dev quiere más, que vuelva a ejecutar `/factory`.
- Sin latido durante 30 min (configurable en el hub), el item vuelve a la cola solo.
- Nunca imprimas `FACTORY_TOKEN` ni lo escribas en ficheros.
- Si el hub no responde, informa del error de conexión y para.
