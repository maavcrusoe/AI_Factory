---
name: factory
description: Toma la siguiente petición del hub de AI Factory, la construye en una rama factory/<id> con planner, builder, gate y revisores, y abre un PR en borrador. Usar cuando el dev escribe /factory o pide coger trabajo de la cola del hub.
---

# /factory

Pipeline del cliente (Fase 4). Corre en tu máquina con tu cuenta de Claude y tu sesión `gh`. El hub solo guarda estado, logs y diffs.

## Requisitos
- `.factory/config.yaml` en la raíz del clon del proyecto, con `projectId` y `hubUrl` (ver `config.example.yaml`).
- `checks.sh` en la raíz del proyecto: es el gate. Debe salir con 0 si todo está bien.
- Variable de entorno `FACTORY_TOKEN` con tu token personal (`fct_...`). Nunca va en `config.yaml` ni en el repo.
- `gh` autenticado (`gh auth status`), `git`, `python` 3.12 y `claude` en el PATH.

## Ejecutar
Desde la raíz de AI_Factory:

```sh
python .claude/skills/factory/scripts/pipeline.py --repo <ruta-al-clon-del-proyecto> [--item N]
```

- Sin `--item`, toma la primera petición de la cola. Con `--item N`, reclama esa.
- Si el proceso se corta, vuelve a ejecutar el mismo comando: reanuda desde `<clon>.factory/runs/<id>/state.json` sin reclamar de nuevo.
- Lanza en segundo plano si tarda (`run_in_background`): una ejecución completa puede durar varios minutos.

## Etapas
1. **claim**: `POST /api/v1/work/{id}/claim`. Si el hub responde 409, otro dev lo tiene; el pipeline para.
2. **worktree**: `git worktree add -b factory/<id> <clon>.factory/worktrees/<id> origin/main`. Solo ramas `factory/*`.
3. **plan**: agente `planner` escribe `.factory/specs/<id>/spec.md` en la rama.
4. **build**: agente `builder` implementa. Si el spec no vale, escribe `SPEC_PROBLEM:` y vuelve a plan (una vez).
5. **gate**: `checks.sh` en el worktree. Resultado por ronda en el hub.
6. **revisores**: `code-reviewer` y `test-reviewer`. Cualquier cambio pedido vuelve a build.
7. **diff**: `git diff origin/main...HEAD` se sube al hub.
8. **push y PR**: `git push origin factory/<id>`; `gh pr create --draft` con `Closes #N` si el item tiene issue enlazado.
9. **complete**: el hub pasa el item a `PR_OPEN`.

Cada etapa sube logs o diffs al hub y actualiza el latido (cada 60 s).

## Límites
- Máximo 3 rondas de builder. Gate rojo o revisión con cambios tras la tercera: liberación con motivo `necesita humano: ...` y `failure_report` en el hub.
- Sin crédito o con límite de uso de Claude: liberación con motivo `necesita humano: sin crédito o límite de uso ...`.
- Nunca haces merge. Nunca empujas ramas que no sean `factory/*`.

## Reglas
- Nunca imprimas `FACTORY_TOKEN` ni lo escribas en ficheros.
- Si el hub no responde, el pipeline guarda las subidas en `outbox.jsonl` y las reenvía al reanudar.
- Si pierdes el claim (409 en el latido), el pipeline para sin liberar: el hub ya decidió.
- Los agentes viven en `.claude/agents/` de este repo, no en el worktree: no acaban en el PR.
