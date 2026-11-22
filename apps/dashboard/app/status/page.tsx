import Link from "next/link";
export const instant = false;

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

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
    <main data-screen="status" className="mx-auto w-full max-w-2xl gap-6 p-4 sm:p-8">
      <h1 className="mb-6 text-2xl font-semibold">Estado del hub</h1>
      <Link href="/inbox" className="mb-4 inline-block text-sm underline">
        Ir a la bandeja
      </Link>
      <ul className="grid gap-3">
        <StatusRow label="API" ok={apiOk} detail={apiOk ? "Respondiendo" : `No disponible en ${API_URL}`} />
        <StatusRow label="Base de datos" ok={dbOk} detail={dbOk ? "Conectada" : "Sin conexión"} />
        <StatusRow label="Usuario" ok detail={`${me.email} (${me.role})`} />
      </ul>
    </main>
  );
}

function StatusRow({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return (
    <li className="flex items-center justify-between rounded border p-4">
      <span className="font-medium">{label}</span>
      <span className={ok ? "text-green-700" : "text-red-600"}>
        {ok ? "OK" : "Error"} · {detail}
      </span>
    </li>
  );
}
