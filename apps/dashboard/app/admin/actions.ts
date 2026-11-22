"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

const DIFFICULTIES = ["low", "medium", "high"];
const MEANINGS = ["none", "minor", "major", "dubious"];
const ROLES = ["admin", "developer", "reviewer", "viewer"];

/** Llamada autenticada a la API. Sin sesión o con 401, manda a login. */
async function callApi(path: string, method: "POST" | "PATCH" | "PUT", body: unknown): Promise<Response> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (response.status === 401) redirect("/login");
  return response;
}

/** Código de error para la URL. La API da el motivo en `detail`; aquí solo importa la categoría. */
function errorCode(status: number): string {
  if (status === 403) return "forbidden";
  if (status === 409) return "conflict";
  if (status === 422) return "invalid";
  return "failed";
}

export async function createUserAction(formData: FormData): Promise<void> {
  const role = String(formData.get("role") ?? "");
  const response = await callApi("/api/v1/users", "POST", {
    email: String(formData.get("email") ?? "").trim(),
    password: String(formData.get("password") ?? ""),
    role: ROLES.includes(role) ? role : "developer",
  });
  if (!response.ok) redirect(`/admin/users?error=${errorCode(response.status)}`);
  redirect("/admin/users?saved=created");
}

export async function updateUserAction(formData: FormData): Promise<void> {
  const id = String(formData.get("id") ?? "");
  if (!/^\d+$/.test(id)) redirect("/admin/users");
  const role = String(formData.get("role") ?? "");
  const response = await callApi(`/api/v1/users/${id}`, "PATCH", {
    role: ROLES.includes(role) ? role : undefined,
    is_active: formData.get("is_active") === "on",
  });
  if (!response.ok) redirect(`/admin/users?error=${errorCode(response.status)}`);
  redirect("/admin/users?saved=updated");
}

export async function savePolicyAction(formData: FormData): Promise<void> {
  const slug = String(formData.get("project") ?? "");
  const body = {
    require_human_always: formData.get("require_human_always") === "on",
    human_if_difficulty: formData.getAll("human_if_difficulty").map(String).filter((v) => DIFFICULTIES.includes(v)),
    sensitive_paths: String(formData.get("sensitive_paths") ?? "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean),
    human_if_unplanned: formData.get("human_if_unplanned") === "on",
    human_if_meaning: formData.getAll("human_if_meaning").map(String).filter((v) => MEANINGS.includes(v)),
  };
  const response = await callApi(`/api/v1/projects/${encodeURIComponent(slug)}/merge-policy`, "PUT", body);
  const target = `/admin/policies?project=${encodeURIComponent(slug)}`;
  if (!response.ok) redirect(`${target}&error=${errorCode(response.status)}`);
  redirect(`${target}&saved=1`);
}
