import { cookies } from "next/headers";
import type { ReactNode } from "react";
import { logoutAction } from "@/app/login/actions";
import { fetchJson, type Me } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";
import { SiteNav } from "./site-nav";

/** Marco común: menú lateral + contenido. Sin sesión válida (login) se muestra el contenido a pantalla completa. */
export async function AppShell({ children }: { children: ReactNode }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const me = token ? await fetchJson<Me>("/api/v1/auth/me", token) : null;
  if (!me) return <>{children}</>;
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <SiteNav role={me.role} email={me.email} logout={logoutAction} />
      <div className="min-w-0 flex-1 p-4 sm:p-8">{children}</div>
    </div>
  );
}
