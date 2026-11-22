import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { StatusBadge } from "@/components/status-badge";
import { apiFetch, type WorkItem } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";

export const instant = false;

export default async function ApprovalsPage() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  const response = await apiFetch("/api/v1/approvals", token).catch(() => null);
  if (!response || response.status === 401) redirect("/login");
  const items = (await response.json()) as WorkItem[];

  return (
    <main data-screen="approvals" className="mx-auto w-full max-w-3xl gap-6 p-4 sm:p-8">
      <Link href="/inbox" className="text-sm underline">
        ← Bandeja
      </Link>
      <h1 className="mt-4 mb-6 text-2xl font-semibold">Aprobaciones</h1>
      {items.length === 0 ? (
        <p className="text-neutral-600">Nada pendiente de aprobación.</p>
      ) : (
        <ul data-testid="approvals" className="grid gap-3">
          {items.map((item) => (
            <li key={item.id}>
              <Link href={`/approvals/${item.id}`} className="grid gap-2 rounded border p-4 hover:bg-neutral-50">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium">
                    #{item.id} {item.title}
                  </span>
                  <StatusBadge status={item.status} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
