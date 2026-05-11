/**
 * Thin client for the Xenia FastAPI backend.
 *
 * Talks via the Next.js rewrite at `/api/xenia/*` → `XENIA_API_URL/*`
 * (default `http://localhost:8080`). Both server and client components can call
 * these helpers; on the server the base URL needs to resolve, on the client the
 * rewrite handles it.
 */
const BROWSER_BASE = "/api/xenia";
const SERVER_BASE =
  process.env.XENIA_API_URL?.replace(/\/$/, "") ?? "http://localhost:8080";

function base(): string {
  return typeof window === "undefined" ? SERVER_BASE : BROWSER_BASE;
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;
  constructor(status: number, body: unknown, message?: string) {
    super(message ?? `xenia api error ${status}`);
    this.status = status;
    this.body = body;
  }
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${base()}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      body = await res.text().catch(() => null);
    }
    throw new ApiError(res.status, body);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------- Processes ----------

export type ProcessStatus = "active" | "paused" | "archived";
export type ProcessTargetKind = "agent" | "mission" | "worker";
export type ProcessLastStatus = "ok" | "partial" | "failed";

export interface Process {
  id: string;
  name: string;
  description: string;
  cron_expression: string;
  schedule_human: string;
  target_kind: ProcessTargetKind;
  target_ref: string;
  target_label: string;
  owner_name: string;
  owner_initials: string;
  status: ProcessStatus;
  last_run_at: string | null;
  last_run_status: ProcessLastStatus | null;
  last_run_id: string | null;
  next_run_at: string | null;
  success_rate_30d: number;
  runs_30d: number;
  created_at: string;
  updated_at: string;
}

export interface ProcessSummary {
  active: number;
  paused: number;
  next_within_1h: number;
}

export interface ProcessCreate {
  name: string;
  description?: string;
  cron_expression: string;
  schedule_human?: string;
  target_kind: ProcessTargetKind;
  target_ref: string;
  target_label?: string;
  payload?: Record<string, unknown>;
  owner_name: string;
  owner_initials?: string;
}

export const processesApi = {
  list: () => api<Process[]>("/v1/processes"),
  summary: () => api<ProcessSummary>("/v1/processes/summary"),
  create: (body: ProcessCreate) =>
    api<Process>("/v1/processes", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  setStatus: (id: string, action: "pause" | "resume") =>
    api<Process>(`/v1/processes/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ action }),
    }),
  runNow: (id: string) =>
    api<Process>(`/v1/processes/${id}/run`, { method: "POST" }),
};
