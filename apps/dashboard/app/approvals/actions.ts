"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

type Decision = "approve" | "request-changes" | "merge";

// Un 409 significa versión vieja o estado distinto: el revisor debe recargar y decidir otra vez.
function errorCode(status: number): string {
  if (status === 409) return "stale";
  if (status === 403) return "forbidden";
  return "failed";
}

async function decide(id: string, action: Decision, body: Record<string, unknown>): Promise<void> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  if (!/^\d+$/.test(id)) redirect("/approvals");

  const response = await fetch(`${API_URL}/api/v1/work/${id}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (response.status === 401) redirect("/login");
  if (!response.ok) redirect(`/approvals/${id}?error=${errorCode(response.status)}`);
  redirect(`/approvals/${id}`);
}

function expectedVersion(formData: FormData): number {
  const value = Number(formData.get("expectedVersion"));
  return Number.isInteger(value) && value >= 0 ? value : -1;
}

export async function approveAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  await decide(id, "approve", { expected_version: expectedVersion(formData) });
}

export async function requestChangesAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  const reason = String(formData.get("reason") ?? "").trim();
  await decide(id, "request-changes", { expected_version: expectedVersion(formData), reason: reason || "Sin motivo" });
}

export async function mergeAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  await decide(id, "merge", { expected_version: expectedVersion(formData) });
}
