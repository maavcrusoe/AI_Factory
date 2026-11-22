import type { Metadata } from "next";
import { cookies } from "next/headers";
import type { ReactNode } from "react";
import "./globals.css";
import "@/themes/claude/theme.css";
import "@/themes/codex/theme.css";
import "@/themes/toggle.css";
import { ThemeToggle } from "@/components/theme-toggle";
import codex from "@/themes/codex";
import { DEFAULT_THEME, THEME_COOKIE, isThemeId } from "@/themes/registry";

export const metadata: Metadata = {
  title: "AI Factory",
  description: "Dashboard del hub de AI Factory",
};

/** Sin cookie, recupera la elección de localStorage antes del primer pintado. */
const FALLBACK_SCRIPT = `try{var c=document.cookie.indexOf("${THEME_COOKIE}=")>-1;var t=localStorage.getItem("${THEME_COOKIE}");if(!c&&t)document.documentElement.dataset.theme=t}catch(e){}`;

export default async function RootLayout({ children }: { children: ReactNode }) {
  const stored = (await cookies()).get(THEME_COOKIE)?.value;
  const theme = isThemeId(stored) ? stored : DEFAULT_THEME;
  return (
    <html lang="es" data-theme={theme} className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: FALLBACK_SCRIPT }} />
      </head>
      <body className="min-h-full flex flex-col font-sans">
        <codex.Masthead />
        <div className="theme-bar">
          <ThemeToggle initial={theme} />
        </div>
        {children}
      </body>
    </html>
  );
}
