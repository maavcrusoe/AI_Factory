import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LiveRefresh } from "@/components/live-refresh";
import { SiteNav } from "@/components/site-nav";
import { fetchJson, type Me, type MergePolicy, type PlatformSettings, type ProjectSummary } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";
import { savePolicyAction } from "../actions";

export const instant = false;

const DIFFICULTY_OPTIONS = [
  { value: "low", label: "Baja" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
];
const MEANING_OPTIONS = [
  { value: "none", label: "Ninguno" },
  { value: "minor", label: "Menor" },
  { value: "major", label: "Mayor" },
  { value: "dubious", label: "Dudoso" },
];

const ERRORS: Record<string, string> = {
  conflict: "Otra edición ganó a la tuya. Recarga y vuelve a guardar.",
  invalid: "La política no es válida.",
  forbidden: "Solo un admin puede editar la política.",
  failed: "No se pudo guardar la política.",
};

/** Admin: política de merge por proyecto. Guardar crea una versión nueva; las anteriores quedan como historial. */
export default async function AdminPoliciesPage({
  searchParams,
}: {
  searchParams: Promise<{ project?: string; saved?: string; error?: string }>;
}) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  const me = await fetchJson<Me>("/api/v1/auth/me", token);
  if (!me) redirect("/login");
  if (me.role !== "admin") redirect("/board");

  const { project: requested, saved, error } = await searchParams;
  const projects = (await fetchJson<ProjectSummary[]>("/api/v1/projects", token)) ?? [];
  const slug = projects.find((p) => p.slug === requested)?.slug ?? projects[0]?.slug;
  const settings = await fetchJson<PlatformSettings>("/api/v1/settings", token);
  const policy = slug
    ? await fetchJson<MergePolicy>(`/api/v1/projects/${encodeURIComponent(slug)}/merge-policy`, token)
    : null;
  const body = policy?.body;

  return (
    <main data-screen="policies" className="mx-auto w-full max-w-3xl gap-6 p-4 sm:p-8">
      <LiveRefresh />
      <h1 className="mb-4 text-2xl font-semibold">Políticas</h1>
      <SiteNav isAdmin />

      {saved ? (
        <p role="status" className="mb-4 rounded bg-green-50 p-3 text-sm text-green-900">
          Política guardada como versión nueva.
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-800">
          {ERRORS[error] ?? ERRORS.failed}
        </p>
      ) : null}

      {projects.length === 0 || !slug || !body || !policy ? (
        <p className="text-neutral-600">No hay proyectos con política todavía.</p>
      ) : (
        <>
          <form method="get" className="mb-6 flex flex-wrap items-end gap-3">
            <label className="grid gap-1 text-sm">
              Proyecto
              <select name="project" defaultValue={slug} className="rounded border px-2 py-2">
                {projects.map((project) => (
                  <option key={project.slug} value={project.slug}>
                    {project.name}
                  </option>
                ))}
              </select>
            </label>
            <button type="submit" className="rounded border px-4 py-2 hover:bg-neutral-100">
              Cambiar
            </button>
          </form>

          <p className="mb-4 text-sm text-neutral-600" data-testid="policy-version">
            Versión {policy.version}
            {policy.version === 0 ? " (por defecto: todo merge pide humano)" : ""}
          </p>

          <form action={savePolicyAction} className="grid gap-5 rounded border p-4" aria-label="Política de merge">
            <input type="hidden" name="project" value={slug} />
            <fieldset className="grid gap-2 text-sm">
              <legend className="font-medium">Cuándo pedir humano</legend>
              <label className="flex items-center gap-2">
                <input type="checkbox" name="require_human_always" defaultChecked={body.require_human_always} />
                Siempre (ignora el resto de reglas)
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" name="human_if_unplanned" defaultChecked={body.human_if_unplanned} />
                Funcionalidad no planificada
              </label>
              <div className="flex flex-wrap gap-4">
                <span>Dificultad:</span>
                {DIFFICULTY_OPTIONS.map((option) => (
                  <label key={option.value} className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      name="human_if_difficulty"
                      value={option.value}
                      defaultChecked={body.human_if_difficulty.includes(option.value)}
                    />
                    {option.label}
                  </label>
                ))}
              </div>
              <div className="flex flex-wrap gap-4">
                <span>Significado del cambio:</span>
                {MEANING_OPTIONS.map((option) => (
                  <label key={option.value} className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      name="human_if_meaning"
                      value={option.value}
                      defaultChecked={body.human_if_meaning.includes(option.value)}
                    />
                    {option.label}
                  </label>
                ))}
              </div>
            </fieldset>

            <label className="grid gap-1 text-sm">
              Rutas sensibles (una por línea, admite <code>**</code>; cualquier coincidencia pide humano)
              <textarea
                name="sensitive_paths"
                rows={5}
                defaultValue={body.sensitive_paths.join("\n")}
                className="rounded border px-3 py-2 font-mono text-xs"
              />
            </label>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-neutral-500">
                Guardar crea una versión nueva; las anteriores se conservan para la auditoría.
              </p>
              <button type="submit" className="rounded bg-neutral-900 px-4 py-2 text-white">
                Guardar nueva versión
              </button>
            </div>
          </form>
        </>
      )}

      <section className="mt-8 grid gap-2 text-sm" aria-label="Retención">
        <h2 className="font-medium">Retención de logs</h2>
        <p>
          Los logs del pipeline se borran a los{" "}
          <span data-testid="retention-days" className="font-medium">
            {settings?.log_retention_days ?? "—"}
          </span>{" "}
          días (variable <code>LOG_RETENTION_DAYS</code>, por defecto 30). Diffs e informes se conservan.
        </p>
      </section>
    </main>
  );
}
