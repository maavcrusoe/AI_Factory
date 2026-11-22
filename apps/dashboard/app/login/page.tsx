export const instant = false;

import { loginAction } from "./actions";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const { error } = await searchParams;

  return (
    <main data-screen="login" className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 p-4">
      <h1 className="text-2xl font-semibold">Entrar a AI Factory</h1>
      <form action={loginAction} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input name="email" type="email" required autoComplete="username" className="rounded border px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Contraseña
          <input name="password" type="password" required autoComplete="current-password" className="rounded border px-3 py-2" />
        </label>
        {error ? (
          <p role="alert" className="text-sm text-red-600">
            Credenciales no válidas.
          </p>
        ) : null}
        <button type="submit" className="rounded bg-black px-3 py-2 text-white">
          Entrar
        </button>
      </form>
    </main>
  );
}
