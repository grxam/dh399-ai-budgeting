// Typed wrappers around the FastAPI backend. In development Vite proxies
// /api to the backend (see vite.config.ts).

export type BudgetState = "ok" | "warning" | "over";

export interface BudgetStatus {
  category: string;
  monthly_limit: number;
  spent: number;
  remaining: number;
  pct_used: number;
  state: BudgetState;
}

export interface GoalStatus {
  id: number;
  name: string;
  description: string | null;
  icon: string | null;
  target_amount: number;
  saved_amount: number;
  remaining: number;
  pct_complete: number;
  target_date: string | null;
  months_left: number | null;
  monthly_needed: number | null;
  state: "on_track" | "done" | "overdue";
}

export interface Report {
  month: string;
  budgets: BudgetStatus[];
  unbudgeted: Record<string, number>;
  goals: GoalStatus[];
  total_budget: number;
  total_spent_on_budgeted: number;
}

export interface ActivityItem {
  source: "receipt" | "manual";
  id: number;
  kind: "expense" | "income";
  title: string | null;
  category: string;
  amount: number;
  date: string | null;
}

export interface Insights {
  month: string;
  period: { start: string; end: string };
  spent: number;
  previous: { start: string; end: string; spent: number };
  change_pct: number | null;
  difference: number;
  daily: { date: string; amount: number }[];
  last_7_days_total: number;
  by_category: { category: string; amount: number }[];
}

export type Notification =
  | { id: string; kind: "budget_over" | "budget_warning"; category: string; spent: number; limit: number; pct_used: number }
  | { id: string; kind: "goal_done" | "goal_overdue"; goal_id: number; name: string; saved: number; target: number };

export interface LineItem {
  description: string;
  quantity: number;
  unit_price: number | null;
  total_price: number;
  category: string;
}

export interface ReceiptData {
  merchant: string;
  purchase_date: string | null;
  currency: string;
  subtotal: number | null;
  tax: number | null;
  total: number;
  category: string;
  items: LineItem[];
  confidence: number;
}

export interface ExtractResult {
  receipt: ReceiptData;
  warnings: string[];
  needs_review: boolean;
}

export interface NewGoal {
  name: string;
  target_amount: number;
  saved_amount?: number;
  target_date?: string | null;
  description?: string | null;
  icon?: string | null;
}

export interface NewTransaction {
  kind: "expense" | "income";
  amount: number;
  category?: string;
  description?: string | null;
  txn_date?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new Error("Can't reach the server. Is the API running?");
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail) && body.detail[0]?.msg) message = body.detail[0].msg;
    } catch {
      // body wasn't JSON; keep the generic message
    }
    throw new Error(message);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

const monthQuery = (month?: string) => (month ? `month=${month}` : "");

export const api = {
  report: (month?: string) => request<Report>(`/report?${monthQuery(month)}`),
  insights: (month?: string) => request<Insights>(`/insights?${monthQuery(month)}`),
  notifications: (month?: string) => request<Notification[]>(`/notifications?${monthQuery(month)}`),
  activity: (opts: { month?: string; limit?: number; offset?: number } = {}) =>
    request<{ items: ActivityItem[] }>(
      `/activity?limit=${opts.limit ?? 20}&offset=${opts.offset ?? 0}&${monthQuery(opts.month)}`,
    ),

  setBudget: (category: string, monthly_limit: number) =>
    request<void>(`/budgets/${category}`, json("PUT", { monthly_limit })),
  deleteBudget: (category: string) => request<void>(`/budgets/${category}`, { method: "DELETE" }),

  addGoal: (goal: NewGoal) => request<{ id: number }>("/goals", json("POST", goal)),
  contribute: (id: number, amount: number) =>
    request<void>(`/goals/${id}/contribute`, json("POST", { amount })),
  deleteGoal: (id: number) => request<void>(`/goals/${id}`, { method: "DELETE" }),

  extractReceipt: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<ExtractResult>("/receipts/extract", { method: "POST", body: form });
  },
  saveReceipt: (receipt: ReceiptData) => request<{ id: number }>("/receipts", json("POST", receipt)),
  deleteReceipt: (id: number) => request<void>(`/receipts/${id}`, { method: "DELETE" }),

  addTransaction: (txn: NewTransaction) => request<{ id: number }>("/transactions", json("POST", txn)),
  deleteTransaction: (id: number) => request<void>(`/transactions/${id}`, { method: "DELETE" }),

  advice: (question: string, brief = false) =>
    request<{ answer: string; disclaimer: string }>("/advice", json("POST", { question, brief })),
};
