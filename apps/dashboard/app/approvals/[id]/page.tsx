import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { SiteNav } from "@/components/site-nav";
import { StatusBadge } from "@/components/status-badge";
import { apiFetch, fetchJson, type Me, type WorkArtifact, type WorkItemDetail } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";
import { approveAction, mergeAction, requestChangesAction } from "../actions";

export const instant = false;

const ERRORS: Record<string, string> = {
  stale: "Alguien decidió antes o el item cambió. Recarga y decide sobre la versión actual. Si el PR cambió, hace falta un nuevo informe del cliente.",
  forbidden: "Tu rol no permite esta decisión. Solo revisores y admins aprueban y mergean.",
  failed: "No se pudo completar la decisión.",
};
const MAX_DIFF_CHARS = 60_000;

export default async function ApprovalPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ error?: string }>;
}) {
  const { id } = await params;
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const response = await apiFetch(`/api/v1/inputs/${id}`, token).catch(() => null);
  if (!response || response.status === 401) redirect("/login");
  if (response.status === 404) notFound();
  const item = (await response.json()) as WorkItemDetail;
  const artifactsResponse = await apiFetch(`/api/v1/work/${id}/artifacts`, token).catch(() => null);
  const artifacts: WorkArtifact[] = artifactsResponse?.ok ? await artifactsResponse.json() : [];
  const diff = artifacts.filter((a) => a.kind === "diff").at(-1)?.content ?? null;
  const { error } = await searchParams;
  const me = await fetchJson<Me>("/api/v1/auth/me", token);

  const waiting = item.status === "WAITING_HUMAN_MERGE";
  const ready = item.status === "READY_TO_MERGE";

  return (
    <main data-screen="approval" className="mx-auto w-full max-w-3xl gap-6 p-4 sm:p-8">
      <SiteNav isAdmin={me?.role === "admin"} />
      <Link href="/approvals" className="text-sm underline">
        ← Aprobaciones
      </Link>
      <header className="mt-4 mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">
          #{item.id} {item.title}
        </h1>
        <StatusBadge status={item.status} />
      </header>

      {error ? (
        <p role="alert" className="mb-6 rounded bg-red-50 p-3 text-sm text-red-800">
          {ERRORS[error] ?? ERRORS.failed}
        </p>
      ) : null}

      <section className="mb-6 grid gap-3" aria-label="Gate final">
        <h2 className="font-medium">Gate final</h2>
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <Field label="Resultado" value={item.gate_result ?? "—"} />
          <Field label="SHA" value={item.gate_sha ? item.gate_sha.slice(0, 12) : "—"} />
          <Field label="Significado" value={item.meaning_change ?? "—"} />
          <Field label="Planificada" value={item.planned === null ? "—" : item.planned ? "sí" : "no"} />
          <Field label="Dificultad" value={item.difficulty ?? "—"} />
          <Field label="Versión" value={String(item.approval_version)} />
        </dl>
        {item.pr_url ? (
          <a href={item.pr_url} className="text-sm underline" target="_blank" rel="noreferrer">
            PR #{item.pr_number}
          </a>
        ) : null}
      </section>

      <section className="mb-6 grid gap-2" aria-label="Política">
        <h2 className="font-medium">Por qué pide humano</h2>
        {item.policy_reasons && item.policy_reasons.length > 0 ? (
          <ul className="list-disc pl-5 text-sm">
            {item.policy_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-600">Sin política evaluada todavía.</p>
        )}
        {item.touched_paths && item.touched_paths.length > 0 ? (
          <details className="text-sm">
            <summary>Rutas tocadas ({item.touched_paths.length})</summary>
            <ul className="pl-5 font-mono text-xs">
              {item.touched_paths.map((path) => (
                <li key={path}>{path}</li>
              ))}
            </ul>
          </details>
        ) : null}
      </section>

      <section className="mb-6 grid gap-2" aria-label="Hallazgos del revisor">
        <h2 className="font-medium">Hallazgos del revisor</h2>
        {item.review_findings && item.review_findings.length > 0 ? (
          item.review_findings.map((finding, index) => (
            <pre key={index} className="whitespace-pre-wrap rounded bg-neutral-50 p-3 text-xs">
              {finding}
            </pre>
          ))
        ) : (
          <p className="text-sm text-neutral-600">Sin hallazgos registrados.</p>
        )}
      </section>

      <section className="mb-6 grid gap-2" aria-label="Diff">
        <h2 className="font-medium">Diff</h2>
        {diff ? (
          <pre data-testid="diff" className="max-h-[60vh] overflow-auto rounded bg-neutral-900 p-3 text-xs text-neutral-100">
            {diff.slice(0, MAX_DIFF_CHARS)}
            {diff.length > MAX_DIFF_CHARS ? "\n… diff recortado en el panel; completo en el PR" : ""}
          </pre>
        ) : (
          <p className="text-sm text-neutral-600">Sin diff subido por el cliente.</p>
        )}
      </section>

      {waiting ? (
        <section className="mb-6 grid gap-6" aria-label="Decisión">
          <form action={approveAction} className="grid gap-2 rounded border p-4">
            <input type="hidden" name="id" value={item.id} />
            <input type="hidden" name="expectedVersion" value={item.approval_version} />
            <h2 className="font-medium">Aprobar</h2>
            <button type="submit" className="justify-self-start rounded bg-green-700 px-4 py-2 text-white">
              Aprobar cambio
            </button>
          </form>
          <form action={requestChangesAction} className="grid gap-2 rounded border p-4">
            <input type="hidden" name="id" value={item.id} />
            <input type="hidden" name="expectedVersion" value={item.approval_version} />
            <h2 className="font-medium">Pedir cambios</h2>
            <label className="grid gap-1 text-sm">
              Motivo
              <textarea name="reason" required maxLength={2000} rows={3} className="rounded border px-3 py-2" />
            </label>
            <button type="submit" className="justify-self-start rounded border px-4 py-2">
              Pedir cambios
            </button>
          </form>
        </section>
      ) : null}

      {ready ? (
        <form action={mergeAction} className="mb-6 grid gap-2 rounded border p-4">
          <input type="hidden" name="id" value={item.id} />
          <input type="hidden" name="expectedVersion" value={item.approval_version} />
          <h2 className="font-medium">Mergear</h2>
          <p className="text-sm text-neutral-600">Se mergea el SHA {item.gate_sha?.slice(0, 12)} si el PR sigue igual.</p>
          <button type="submit" className="justify-self-start rounded bg-neutral-900 px-4 py-2 text-white">
            Mergear PR
          </button>
        </form>
      ) : null}

      <section className="grid gap-2" aria-label="Auditoría">
        <h2 className="font-medium">Auditoría</h2>
        <ol className="grid gap-1 text-xs text-neutral-700">
          {item.events.map((event) => (
            <li key={event.id}>
              {new Date(event.created_at).toLocaleString("es-ES")} · {event.kind} · {event.actor}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-neutral-600">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}
