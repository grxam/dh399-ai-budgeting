import { useState } from "react";
import { Bell, ChevronDown } from "lucide-react";
import { api, type Notification } from "../api";
import { categoryMeta } from "../categories";
import { money, monthLabel, monthName } from "../format";
import { recentMonths, useApi, useMonth } from "../hooks";
import { Sheet } from "./ui";

const SEEN_KEY = "stashflow.seenNotifications";

function readSeen(): Set<string> {
  try {
    return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) ?? "[]"));
  } catch {
    return new Set();
  }
}

function describe(n: Notification): { title: string; body: string; tone: "alert" | "warn" | "good" } {
  switch (n.kind) {
    case "budget_over":
      return {
        title: `${categoryMeta(n.category).label} is over budget`,
        body: `${money(n.spent)} spent of ${money(n.limit)} this month.`,
        tone: "alert",
      };
    case "budget_warning":
      return {
        title: `${categoryMeta(n.category).label} is at ${Math.round(n.pct_used)}%`,
        body: `${money(n.limit - n.spent)} left of ${money(n.limit)}.`,
        tone: "warn",
      };
    case "goal_overdue":
      return {
        title: `${n.name} passed its target date`,
        body: `${money(n.saved)} saved of ${money(n.target)}. Pick a new date or keep going.`,
        tone: "warn",
      };
    case "goal_done":
      return { title: `${n.name} reached!`, body: `You saved ${money(n.target)}. Nicely done.`, tone: "good" };
  }
}

export function Header({ title, showMonth = true }: { title: string; showMonth?: boolean }) {
  const { month, setMonth } = useMonth();
  const [open, setOpen] = useState(false);
  const [seen, setSeen] = useState(readSeen);
  const { data: notes } = useApi(() => api.notifications(month), [month]);
  const unread = (notes ?? []).filter((n) => !seen.has(n.id)).length;

  const openNotes = () => {
    setOpen(true);
    if (notes?.length) {
      const next = new Set([...seen, ...notes.map((n) => n.id)]);
      localStorage.setItem(SEEN_KEY, JSON.stringify([...next]));
      setSeen(next);
    }
  };

  return (
    <header className="header">
      <div className="brand-row">
        <span className="brand">stashflow</span>
        <button className="icon-button" onClick={openNotes} aria-label={unread ? `Notifications, ${unread} new` : "Notifications"}>
          <Bell size={22} strokeWidth={1.6} />
          {unread > 0 && <span className="dot" />}
        </button>
      </div>
      <div className="title-row">
        <h1>{title}</h1>
        {showMonth && (
          <label className="month-picker">
            <span>{monthName(month)}</span>
            <ChevronDown size={16} />
            <select value={month} onChange={(e) => setMonth(e.target.value)} aria-label="Month">
              {recentMonths().map((m) => (
                <option key={m} value={m}>
                  {monthLabel(m)}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <Sheet open={open} onClose={() => setOpen(false)} title="Notifications">
        {!notes?.length ? (
          <p className="muted">You're all caught up. We'll let you know when a budget gets close or a goal is reached.</p>
        ) : (
          <ul className="note-list">
            {notes.map((n) => {
              const d = describe(n);
              return (
                <li key={n.id} className={`note note-${d.tone}`}>
                  <strong>{d.title}</strong>
                  <span>{d.body}</span>
                </li>
              );
            })}
          </ul>
        )}
      </Sheet>
    </header>
  );
}
