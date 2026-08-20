/* API client. Aborts superseded requests, normalises errors, notices offline. */

const inFlight = new Map();

class ApiError extends Error {
  constructor(message, status, kind) {
    super(message);
    this.status = status;
    this.kind = kind;
  }
}

async function request(path, { key = path, signal } = {}) {
  if (inFlight.has(key)) inFlight.get(key).abort();
  const controller = new AbortController();
  inFlight.set(key, controller);

  if (signal) signal.addEventListener("abort", () => controller.abort(), { once: true });

  try {
    const response = await fetch(path, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      throw new ApiError("The server sent something unreadable", response.status, "decode");
    }
    if (!response.ok) {
      const detail = payload?.error || {};
      throw new ApiError(detail.message || "Request failed", response.status, detail.kind || "request");
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError") throw error;
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      navigator.onLine ? "Could not reach the server" : "You are offline",
      0,
      navigator.onLine ? "network" : "offline",
    );
  } finally {
    if (inFlight.get(key) === controller) inFlight.delete(key);
  }
}

export const api = {
  ApiError,
  report(query, { days } = {}) {
    const params = new URLSearchParams({ q: query });
    if (days) params.set("days", String(days));
    return request(`/api/v1/report?${params}`, { key: "report" });
  },
  search(query, limit = 8) {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    return request(`/api/v1/search?${params}`, { key: "search" });
  },
  compare(queries, { days } = {}) {
    const params = new URLSearchParams();
    queries.forEach((q) => params.append("q", q));
    if (days) params.set("days", String(days));
    return request(`/api/v1/compare?${params}`, { key: "compare" });
  },
  capabilities() {
    return request("/api/v1/capabilities", { key: "capabilities" });
  },
};
