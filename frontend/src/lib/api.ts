const API_BASE = typeof window === "undefined"
  ? (process.env.INTERNAL_API_URL || "http://api-gateway:8026")
  : "/api";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || error.error || `API error ${res.status}`);
  }
  return res.json();
}

// Client-side fetcher that goes through Next.js API routes
export async function clientFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || error.error || `API error ${res.status}`);
  }
  return res.json();
}

export const fetcher = (url: string) => fetch(url).then((r) => r.json());
