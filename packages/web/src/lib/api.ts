/**
 * API client for the Rewind backend.
 *
 * In development with NEXT_PUBLIC_API_URL set, calls go directly to the
 * Python backend using the API key for authentication.
 *
 * In production (or dev without NEXT_PUBLIC_API_URL), calls go through
 * Next.js BFF proxy routes which attach NextAuth session headers.
 */
import type {
  BatchRequest,
  BatchResponse,
  DashboardStats,
  FilterValues,
  ProjectActivity,
  ProjectSummary,
  SearchResponse,
  SessionDetail,
  SessionListResponse,
  Tag,
} from "./types";

// Dev direct mode: NEXT_PUBLIC_API_URL + NEXT_PUBLIC_API_KEY bypass BFF
// Production / BFF mode: relative paths hit Next.js API routes
const DIRECT_URL = process.env.NEXT_PUBLIC_API_URL;
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

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
  // If NEXT_PUBLIC_API_URL is set, call backend directly (dev convenience)
  // Otherwise use relative path to hit Next.js BFF proxy routes
  const url = DIRECT_URL ? `${DIRECT_URL}${path}` : path;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };

  // Only attach API key in direct mode
  if (DIRECT_URL && API_KEY) {
    headers["Authorization"] = `Bearer ${API_KEY}`;
  }

  const res = await fetch(url, {
    ...init,
    headers,
  });

  if (res.status === 401 && !DIRECT_URL && typeof window !== "undefined") {
    window.location.href = "/login";
    return undefined as unknown as T;
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, body);
  }

  // 204 No Content — return undefined (caller uses Promise<void>)
  if (res.status === 204) {
    return undefined as unknown as T;
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

// ── Tags ──────────────────────────────────────────────────────────────

export async function listTags(): Promise<Tag[]> {
  return apiFetch<Tag[]>("/api/tags");
}

export async function createTag(body: { name: string; color: string }): Promise<Tag> {
  return apiFetch<Tag>("/api/tags", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateTag(
  id: string,
  body: { name?: string; color?: string },
): Promise<Tag> {
  return apiFetch<Tag>(`/api/tags/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteTag(id: string): Promise<void> {
  return apiFetch<void>(`/api/tags/${id}`, { method: "DELETE" });
}

export async function addTagToSession(
  sessionId: string,
  tagId: string,
): Promise<void> {
  return apiFetch<void>(`/api/sessions/${sessionId}/tags/${tagId}`, {
    method: "PUT",
  });
}

export async function removeTagFromSession(
  sessionId: string,
  tagId: string,
): Promise<void> {
  return apiFetch<void>(`/api/sessions/${sessionId}/tags/${tagId}`, {
    method: "DELETE",
  });
}

// ── Star ──────────────────────────────────────────────────────────────

export async function toggleStar(
  id: string,
  isStarred: boolean,
): Promise<{ is_starred: boolean }> {
  return apiFetch<{ is_starred: boolean }>(`/api/sessions/${id}/star`, {
    method: "PATCH",
    body: JSON.stringify({ is_starred: isStarred }),
  });
}

// ── Trash ─────────────────────────────────────────────────────────────

export async function trashSession(id: string): Promise<void> {
  return apiFetch<void>(`/api/sessions/${id}/trash`, { method: "POST" });
}

export async function restoreSession(id: string): Promise<void> {
  return apiFetch<void>(`/api/sessions/${id}/trash`, { method: "DELETE" });
}

export async function listTrash(params?: {
  page?: number;
  page_size?: number;
}): Promise<SessionListResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return apiFetch<SessionListResponse>(
    `/api/sessions/trash${qs ? `?${qs}` : ""}`,
  );
}

// ── Batch ─────────────────────────────────────────────────────────────

export async function batchOperation(
  body: BatchRequest,
): Promise<BatchResponse> {
  return apiFetch<BatchResponse>("/api/sessions/batch", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Projects ──────────────────────────────────────────────────────────

export async function listProjects(): Promise<ProjectSummary[]> {
  return apiFetch<ProjectSummary[]>("/api/projects");
}

export async function getProjectActivity(
  days?: number,
): Promise<ProjectActivity[]> {
  const qs = days ? `?days=${days}` : "";
  return apiFetch<ProjectActivity[]>(`/api/projects/activity${qs}`);
}
