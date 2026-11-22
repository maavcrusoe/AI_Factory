"use client";

import { useSyncExternalStore } from "react";
import { THEMES, THEME_COOKIE, isThemeId, type ThemeId } from "@/themes/registry";

/** Aplica y persiste la elección: <html data-theme> al instante, cookie (SSR sin parpadeo) y localStorage (respaldo). */
function applyTheme(id: ThemeId) {
  document.documentElement.dataset.theme = id;
  document.cookie = `${THEME_COOKIE}=${id}; path=/; max-age=31536000; samesite=lax`;
  try {
    localStorage.setItem(THEME_COOKIE, id);
  } catch {}
}

function subscribe(cb: () => void) {
  const mo = new MutationObserver(cb);
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => mo.disconnect();
}

/** Selector de tema (radiogroup nativo: flechas de teclado incluidas). El estado vive en <html data-theme>. */
export function ThemeToggle({ initial }: { initial: ThemeId }) {
  const attr = useSyncExternalStore(
    subscribe,
    () => document.documentElement.dataset.theme,
    () => initial,
  );
  const theme = isThemeId(attr) ? attr : initial;

  return (
    <fieldset className="theme-toggle" data-testid="theme-toggle">
      <legend className="theme-toggle__legend">Tema</legend>
      <div role="radiogroup" aria-label="Tema visual" className="theme-toggle__group">
        {THEMES.map((t) => (
          <label key={t.id} className="theme-toggle__option" title={t.description}>
            <input
              type="radio"
              name="theme"
              value={t.id}
              checked={theme === t.id}
              onChange={() => {
                applyTheme(t.id);
              }}
            />
            <span>{t.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
