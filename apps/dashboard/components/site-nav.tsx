"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/projects", label: "Proyectos" },
  { href: "/board", label: "Tablero" },
  { href: "/inbox", label: "Bandeja" },
  { href: "/approvals", label: "Aprobaciones" },
  { href: "/status", label: "Estado" },
];

const ADMIN_LINKS = [
  { href: "/admin/users", label: "Usuarios" },
  { href: "/admin/policies", label: "Políticas" },
];

/** Navegación común del dashboard. Las pantallas de admin solo aparecen para admins (la API lo exige igualmente). */
export function SiteNav({ isAdmin }: { isAdmin: boolean }) {
  const pathname = usePathname();
  const links = isAdmin ? [...LINKS, ...ADMIN_LINKS] : LINKS;
  return (
    <nav aria-label="Principal" className="mb-6 flex flex-wrap gap-x-4 gap-y-2 border-b pb-3 text-sm">
      {links.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          aria-current={pathname === link.href || pathname.startsWith(`${link.href}/`) ? "page" : undefined}
          className="underline-offset-2 hover:underline"
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
