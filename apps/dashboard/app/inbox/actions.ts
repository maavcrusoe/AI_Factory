"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

export async function createInputAction(formData: FormData): Promise<void> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");

  const idempotencyKey = String(formData.get("idempotencyKey") ?? "") || crypto.randomUUID();
  const response = await fetch(`${API_URL}/api/v1/inputs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "X-Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({
      projectId: String(formData.get("projectId") ?? "meme-demo"),
      title: String(formData.get("title") ?? ""),
      body: String(formData.get("body") ?? ""),
      source: "form",
    }),
    cache: "no-store",
  });

  if (!response.ok) redirect("/inbox?error=1");
  const item = (await response.json()) as { id: number };
  redirect(`/work/${item.id}`);
}
