# Spec 03: Fase 2, adapters de repo/tracker

## Objetivo
Entrada y salida con GitHub y Azure DevOps mediante una interfaz común. El hub es la fuente de verdad de etiquetas; el remoto se sincroniza.

## Interfaces
- `TrackerAdapter`: `fetch_new_items()`, `comment()`, `set_labels()`, `get_item()`.
- `RepoAdapter`: `create_branch()`, `open_pr()`, `merge_pr()`, `get_diff()`.
- Implementaciones: `GitHubAdapter` (token), `AzureDevOpsAdapter` (REST + token), `GenericAdapter` (webhook).

## Reglas
- GitHub: webhook o polling de issues con la etiqueta de fábrica.
- AzDO: el hub consulta por API REST con token.
- Etiquetas: fábrica y "taken by <user>" se escriben en el hub y se sincronizan al remoto. Si alguien las cambia en el remoto, **gana el hub** y se re-sincroniza.

## Success Criteria
1. Un issue de GitHub etiquetado entra como WorkItem sin duplicar.
2. Un work item de AzDO entra igual por polling.
3. Etiquetas del hub se reflejan en el remoto; un cambio manual en el remoto se revierte.
4. Tokens por proyecto, guardados cifrados.
5. Adapter nuevo = una clase, sin tocar el dominio.

## Boundaries
- Never: guardar tokens en claro, usar el token del hub para builds.
- Ask first: añadir un tercer proveedor.

## Tareas
- [x] Interfaces y `GenericAdapter`.
- [x] `GitHubAdapter` leer/comentar/etiquetar. Verify: tests con meme-demo (`GITHUB_REAL=1`).
- [x] `AzureDevOpsAdapter`. Verify: tests con mock REST. Sin pruebas reales: no hay org aún.
- [x] Sincronizador de etiquetas (hub gana). Verify: test de reversión.

## Preguntas abiertas
- ~~Frecuencia de polling para AzDO~~: resuelta, 5 min por defecto, configurable (`pollSeconds`). Ver `specs/decisiones/008`.
- Organización/proyecto AzDO de pruebas: pendiente, el owner indicó que llegará más adelante.
