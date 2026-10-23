// HTTP-клиент: baseURL, Bearer-токен, единый разбор ошибок по контракту API.
import type { ApiErrorDetail } from "./types";

export const API_URL =
  process.env.EXPO_PUBLIC_API_URL ?? "http://10.0.2.2:8000";

let authToken: string | null = null;
export function setAuthToken(token: string | null) {
  authToken = token;
}

export class ApiError extends Error {
  constructor(public detail: ApiErrorDetail) {
    super(detail.message);
  }
  get code() {
    return this.detail.code;
  }
}

async function parseError(res: Response): Promise<ApiError> {
  try {
    const body = await res.json();
    const d = body?.detail;
    if (d && typeof d === "object") {
      return new ApiError({ code: d.code ?? "ERROR", message: d.message ?? "Ошибка", fields: d.fields });
    }
    return new ApiError({ code: "HTTP_" + res.status, message: `Ошибка сервера (${res.status})` });
  } catch {
    return new ApiError({ code: "NETWORK", message: "Нет соединения с сервером" });
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  form?: FormData;
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (authToken) headers.Authorization = `Bearer ${authToken}`;
  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form; // fetch сам выставит multipart boundary
  } else if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  const res = await fetch(`${API_URL}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body,
  });
  if (!res.ok) throw await parseError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
