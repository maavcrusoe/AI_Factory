"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

export async function decideAction(formData: FormData): Promise<void> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const id = String(formData.get("id") ?? "");
  if (!/^\d+$/.test(id)) redirect("/inbox");

  const reason = String(formData.get("reason") ?? "").trim();
  const label = String(formData.get("label") ?? "").trim();
  const response = await fetch(`${API_URL}/api/v1/inputs/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      action: String(formData.get("action") ?? ""),
      reason: reason || null,
      label: label || null,
    }),
    cache: "no-store",
  });

  if (!response.ok) redirect(`/work/${id}?error=1`);
  redirect(`/work/${id}`);
}
