// Типы 1:1 по контракту docs/API.md (FastAPI-схемы).
export interface User {
  id: number;
  name: string;
  email: string;
  notifications_enabled: boolean;
  autosave_enabled: boolean;
  biometrics_enabled: boolean;
  theme_preference: "light" | "dark";
  monthly_budget: number;
}

export interface ReceiptItem {
  id?: number;
  item_name: string;
  price: number;
}

export interface Receipt {
  id: number;
  shop_name: string;
  date: string; // ISO
  total_amount: number;
  currency: string;
  category: string;
  status: string;
}

export interface ReceiptDetail extends Receipt {
  items: ReceiptItem[];
  ocr_confidence?: number | null;
}

export interface ScanResult {
  receipt: ReceiptDetail;
  low_confidence_fields: string[]; // поля для подсветки на экране корректировки
}

export interface ReceiptListResponse {
  total: number;
  page: number;
  size: number;
  items: Receipt[];
}

export interface StatsEntry {
  label: string;
  amount: number;
}

export interface HomeStats {
  today_spent: number;
  month_spent: number;
  month_limit: number;
  limit_used_pct: number;
  receipts_today: number;
  avg_receipt_today: number;
  categories_today: number;
  by_category_today: StatsEntry[];
}

export interface SummaryStats {
  period: "week" | "month" | "all";
  total: number;
  count: number;
  avg: number;
  max: number;
  by_day: StatsEntry[];
  by_category: StatsEntry[];
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  fields?: string[];
}
