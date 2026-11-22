import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LiveRefresh } from "@/components/live-refresh";
import { SiteNav } from "@/components/site-nav";
import { fetchJson, type Me, type UserRow } from "@/lib/api";
import { SESSION_COOKIE } from "@/lib/config";
import { createUserAction, updateUserAction } from "../actions";

export const instant = false;

const ROLE_OPTIONS = [
  { value: "developer", label: "Desarrollador" },
  { value: "reviewer", label: "Revisor" },
  { value: "viewer", label: "Solo lectura" },
  { value: "admin", label: "Admin" },
];

const ERRORS: Record<string, string> = {
  conflict: "Ese email ya existe.",
  invalid: "Datos no válidos. Revisa el email (mínimo 3 caracteres) y la contraseña (mínimo 8).",
  forbidden: "Tu rol no permite esta acción.",
  failed: "No se pudo completar la acción.",
};

/** Admin: usuarios, roles y activación. Solo admins; la API lo exige igualmente. */
export default async function AdminUsersPage({
  searchParams,
}: {
  searchParams: Promise<{ saved?: string; error?: string }>;
}) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  const me = await fetchJson<Me>("/api/v1/auth/me", token);
  if (!me) redirect("/login");
  if (me.role !== "admin") redirect("/board");
  const users = (await fetchJson<UserRow[]>("/api/v1/users", token)) ?? [];
  const { saved, error } = await searchParams;

  return (
    <main className="mx-auto w-full max-w-4xl gap-6 p-4 sm:p-8">
      <LiveRefresh />
      <h1 className="mb-4 text-2xl font-semibold">Usuarios y roles</h1>
      <SiteNav isAdmin />

      {saved ? (
        <p role="status" className="mb-4 rounded bg-green-50 p-3 text-sm text-green-900">
          {saved === "created" ? "Usuario creado." : "Cambios guardados."}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mb-4 rounded bg-red-50 p-3 text-sm text-red-800">
          {ERRORS[error] ?? ERRORS.failed}
        </p>
      ) : null}

      <form action={createUserAction} className="mb-8 grid gap-3 rounded border p-4 sm:grid-cols-2" aria-label="Nuevo usuario">
        <h2 className="font-medium sm:col-span-2">Nuevo usuario</h2>
        <label className="grid gap-1 text-sm">
          Email
          <input name="email" type="email" required maxLength={320} className="rounded border px-3 py-2" />
        </label>
        <label className="grid gap-1 text-sm">
          Contraseña inicial (mín. 8)
          <input name="password" type="password" required minLength={8} maxLength={200} className="rounded border px-3 py-2" />
        </label>
        <label className="grid gap-1 text-sm">
          Rol
          <select name="role" defaultValue="developer" className="rounded border px-2 py-2">
            {ROLE_OPTIONS.map((role) => (
              <option key={role.value} value={role.value}>
                {role.label}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="self-end justify-self-start rounded bg-neutral-900 px-4 py-2 text-white">
          Crear usuario
        </button>
      </form>

      <div className="overflow-x-auto">
        <table data-testid="users" className="w-full min-w-[32rem] text-left text-sm">
          <thead className="border-b text-xs text-neutral-500">
            <tr>
              <th className="py-2 pr-3 font-medium">Email</th>
              <th className="py-2 pr-3 font-medium">Rol</th>
              <th className="py-2 pr-3 font-medium">Activo</th>
              <th className="py-2 font-medium">
                <span className="sr-only">Acciones</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b align-middle">
                <td className="py-2 pr-3">
                  {user.email}
                  {user.id === me.id ? <span className="ml-2 text-xs text-neutral-500">(tú)</span> : null}
                </td>
                <td colSpan={3} className="py-2">
                  <form action={updateUserAction} className="flex flex-wrap items-center gap-3">
                    <input type="hidden" name="id" value={user.id} />
                    <label className="flex items-center gap-1">
                      <span className="sr-only">Rol de {user.email}</span>
                      <select name="role" defaultValue={user.role} className="rounded border px-2 py-1">
                        {ROLE_OPTIONS.map((role) => (
                          <option key={role.value} value={role.value}>
                            {role.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="flex items-center gap-1">
                      <input type="checkbox" name="is_active" defaultChecked={user.is_active} />
                      Activo
                    </label>
                    <button type="submit" className="rounded border px-3 py-1 hover:bg-neutral-100">
                      Guardar
                    </button>
                  </form>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
