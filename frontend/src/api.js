const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

let token = localStorage.getItem("cn_token") || null;

export function setToken(t) {
  token = t;
  if (t) localStorage.setItem("cn_token", t);
  else localStorage.removeItem("cn_token");
}

export function getToken() {
  return token;
}

async function req(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (res.status === 401) {
    setToken(null);
    throw new Error("Session expired. Please sign in again.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  health: () => req("/api/health"),
  signup: (email, password) =>
    req("/api/auth/signup", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email, password) =>
    req("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  getPreferences: () => req("/api/preferences"),
  savePreferences: (body) =>
    req("/api/preferences", { method: "PUT", body: JSON.stringify(body) }),
  listNews: ({ tab = "top", q = "", limit = 20, offset = 0 } = {}) => {
    const params = new URLSearchParams({ tab, limit, offset });
    if (q) params.set("q", q);
    return req(`/api/news?${params.toString()}`);
  },
  getNewsDetail: (id) => req(`/api/news/${id}`),
  analyze: (id) => req(`/api/news/${id}/analyze`, { method: "POST" }),
  usage: () => req("/api/usage"),
  refreshNews: () => req("/api/news/refresh", { method: "POST" }),
  backfill: () => req("/api/news/backfill", { method: "POST" }),
  signalClick: (id) => req(`/api/news/${id}/click`, { method: "POST" }),
  signalDown: (id) => req(`/api/news/${id}/feedback`, { method: "POST" }),
  exportAnalysis: async (id) => {
    const res = await fetch(`${BASE}/api/news/${id}/export`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `contextnews-${id}.md`;
    link.click();
    URL.revokeObjectURL(url);
  },
};
