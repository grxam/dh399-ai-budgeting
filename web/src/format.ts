const whole = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const cents = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

/** $1,450 for whole amounts, $64.80 otherwise. Pass exact=true to always show cents. */
export function money(value: number, exact = false): string {
  return exact || !Number.isInteger(Math.round(value * 100) / 100) ? cents.format(value) : whole.format(value);
}

export function pct(value: number): string {
  return `${Math.round(value)}%`;
}

/** Parse YYYY-MM-DD as a local date (new Date("2026-11-18") would be UTC). */
export function parseDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function isoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function todayIso(): string {
  return isoDate(new Date());
}

/** "Today", "Yesterday", or "Nov 12". */
export function relativeDay(iso: string | null): string {
  if (!iso) return "No date";
  const day = parseDate(iso);
  const today = parseDate(todayIso());
  const diff = Math.round((today.getTime() - day.getTime()) / 86_400_000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return day.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

/** "Nov 1–18" for a range inside one month. */
export function shortRange(start: string, end: string): string {
  const s = parseDate(start);
  const e = parseDate(end);
  const month = s.toLocaleDateString("en-US", { month: "short" });
  if (s.getMonth() === e.getMonth()) return `${month} ${s.getDate()}–${e.getDate()}`;
  return `${month} ${s.getDate()} – ${e.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}

export function monthName(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-US", { month: "long" });
}

export function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-US", { month: "long", year: "numeric" });
}
