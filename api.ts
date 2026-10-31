async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers, credentials: "include" });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = data?.detail;
    const message = typeof detail === "string" ? detail : res.statusText;
    throw new Error(message || "Request failed");
  }
  return data as T;
}

export const api = {
  status: () => request<{ twilio_configured: boolean; openai_configured: boolean; angel_one_configured: boolean; sms_setup_hint: string | null }>("/api/auth/status"),
  me: () => request<{ id: number; email: string | null; phone: string | null; name: string; has_profile: boolean }>("/api/auth/me"),
  register: (body: object) => request("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: object) => request("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  otpStart: (phone: string) => request("/api/auth/otp/start", { method: "POST", body: JSON.stringify({ phone }) }),
  otpVerify: (body: object) => request("/api/auth/otp/verify", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  profile: () => request<{ profile: Record<string, unknown> | null; what_is_saved: string }>("/api/profile"),
  saveProfile: (body: object) => request("/api/profile", { method: "PUT", body: JSON.stringify(body) }),
  overview: () => request<Record<string, unknown>>("/api/overview"),
  budget: () => request<{ monthly_income: number; categories: { id: number; name: string; planned_amount: number }[]; planned_spending: number; remaining_income: number; note: string }>("/api/budget"),
  addCategory: (body: object) => request("/api/budget/categories", { method: "POST", body: JSON.stringify(body) }),
  patchCategory: (id: number, body: object) => request(`/api/budget/categories/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteCategory: (id: number) => request(`/api/budget/categories/${id}`, { method: "DELETE" }),
  sip: () => request<Record<string, unknown>>("/api/sip"),
  saveSip: (body: object) => request("/api/sip", { method: "PUT", body: JSON.stringify(body) }),
  assets: (refresh = false) => request<Record<string, unknown>>(`/api/assets${refresh ? "?refresh=true" : ""}`),
  coach: (question: string) => request<{ answer: string; source: string; used_fallback: boolean; detected_language: string; disclaimer: string }>("/api/coach/ask", { method: "POST", body: JSON.stringify({ question }) }),
};

export function inr(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(n);
}

export function usd(n: number | null | undefined): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(n);
}
