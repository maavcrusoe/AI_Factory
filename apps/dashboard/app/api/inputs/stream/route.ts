import { cookies } from "next/headers";
import { API_URL, SESSION_COOKIE } from "@/lib/config";

/** Proxy del SSE del hub: el navegador no ve el token, va en cookie httpOnly. */
export async function GET(request: Request): Promise<Response> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return new Response("No autenticado", { status: 401 });

  const upstream = await fetch(`${API_URL}/api/v1/inputs/stream`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
    signal: request.signal,
  });
  if (!upstream.ok || !upstream.body) return new Response("Stream no disponible", { status: 502 });

  return new Response(upstream.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache, no-transform" },
  });
}
