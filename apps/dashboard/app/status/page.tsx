import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

export const instant = false;

type Health = { status: string; database: string };
type Me = { id: number; email: string; role: string };

async function fetchHealth(): Promise<Health | null> {
  try {
    const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return (await response.json()) as Health;
  } catch {
    return null;
  }
}

export default async function StatusPage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  const meResponse = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  }).catch(() => null);
  if (!meResponse || meResponse.status === 401) redirect("/login");
  const me = (await meResponse.json()) as Me;
  const health = await fetchHealth();
  const apiOk = health?.status === "ok";
  const dbOk = health?.database === "ok";

  return (
    <main className="mx-auto w-full max-w-3xl">
      <h1 className="text-2xl font-bold tracking-tight">Estado del hub</h1>
      <p className="mb-6 text-sm text-slate-500">Salud de los servicios y tu sesión.</p>
      <ul className="grid gap-3 sm:grid-cols-3">
        <StatusCard label="API" ok={apiOk} detail={apiOk ? "Respondiendo" : `No disponible en ${API_URL}`} />
        <StatusCard label="Base de datos" ok={dbOk} detail={dbOk ? "Conectada" : "Sin conexión"} />
        <StatusCard label="Sesión" ok detail={`${me.email} (${me.role})`} />
      </ul>
    </main>
  );
}

function StatusCard({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <li className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-white/5">
      <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-500">
        <span className={`h-2.5 w-2.5 rounded-full ${ok ? "bg-emerald-500" : "bg-red-500"}`} />
        {label}
      </div>
      <p className={`break-words text-sm font-semibold ${ok ? "" : "text-red-600"}`}>{detail}</p>
    </li>
  );
}
