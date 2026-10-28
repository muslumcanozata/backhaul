export const API = "http://localhost:8000";

function detailOf(body: unknown): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return "İstek tamamlanamadı";
  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object" && "msg" in detail[0]) {
    return String(detail[0].msg);
  }
  return "İstek tamamlanamadı";
}

export async function api<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(detailOf(await response.json().catch(() => null)));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function upload<T>(path: string, token: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API}${path}`, { method: "POST", body, headers });
  if (!response.ok) {
    throw new Error(detailOf(await response.json().catch(() => null)));
  }
  return response.json() as Promise<T>;
}

export async function download(path: string, token: string, filename: string): Promise<void> {
  const response = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!response.ok) {
    throw new Error(detailOf(await response.json().catch(() => null)));
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
