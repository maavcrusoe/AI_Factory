import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import { LiveRefresh } from "@/components/live-refresh";
import { StatusBadge } from "@/components/status-badge";
import { apiFetch, DECIDABLE, type WorkArtifact, type WorkItemDetail } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";
import { decideAction } from "./actions";

export const instant = false;

export default async function WorkPage({
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
  const stages = item.events.filter((e) => ["stage", "pr_opened", "tracker_linked"].includes(e.kind));
  const { error } = await searchParams;

  return (
    <main className="mx-auto w-full max-w-3xl gap-6 p-4 sm:p-8">
      <LiveRefresh />
      <Link href="/inbox" className="text-sm underline">
        ← Bandeja
      </Link>
      <header className="mt-4 mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">
          #{item.id} {item.title}
        </h1>
        <StatusBadge status={item.status} />
      </header>

      {item.reason ? <p className="mb-6 rounded bg-amber-50 p-3 text-sm">{item.reason}</p> : null}

      {item.owner ? (
        <section className="mb-6 grid gap-4" aria-label="Trabajo asignado">
          <h2 className="font-medium">Trabajo</h2>
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <Field label="Dueño" value={item.owner} />
            <Field label="Cogido" value={formatDate(item.claimed_at)} />
            <Field label="Último latido" value={formatDate(item.last_heartbeat_at)} />
            <Field label="Estado" value={item.heartbeat_state ?? "—"} />
          </dl>
          {item.heartbeat_message ? <p className="text-sm">{item.heartbeat_message}</p> : null}
        </section>
      ) : null}

      <section className="mb-6 grid gap-4">
        <h2 className="font-medium">Valoración del intake</h2>
        <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <Field label="Decisión" value={item.decision ?? "—"} />
          <Field label="Confianza" value={item.confidence !== null ? `${Math.round(item.confidence * 100)}%` : "—"} />
          <Field label="Tipo" value={item.work_type ?? "—"} />
          <Field label="Dificultad" value={item.difficulty ?? "—"} />
          <Field label="Riesgo" value={item.risk ?? "—"} />
          <Field label="Origen" value={item.source} />
        </dl>
        {item.summary ? (
          <p>
            <span className="font-medium">Resumen: </span>
            {item.summary}
          </p>
        ) : null}
        {item.valuation ? (
          <p>
            <span className="font-medium">Valoración: </span>
            {item.valuation}
          </p>
        ) : null}
        {item.labels.length > 0 ? (
          <p className="flex flex-wrap gap-2 text-xs">
            {item.labels.map((label) => (
              <span key={label} className="rounded bg-neutral-100 px-1.5 py-0.5">
                {label}
              </span>
            ))}
          </p>
        ) : null}
      </section>

      <section className="mb-6 grid gap-4">
        <h2 className="font-medium">Texto original</h2>
        <pre className="whitespace-pre-wrap rounded border p-3 text-sm">{item.body}</pre>
        {item.expanded_body ? (
          <>
            <h2 className="font-medium">Texto ampliado por el modelo</h2>
            <pre className="whitespace-pre-wrap rounded border border-dashed p-3 text-sm">{item.expanded_body}</pre>
          </>
        ) : null}
      </section>

      {DECIDABLE.has(item.status) ? (
        <form action={decideAction} className="mb-8 grid gap-3 rounded border p-4" data-testid="decision">
          <h2 className="font-medium">Decisión</h2>
          {error ? <p className="text-sm text-red-600">No se pudo aplicar la decisión.</p> : null}
          <input type="hidden" name="id" value={item.id} />
          <label className="grid gap-1 text-sm">
            Motivo (opcional)
            <input name="reason" maxLength={1000} className="rounded border px-3 py-2" />
          </label>
          <label className="grid gap-1 text-sm">
            Etiqueta si aceptas (opcional, por defecto factory:human)
            <input name="label" maxLength={40} className="rounded border px-3 py-2" />
          </label>
          <div className="flex flex-wrap gap-2">
            <button name="action" value="accept" className="rounded bg-green-700 px-4 py-2 text-white">
              Aceptar
            </button>
            <button name="action" value="request_info" className="rounded bg-sky-700 px-4 py-2 text-white">
              Pedir información
            </button>
            <button name="action" value="reject" className="rounded bg-red-700 px-4 py-2 text-white">
              Rechazar
            </button>
          </div>
        </form>
      ) : null}

      <section className="mb-6 grid gap-2" aria-label="Etapas del pipeline">
        <h2 className="font-medium">Etapas del pipeline</h2>
        <ol data-testid="stages" className="grid gap-1 text-sm">
          {stages.length === 0 ? <li className="text-neutral-500">Sin etapas todavía.</li> : null}
          {stages.map((event) => (
            <li key={event.id} className="flex flex-wrap gap-2 border-b py-1">
              <span className="font-mono text-xs">{String(event.detail?.stage ?? event.kind)}</span>
              <span>{String(event.detail?.message ?? event.detail?.pr_url ?? "")}</span>
              <span className="text-neutral-500">{formatDate(event.created_at)}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="mb-6 grid gap-2" aria-label="Logs y diffs">
        <h2 className="font-medium">Logs y diffs</h2>
        {artifacts.length === 0 ? <p className="text-sm text-neutral-500">Sin artefactos todavía.</p> : null}
        {artifacts.map((artifact) => (
          <details key={artifact.id} data-testid="artifact" className="rounded border p-2">
            <summary className="cursor-pointer text-sm">
              {artifact.kind} · {artifact.stage} · ronda {artifact.round}
            </summary>
            <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap rounded bg-neutral-50 p-2 text-xs">
              {artifact.content}
            </pre>
          </details>
        ))}
      </section>

      <section className="grid gap-2">
        <h2 className="font-medium">Auditoría</h2>
        <ol data-testid="events" className="grid gap-1 text-sm">
          {item.events.map((event) => (
            <li key={event.id} className="flex flex-wrap gap-2 border-b py-1">
              <span className="font-mono text-xs">{event.kind}</span>
              <span className="text-neutral-600">
                {event.from_status ?? "∅"} → {event.to_status ?? "—"}
              </span>
              <span className="text-neutral-500">por {event.actor}</span>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border p-2">
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString("es-ES") : "—";
}
