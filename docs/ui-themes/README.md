# Temas de UI del dashboard

El dashboard incluye dos temas, **Claude** (por defecto) y **Codex**, y un selector visible en todas las páginas (también en login), arriba a la derecha.

## Cómo funciona el selector
- Registro único: `apps/dashboard/themes/registry.ts` (`id`, `label`, `description`).
- Componente: `components/theme-toggle.tsx`, un `radiogroup` con radios nativos (flechas de teclado, foco visible, sin movimiento con `prefers-reduced-motion`). Estilos neutros en `themes/toggle.css`.
- Al elegir: cambia `<html data-theme>` al instante (sin recarga) y guarda cookie `ai-factory-theme` (1 año) y `localStorage` como respaldo.
- `app/layout.tsx` lee la cookie en el servidor, así el HTML ya sale con el tema correcto (sin parpadeo). Sin cookie, un script mínimo en `<head>` recupera `localStorage` antes del primer pintado. Por defecto: `claude`.
- Los CSS de ambos temas se cargan siempre; no se filtran entre sí porque todo selector va acotado a `[data-theme="<id>"]`.

## Añadir un tema
1. Crear `apps/dashboard/themes/<id>/` con `index.ts` (`id`, `label`, `description`) y `theme.css` acotado a `[data-theme="<id>"]`.
2. Importar su CSS en `app/layout.tsx`.
3. Añadir una línea en `THEMES` de `themes/registry.ts`.

## Retirar el tema perdedor
1. Quitar su línea de `THEMES` en `registry.ts` y su import de CSS en `app/layout.tsx`.
2. Borrar `themes/<id>/` y `docs/ui-themes/<id>.md`.
3. Si es Codex: quitar `<codex.Masthead />` y su import del layout; los atributos `data-screen` de las páginas son inocuos y pueden quedarse.
4. Si queda un solo tema: quitar `<ThemeToggle />` y `toggle.css`, y fijar `DEFAULT_THEME`.
