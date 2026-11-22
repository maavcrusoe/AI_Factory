import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LiveRefresh } from "@/components/live-refresh";
import { StatusBadge } from "@/components/status-badge";
import { apiFetch, type WorkItem } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";
import { createInputAction } from "./actions";

export const instant = false;

export default async function InboxPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const response = await apiFetch("/api/v1/inputs", token).catch(() => null);
  if (!response || response.status === 401) redirect("/login");
  const items = (await response.json()) as WorkItem[];
  const { error } = await searchParams;
  const idempotencyKey = crypto.randomUUID();

  return (
    <main data-screen="inbox" className="mx-auto w-full max-w-3xl gap-6 p-4 sm:p-8">
      <LiveRefresh />
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Bandeja</h1>
        <nav className="flex gap-4 text-sm">
          <Link href="/approvals" className="underline">
            Aprobaciones
          </Link>
          <Link href="/status" className="underline">
            Estado del hub
          </Link>
        </nav>
      </header>

      <form action={createInputAction} className="mb-8 grid gap-3 rounded border p-4">
        <h2 className="font-medium">Nueva petición</h2>
        <input type="hidden" name="idempotencyKey" value={idempotencyKey} />
        <input type="hidden" name="projectId" value="meme-demo" />
        <label className="grid gap-1 text-sm">
          Título
          <input name="title" required maxLength={200} className="rounded border px-3 py-2" />
        </label>
        <label className="grid gap-1 text-sm">
          Descripción
          <textarea name="body" required maxLength={20000} rows={4} className="rounded border px-3 py-2" />
        </label>
        <button type="submit" className="justify-self-start rounded bg-neutral-900 px-4 py-2 text-white">
          Enviar al hub
        </button>
        {error ? <p className="text-sm text-red-600">No se pudo crear la petición.</p> : null}
      </form>

      {items.length === 0 ? (
        <p className="text-neutral-600">Sin peticiones todavía.</p>
      ) : (
        <ul data-testid="inbox" className="grid gap-3">
          {items.map((item) => (
            <li key={item.id}>
              <Link href={`/work/${item.id}`} className="grid gap-2 rounded border p-4 hover:bg-neutral-50">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">{item.title}</span>
                  <StatusBadge status={item.status} />
                </div>
                <div className="flex flex-wrap gap-2 text-xs text-neutral-600">
                  <span>#{item.id}</span>
                  <span>origen: {item.source}</span>
                  {item.work_type ? <span>tipo: {item.work_type}</span> : null}
                  {item.confidence !== null ? <span>confianza: {Math.round(item.confidence * 100)}%</span> : null}
                  {item.labels.map((label) => (
                    <span key={label} className="rounded bg-neutral-100 px-1.5">
                      {label}
                    </span>
                  ))}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
