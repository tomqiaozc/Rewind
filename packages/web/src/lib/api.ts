/**
 * API client for the Rewind backend.
 *
 * During development without auth, calls go directly to the Python backend.
 * In production, calls go through Next.js API route proxies (BFF pattern).
 */
import type {
  DashboardStats,
  FilterValues,
  SearchResponse,
  SessionDetail,
  SessionListResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, body);
  }

  return res.json() as Promise<T>;
}

// ── Sessions ──────────────────────────────────────────────────────────

export async function listSessions(params?: {
  page?: number;
  page_size?: number;
  source?: string;
  project?: string;
  model?: string;
  is_starred?: boolean;
  sort_by?: string;
  sort_order?: string;
}): Promise<SessionListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") {
        searchParams.set(key, String(value));
      }
    }
  }
  const qs = searchParams.toString();
  return apiFetch<SessionListResponse>(
    `/api/sessions${qs ? `?${qs}` : ""}`,
  );
}

export async function getSession(id: string): Promise<SessionDetail> {
  return apiFetch<SessionDetail>(`/api/sessions/${id}`);
}

export async function getSessionFilters(): Promise<FilterValues> {
  return apiFetch<FilterValues>("/api/sessions/filters");
}

// ── Search ────────────────────────────────────────────────────────────

export async function searchSessions(params: {
  q: string;
  source?: string;
  limit?: number;
  offset?: number;
}): Promise<SearchResponse> {
  const searchParams = new URLSearchParams({ q: params.q });
  if (params.source) searchParams.set("source", params.source);
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.offset) searchParams.set("offset", String(params.offset));
  return apiFetch<SearchResponse>(`/api/search?${searchParams.toString()}`);
}

// ── Stats ─────────────────────────────────────────────────────────────

export async function getDashboardStats(
  days?: number,
): Promise<DashboardStats> {
  const qs = days ? `?days=${days}` : "";
  return apiFetch<DashboardStats>(`/api/stats${qs}`);
}

export { ApiError };
