# Tema de UI del dashboard

`main` usa **un solo tema: Claude** (`apps/dashboard/themes/claude/`, descrito en `claude.md`). No hay interruptor, ni cookie, ni `localStorage` de tema: `app/layout.tsx` fija `<html data-theme="claude">` en el servidor, así que no hay parpadeo. `SiteNav` (menú Proyectos, Tablero, Bandeja, Aprobaciones, Estado y admin) sigue en todas las páginas con sesión.

## Estilo Codex: rama `estilo-codex`
El tema Codex se conserva, con el interruptor Claude/Codex, en la rama `origin/estilo-codex` (Codex es el tema por defecto allí; sin cookie sale Codex).

Verlo:
```sh
git fetch origin && git worktree add ../ai-factory-codex origin/estilo-codex
```

Mezclarlo en `main` (recupera `themes/codex`, `themes/registry.ts`, `components/theme-toggle.tsx`, `themes/toggle.css` y el layout con selector):
```sh
git checkout -b feat/volver-a-dos-temas main && git merge origin/estilo-codex
```
Si hay conflicto en `app/layout.tsx`, gana la versión de `estilo-codex`. Después `npm run lint`, `npx tsc --noEmit` y `npx next build` en `apps/dashboard`.

## Cambiar el aspecto de Claude
Editar `apps/dashboard/themes/claude/theme.css`. Todo selector va acotado a `[data-theme="claude"]`.
