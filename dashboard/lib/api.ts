export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiFail extends Error {
  type: string;
  retryAfter?: number | null;
  constructor(type: string, message: string, retryAfter?: number | null) {
    super(message);
    this.type = type;
    this.retryAfter = retryAfter;
  }
}

export async function api<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), init?.timeoutMs ?? 20000);
  try {
    const r = await fetch(API + path, {
      ...init,
      signal: ctl.signal,
      headers: { "content-type": "application/json", ...(init?.headers || {}) },
    });
    const j = await r.json().catch(() => null);
    if (!r.ok) {
      const e = j?.error || { type: "http", message: j?.detail ? String(j.detail) : `Request failed (${r.status})` };
      throw new ApiFail(e.type, e.message, e.retry_after);
    }
    return j as T;
  } catch (e: any) {
    if (e instanceof ApiFail) throw e;
    if (e?.name === "AbortError") throw new ApiFail("timeout", "The server took too long to answer. Please try again.");
    throw new ApiFail("network", "Cannot reach the FlameIntel API. Is it running on " + API + "?");
  } finally {
    clearTimeout(t);
  }
}
