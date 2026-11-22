"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavLink = { href: string; label: string; icon: string; roles?: string[] };

const LINKS: NavLink[] = [
  { href: "/board", label: "Tablero", icon: "▦" },
  { href: "/projects", label: "Proyectos", icon: "◫" },
  { href: "/inbox", label: "Bandeja", icon: "✉", roles: ["admin", "developer", "reviewer"] },
  { href: "/approvals", label: "Aprobaciones", icon: "✔" },
  { href: "/status", label: "Estado", icon: "◉" },
];
const ADMIN_LINKS: NavLink[] = [
  { href: "/admin/users", label: "Usuarios", icon: "☺" },
  { href: "/admin/policies", label: "Políticas", icon: "⚖" },
];

function Item({ link, active }: { link: NavLink; active: boolean }) {
  return (
    <Link
      href={link.href}
      aria-current={active ? "page" : undefined}
      className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
        active ? "bg-indigo-600 text-white shadow-sm" : "text-slate-300 hover:bg-white/10 hover:text-white"
      }`}
    >
      <span aria-hidden className="w-4 text-center">{link.icon}</span>
      {link.label}
    </Link>
  );
}

/** Menú lateral (escritorio) / barra superior desplazable (móvil). Los enlaces de admin solo salen a admins; la API lo exige igualmente. */
export function SiteNav({ role, email, logout }: { role: string; email: string; logout: () => Promise<void> }) {
  const pathname = usePathname();
  const visible = (l: NavLink) => !l.roles || l.roles.includes(role);
  const active = (href: string) => pathname === href || pathname.startsWith(`${href}/`) || (href === "/board" && pathname.startsWith("/work"));
  const main = LINKS.filter(visible);
  return (
    <aside className="flex flex-col gap-3 bg-slate-900 p-3 text-white md:sticky md:top-0 md:h-screen md:w-60 md:shrink-0 md:gap-6 md:p-4">
      <div className="flex items-center justify-between gap-2">
        <Link href="/board" className="flex items-center gap-2 px-1 text-lg font-bold tracking-tight">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-indigo-600 text-base">⚙</span>
          AI Factory
        </Link>
        <form action={logout} className="md:hidden">
          <button className="rounded-lg px-3 py-2 text-sm text-slate-300 hover:bg-white/10">Salir</button>
        </form>
      </div>
      <nav aria-label="Principal" className="flex gap-1 overflow-x-auto md:flex-col md:overflow-visible">
        {main.map((l) => <Item key={l.href} link={l} active={active(l.href)} />)}
        {role === "admin" && (
          <>
            <p className="hidden px-3 pt-4 text-xs font-semibold uppercase tracking-wider text-slate-500 md:block">Administración</p>
            {ADMIN_LINKS.map((l) => <Item key={l.href} link={l} active={active(l.href)} />)}
          </>
        )}
      </nav>
      <div className="mt-auto hidden border-t border-white/10 pt-4 text-sm md:block">
        <p className="truncate font-medium">{email}</p>
        <p className="mb-3 text-xs text-slate-400">{role}</p>
        <form action={logout}>
          <button className="w-full rounded-lg border border-white/20 px-3 py-2 text-slate-200 hover:bg-white/10">Cerrar sesión</button>
        </form>
      </div>
    </aside>
  );
}
