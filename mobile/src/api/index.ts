// Эндпоинты «ЧекСкан» (docs/API.md).
import { api } from "./client";
import type {
  HomeStats, Receipt, ReceiptDetail, ReceiptListResponse,
  ScanResult, SummaryStats, User,
} from "./types";

export interface TokenResponse {
  token: string;
  user: User;
}

export const authApi = {
  register: (email: string, password: string, name?: string) =>
    api<TokenResponse>("/auth/register", { method: "POST", body: { email, password, name } }),
  login: (email: string, password: string) =>
    api<TokenResponse>("/auth/login", { method: "POST", body: { email, password } }),
  me: () => api<User>("/auth/me"),
};

export const receiptsApi = {
  scan: (form: FormData) =>
    api<ScanResult>("/receipts/scan", { method: "POST", form }),
  manual: (body: {
    shop_name: string; date: string; total_amount: number;
    category?: string; items?: { item_name: string; price: number }[];
  }) => api<ReceiptDetail>("/receipts/manual", { method: "POST", body }),
  confirm: (id: number, body: {
    shop_name: string; date: string; total_amount: number;
    category?: string; items?: { item_name: string; price: number }[];
  }) => api<ReceiptDetail>(`/receipts/${id}`, { method: "PATCH", body }),
  list: (page = 1, size = 50, status = "confirmed") =>
    api<ReceiptListResponse>(`/receipts?page=${page}&size=${size}&status=${status}`),
  detail: (id: number) => api<ReceiptDetail>(`/receipts/${id}`),
  remove: (id: number) => api<void>(`/receipts/${id}`, { method: "DELETE" }),
  summaryHome: () =>
    api<{ balance: number; month_spent: number; receipts: Receipt[] }>("/receipts/summary/home"),
};

export const statsApi = {
  home: () => api<HomeStats>("/stats/home"),
  summary: (period: "week" | "month" | "all") => api<SummaryStats>(`/stats/summary?period=${period}`),
};

export const usersApi = {
  patch: (body: Partial<Pick<User,
    "name" | "notifications_enabled" | "autosave_enabled" |
    "biometrics_enabled" | "theme_preference" | "monthly_budget">>) =>
    api<User>("/users/me", { method: "PATCH", body }),
};
