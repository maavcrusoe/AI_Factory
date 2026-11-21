"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Se suscribe al stream SSE del hub y vuelve a pedir los datos del servidor en cada cambio. */
export function LiveRefresh() {
  const router = useRouter();

  useEffect(() => {
    const source = new EventSource("/api/inputs/stream");
    source.addEventListener("change", () => router.refresh());
    return () => source.close();
  }, [router]);

  return null;
}
