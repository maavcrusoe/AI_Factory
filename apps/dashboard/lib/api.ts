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
};

export const DECIDABLE = new Set(["WAITING_HUMAN_TRIAGE", "NEEDS_INFO"]);

export function apiFetch(path: string, token: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_URL}${path}`, {
    ...init,
    headers: { ...(init.headers ?? {}), Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
}
