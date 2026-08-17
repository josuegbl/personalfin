import type { Account, Transaction, Category, DashboardData, UploadResult, ForecastData, ForecastPlanUpdate } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const BASE = `${API_BASE_URL}/api/v1`;

async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v));
    });
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function uploadFile<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  // Sin Content-Type: el browser lo pone con el boundary correcto
  const res = await fetch(BASE + path, { method: "POST", body: form });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  dashboard: {
    get: () => get<DashboardData>("/dashboard"),
  },
  accounts: {
    list: () => get<Account[]>("/accounts"),
    get: (id: number) => get<Account>(`/accounts/${id}`),
    sync: (id: number) => post(`/sync/${id}`),
    syncAll: () => post("/sync/"),
    upload: (id: number, file: File) => uploadFile<UploadResult>(`/sync/${id}/upload`, file),
  },
  transactions: {
    list: (params?: {
      account_id?: number;
      categoria_id?: number;
      fecha_desde?: string;
      fecha_hasta?: string;
      comercio?: string;
      recurrente?: boolean;
      page?: number;
      page_size?: number;
    }) => get<Transaction[]>("/transactions", params as Record<string, string | number | boolean | undefined>),
    update: (id: number, body: Partial<Pick<Transaction, "categoria_id" | "comercio" | "recurrente" | "notas">>) =>
      patch<Transaction>(`/transactions/${id}`, body),
  },
  categories: {
    list: () => get<Category[]>("/categories"),
  },
  forecast: {
    get: (year: number, month: number) => get<ForecastData>(`/forecast/${year}/${month}`),
    save: (year: number, month: number, body: ForecastPlanUpdate) =>
      put<ForecastData>(`/forecast/${year}/${month}`, body),
  },
};
