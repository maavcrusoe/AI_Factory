"use client";

import { useEffect, useState } from "react";

/** Un latido es "viejo" cuando supera la mitad del plazo de caducidad: aviso antes de que el claim caduque. */
export function isHeartbeatStale(lastHeartbeatAt: string | null | undefined, nowMs: number, timeoutSeconds: number): boolean {
  if (!lastHeartbeatAt) return false;
  return nowMs - new Date(lastHeartbeatAt).getTime() > (timeoutSeconds * 1000) / 2;
}

function ageLabel(lastHeartbeatAt: string, nowMs: number): string {
  const minutes = Math.max(0, Math.floor((nowMs - new Date(lastHeartbeatAt).getTime()) / 60_000));
  if (minutes < 1) return "latido hace <1 min";
  if (minutes < 60) return `latido hace ${minutes} min`;
  return `latido hace ${Math.floor(minutes / 60)} h ${minutes % 60} min`;
}

/**
 * Edad del último latido. Se re-evalúa cada 15 s en el navegador: un latido que se queda viejo
 * no genera evento SSE, así que el servidor no puede avisar del cambio.
 */
export function HeartbeatAge({
  lastHeartbeatAt,
  timeoutSeconds,
}: {
  lastHeartbeatAt: string | null | undefined;
  timeoutSeconds: number;
}) {
  const [nowMs, setNowMs] = useState<number | null>(null);

  useEffect(() => {
    const tick = () => setNowMs(Date.now());
    // Primera lectura en el siguiente tick: evita el hidratado con hora distinta en servidor y cliente.
    const first = setTimeout(tick, 0);
    const timer = setInterval(tick, 15_000);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, []);

  if (!lastHeartbeatAt || nowMs === null) return null;
  const stale = isHeartbeatStale(lastHeartbeatAt, nowMs, timeoutSeconds);
  return (
    <span
      data-testid="heartbeat"
      data-stale={stale ? "true" : "false"}
      className={stale ? "rounded bg-red-100 px-1.5 py-0.5 font-medium text-red-800" : "text-neutral-600"}
    >
      {stale ? "⚠ " : ""}
      {ageLabel(lastHeartbeatAt, nowMs)}
    </span>
  );
}
