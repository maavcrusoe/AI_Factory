"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

export async function loginAction(formData: FormData): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: String(formData.get("email") ?? ""),
      password: String(formData.get("password") ?? ""),
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    redirect("/login?error=1");
  }

  const { access_token } = (await response.json()) as { access_token: string };
  const store = await cookies();
  store.set(SESSION_COOKIE, access_token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
  });
  redirect("/status");
}
