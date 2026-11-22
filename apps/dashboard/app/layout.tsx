export const instant = false;

import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import "@/themes/claude/theme.css";

export const metadata: Metadata = {
  title: "AI Factory",
  description: "Dashboard del hub de AI Factory",
};

/** Único tema: Claude. El estilo Codex vive en la rama `estilo-codex` (ver docs/ui-themes/README.md). */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" data-theme="claude" className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">{children}</body>
    </html>
  );
}
