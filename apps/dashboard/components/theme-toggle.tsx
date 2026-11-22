"use client";

import { useState } from "react";
import { THEMES, THEME_COOKIE, type ThemeId } from "@/themes/registry";

/** Selector de tema (radiogroup nativo: flechas de teclado incluidas). Cambia <html data-theme> al instante y persiste en cookie + localStorage. */
export function ThemeToggle({ initial }: { initial: ThemeId }) {
  const [theme, setTheme] = useState<ThemeId>(initial);

  function choose(id: ThemeId) {
    setTheme(id);
    document.documentElement.dataset.theme = id;
    document.cookie = `${THEME_COOKIE}=${id}; path=/; max-age=31536000; samesite=lax`;
    try {
      localStorage.setItem(THEME_COOKIE, id);
    } catch {}
  }

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
              onChange={() => choose(t.id)}
            />
            <span>{t.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

