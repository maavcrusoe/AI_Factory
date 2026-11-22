import { STATUS_LABEL } from "@/lib/api";

const TONE: Record<string, string> = {
  QUEUED: "bg-green-100 text-green-800",
  CLAIMED: "bg-sky-100 text-sky-900",
  PR_OPEN: "bg-violet-100 text-violet-900",
  WAITING_HUMAN_TRIAGE: "bg-amber-100 text-amber-900",
  NEEDS_INFO: "bg-sky-100 text-sky-900",
  REJECTED: "bg-red-100 text-red-800",
  WAITING_HUMAN_MERGE: "bg-amber-100 text-amber-900",
  READY_TO_MERGE: "bg-green-100 text-green-800",
  FIXING: "bg-red-100 text-red-800",
  MERGED: "bg-green-200 text-green-900",
};

export function StatusBadge({ status }: { status: string }) {
  const tone = TONE[status] ?? "bg-neutral-200 text-neutral-800";
  return (
    <span data-testid="status" data-status={status} className={`rounded px-2 py-0.5 text-xs font-medium ${tone}`}>
      {STATUS_LABEL[status] ?? status}
    </span>
  );
}
