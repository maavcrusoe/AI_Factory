import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { HeartbeatAge } from "@/components/heartbeat-age";
import { LiveRefresh } from "@/components/live-refresh";
import { SiteNav } from "@/components/site-nav";
import { StatusBadge } from "@/components/status-badge";
import {
  BOARD_COLUMNS,
  fetchJson,
  type Me,
  type PlatformSettings,
  type ProjectSummary,
  SOURCES,
  STATUS_LABEL,
  type WorkItem,
} from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";

export const instant = false;

const FILTER_KEYS = ["project", "owner", "source", "status"] as const;
type Filters = Partial<Record<(typeof FILTER_KEYS)[number], string>>;

/** Tablero Kanban por estado. Los filtros viajan en la URL y los filtra la API. */
export default async function BoardPage({ searchParams }: { searchParams: Promise<Filters> }) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const filters = await searchParams;
  const query = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    const value = filters[key]?.trim();
    if (value) query.set(key, value);
  }

  const [me, settings, projects, items] = await Promise.all([
    fetchJson<Me>("/api/v1/auth/me", token),
    fetchJson<PlatformSettings>("/api/v1/settings", token),
    fetchJson<ProjectSummary[]>("/api/v1/projects", token),
    fetchJson<WorkItem[]>(`/api/v1/inputs?${query}`, token),
  ]);
  if (!me || !settings || !projects || !items) redirect("/login");

  return (
    <main className="mx-auto w-full max-w-7xl gap-6 p-4 sm:p-8">
      <LiveRefresh />
      <h1 className="mb-4 text-2xl font-semibold">Tablero</h1>
      <SiteNav isAdmin={me.role === "admin"} />

      <form method="get" aria-label="Filtros" className="mb-6 grid gap-3 rounded border p-4 sm:grid-cols-2 lg:grid-cols-5">
        <label className="grid gap-1 text-sm">
          Proyecto
          <select name="project" defaultValue={filters.project ?? ""} className="rounded border px-2 py-2">
            <option value="">Todos</option>
            {projects.map((project) => (
              <option key={project.slug} value={project.slug}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          Dueño (email)
          <input name="owner" defaultValue={filters.owner ?? ""} placeholder="cualquiera" className="rounded border px-2 py-2" />
        </label>
        <label className="grid gap-1 text-sm">
          Origen
          <select name="source" defaultValue={filters.source ?? ""} className="rounded border px-2 py-2">
            <option value="">Todos</option>
            {SOURCES.map((source) => (
              <option key={source} value={source}>
                {source}
              </option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          Estado
          <select name="status" defaultValue={filters.status ?? ""} className="rounded border px-2 py-2">
            <option value="">Todos</option>
            {Object.keys(STATUS_LABEL).map((status) => (
              <option key={status} value={status}>
                {STATUS_LABEL[status]}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="self-end rounded bg-neutral-900 px-4 py-2 text-white">
          Filtrar
        </button>
      </form>

      <p className="mb-3 text-xs text-neutral-500">
        {items.length} items (máximo 200, los más nuevos primero).
      </p>

      <div data-testid="board" className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {BOARD_COLUMNS.map((column) => {
          const cards = items.filter((item) => column.statuses.includes(item.status));
          return (
            <section key={column.title} aria-label={column.title} className="grid content-start gap-2 rounded bg-neutral-50 p-2">
              <h2 className="flex items-center justify-between text-sm font-medium">
                <span>{column.title}</span>
                <span data-testid="column-count" className="text-neutral-500">
                  {cards.length}
                </span>
              </h2>
              {cards.length === 0 ? <p className="px-1 text-xs text-neutral-500">Vacía</p> : null}
              {cards.map((item) => (
                <Link
                  key={item.id}
                  href={`/work/${item.id}`}
                  data-testid="card"
                  className="grid gap-1 rounded border bg-white p-3 text-sm hover:bg-neutral-100"
                >
                  <span className="font-medium">
                    #{item.id} {item.title}
                  </span>
                  <span className="flex flex-wrap gap-2 text-xs text-neutral-600">
                    {item.project_slug ? <span>{item.project_slug}</span> : null}
                    <span>origen: {item.source}</span>
                  </span>
                  <StatusBadge status={item.status} />
                  {item.owner ? (
                    <span className="grid gap-1 text-xs">
                      <span data-testid="owner">{item.owner}</span>
                      <HeartbeatAge lastHeartbeatAt={item.last_heartbeat_at} timeoutSeconds={settings.heartbeat_timeout_seconds} />
                    </span>
                  ) : null}
                </Link>
              ))}
            </section>
          );
        })}
      </div>
    </main>
  );
}
