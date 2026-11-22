import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import theme from "@/themes/codex";

export const metadata: Metadata = {
  title: "AI Factory",
  description: "Dashboard del hub de AI Factory",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es" data-theme={theme.id} className="h-full antialiased">
      <body className="min-h-full flex flex-col font-sans">
        <theme.Masthead />
        {children}
      </body>
    </html>
  );
}
