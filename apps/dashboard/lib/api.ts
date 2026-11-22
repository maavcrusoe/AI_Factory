import { API_URL } from "@/lib/config";

export type WorkItem = {
  id: number;
  source: string;
  title: string;
  status: string;
  decision: string | null;
  confidence: number | null;
  work_type: string | null;
  labels: string[];
  created_at: string;
  updated_at: string;
  // Fase 6: el tablero y la bandeja muestran proyecto, dueño y latido.
  project_slug?: string | null;
  owner?: string | null;
  last_heartbeat_at?: string | null;
  heartbeat_state?: string | null;
};

export type ProjectSummary = {
  slug: string;
  name: string;
  total: number;
  by_status: Record<string, number>;
};

export type Me = { id: number; email: string; role: string; is_active: boolean };

export type UserRow = Me;

export type PlatformSettings = { log_retention_days: number; heartbeat_timeout_seconds: number };

export type MergePolicy = {
  version: number;
  body: {
    require_human_always: boolean;
    human_if_difficulty: string[];
    sensitive_paths: string[];
    human_if_unplanned: boolean;
    human_if_meaning: string[];
  };
};

export type WorkEvent = {
  id: number;
  kind: string;
  from_status: string | null;
  to_status: string | null;
  actor: string;
  detail: Record<string, unknown> | null;
  created_at: string;
};

export type WorkItemDetail = WorkItem & {
  body: string;
  expanded_body: string | null;
  summary: string | null;
  valuation: string | null;
  difficulty: string | null;
  risk: string | null;
  reason: string | null;
  owner: string | null;
  claimed_at: string | null;
  last_heartbeat_at: string | null;
  heartbeat_state: string | null;
  heartbeat_message: string | null;
  pr_number: number | null;
  pr_url: string | null;
  gate_sha: string | null;
  gate_result: string | null;
  meaning_change: string | null;
  planned: boolean | null;
  touched_paths: string[] | null;
  review_findings: string[] | null;
  approval_version: number;
  policy_version: number | null;
  policy_reasons: string[] | null;
  events: WorkEvent[];
};

export type WorkArtifact = {
  id: number;
  stage: string;
  round: number;
  kind: string;
  client_key: string;
  content: string;
  created_at: string;
};

export const STATUS_LABEL: Record<string, string> = {
  RECEIVED: "Recibida",
  NORMALIZING: "Normalizando",
  TRIAGE: "En triage",
  QUEUED: "En cola",
  CLAIMED: "En curso",
  PR_OPEN: "PR en borrador",
  NEEDS_INFO: "Falta información",
  WAITING_HUMAN_TRIAGE: "Revisión humana",
  REJECTED: "Rechazada",
  FIXING: "Cambios pedidos",
  WAITING_HUMAN_MERGE: "Aprobación humana",
  READY_TO_MERGE: "Lista para mergear",
  MERGING: "Mergeando",
  MERGED: "Mergeada",
};

export const DECIDABLE = new Set(["WAITING_HUMAN_TRIAGE", "NEEDS_INFO"]);
export const APPROVAL_QUEUE = new Set(["WAITING_HUMAN_MERGE", "READY_TO_MERGE", "MERGING"]);

/** Columnas del tablero: cada estado cae en una sola columna. */
export const BOARD_COLUMNS: { title: string; statuses: string[] }[] = [
  { title: "Entrada", statuses: ["RECEIVED", "NORMALIZING", "TRIAGE", "WAITING_HUMAN_TRIAGE", "NEEDS_INFO"] },
  { title: "En cola", statuses: ["QUEUED"] },
  { title: "En curso", statuses: ["CLAIMED", "FIXING"] },
  { title: "PR en borrador", statuses: ["PR_OPEN"] },
  { title: "Aprobación", statuses: ["WAITING_HUMAN_MERGE", "READY_TO_MERGE", "MERGING"] },
  { title: "Cerrado", statuses: ["MERGED", "REJECTED"] },
];

export const SOURCES = ["form", "api", "app", "github", "azuredevops"];

export function apiFetch(path: string, token: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
}

/** JSON para páginas de servidor. Devuelve `null` si la sesión no vale (la página manda a login). */
export async function fetchJson<T>(path: string, token: string): Promise<T | null> {
  const response = await apiFetch(path, token).catch(() => null);
  if (!response || response.status === 401) return null;
  if (!response.ok) throw new Error(`${path} respondió ${response.status}`);
  return (await response.json()) as T;
}
