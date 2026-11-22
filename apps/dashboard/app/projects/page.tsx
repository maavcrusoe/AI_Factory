import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LiveRefresh } from "@/components/live-refresh";
import { StatusBadge } from "@/components/status-badge";
import { fetchJson, type Me, type ProjectSummary, STATUS_LABEL } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";

export const instant = false;

/** Resumen de proyectos: cuántos items hay en cada estado y acceso al tablero de cada uno. */
export default async function ProjectsPage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const [me, projects] = await Promise.all([
    fetchJson<Me>("/api/v1/auth/me", token),
    fetchJson<ProjectSummary[]>("/api/v1/projects", token),
  ]);
  if (!me || !projects) redirect("/login");

  return (
    <main className="mx-auto w-full max-w-4xl gap-6 p-4 sm:p-8">
      <LiveRefresh />
      <h1 className="mb-4 text-2xl font-semibold">Proyectos</h1>

      {projects.length === 0 ? <p className="text-neutral-600">No hay proyectos todavía.</p> : null}
      <ul data-testid="projects" className="grid gap-3">
        {projects.map((project) => (
          <li key={project.slug} className="grid gap-3 rounded border p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <div>
                <span className="font-medium">{project.name}</span>{" "}
                <span className="font-mono text-xs text-neutral-500">{project.slug}</span>
              </div>
              <Link href={`/board?project=${encodeURIComponent(project.slug)}`} className="text-sm underline">
                Ver tablero ({project.total})
              </Link>
            </div>
            {Object.keys(project.by_status).length === 0 ? (
              <p className="text-sm text-neutral-500">Sin items.</p>
            ) : (
              <ul className="flex flex-wrap gap-2 text-xs">
                {Object.entries(project.by_status).map(([status, count]) => (
                  <li key={status} className="flex items-center gap-1">
                    <StatusBadge status={status} />
                    <span className="text-neutral-600">{count}</span>
                    <span className="sr-only">{STATUS_LABEL[status] ?? status}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
