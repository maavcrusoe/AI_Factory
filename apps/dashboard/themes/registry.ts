import claude from "./claude";
import codex from "./codex";

/** Registro de temas. Para añadir uno: crear themes/<id>/ con CSS acotado a [data-theme="<id>"], importar su CSS en app/layout.tsx y añadir una línea aquí. */
export const THEMES = [
  { id: claude.id, label: claude.label, description: claude.description },
  { id: codex.id, label: codex.label, description: codex.description },
] as const;

export type ThemeId = (typeof THEMES)[number]["id"];

export const DEFAULT_THEME: ThemeId = "claude";
export const THEME_COOKIE = "ai-factory-theme";

export function isThemeId(value: unknown): value is ThemeId {
  return THEMES.some((t) => t.id === value);
}
