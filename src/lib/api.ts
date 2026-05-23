// =============================================================================
// src/lib/api.ts — Central API helper for all backend calls
//
// All requests go to the FastAPI backend at localhost:8000.
// JWT token is automatically attached from localStorage.
// =============================================================================

export const BACKEND_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const TOKEN_KEY = "agrigpt_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  if (typeof window !== "undefined") localStorage.removeItem(TOKEN_KEY);
}

/** Build headers with optional Authorization Bearer token */
function buildHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...extra,
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

/** Generic fetch wrapper — throws on non-2xx responses */
async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BACKEND_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      ...buildHeaders(),
      ...(options.headers as Record<string, string>),
    },
  });

  if (!res.ok) {
    let message = `Request failed: ${res.status}`;
    try {
      const data = await res.json();
      message = data?.detail ?? message;
    } catch {
      /* ignore parse errors */
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

// ── Auth endpoints ────────────────────────────────────────────────────────────

export interface UserOut {
  id: string;
  name: string;
  email: string;
  language: string;
  location: string;
  photo_url?: string;
  active_crop?: string;
  last_diagnosis?: string;
  last_diagnosis_severity?: string;
  next_irrigation?: string;
  mandi_price?: number;
  mandi_price_change?: number;
  mandi_location?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export const authApi = {
  /** Fetch the Google Client ID from backend (never hardcoded in frontend) */
  getConfig: () =>
    apiFetch<{ google_client_id: string }>("/auth/config"),

  signup: (body: { name: string; email: string; password: string; language?: string; location?: string }) =>
    apiFetch<TokenResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  signin: (body: { email: string; password: string }) =>
    apiFetch<TokenResponse>("/auth/signin", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  /** Send Google id_token to backend for server-side verification */
  googleAuth: (id_token: string, language?: string, location?: string) =>
    apiFetch<TokenResponse>("/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token, language, location }),
    }),

  me: () => apiFetch<TokenResponse>("/auth/me"),

  logout: () =>
    apiFetch<{ message: string }>("/auth/logout", { method: "POST" }),
};

// ── Dashboard endpoints ───────────────────────────────────────────────────────

export interface ActivityItem {
  agent: string;
  query: string;
  status: string;
  time: string;
}

export interface DashboardMetrics {
  active_crop: string;
  last_diagnosis: string;
  last_diagnosis_severity: string;
  next_irrigation: string;
  mandi_price?: number;
  mandi_price_change: number;
  mandi_location: string;
  location: string;
  name: string;
  recent_activity: ActivityItem[];
}

export const dashboardApi = {
  getMetrics: () => apiFetch<DashboardMetrics>("/dashboard/metrics"),

  updateMetrics: (body: Partial<Omit<DashboardMetrics, "recent_activity" | "name" | "location">>) =>
    apiFetch<{ message: string }>("/dashboard/metrics", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  logActivity: (body: { agent: string; query: string; status: string }) =>
    apiFetch<{ message: string }>("/dashboard/activity", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
