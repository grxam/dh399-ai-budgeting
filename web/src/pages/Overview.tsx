import { Link, useNavigate } from "react-router-dom";
import { Check, TrendingUp, TriangleAlert } from "lucide-react";
import { api, type Report } from "../api";
import { categoryMeta } from "../categories";
import { money, parseDate, todayIso } from "../format";
import { currentMonth, useApi, useMonth } from "../hooks";
import { Header } from "../components/Header";
import { ActivityRow, Empty, IconTile, LoadState, Progress, SectionHead } from "../components/ui";

function daysLeftInMonth(month: string): number | null {
  if (month !== currentMonth()) return null;
  const today = parseDate(todayIso());
  const last = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  return last.getDate() - today.getDate();
}

/** "On track" when spending keeps pace with how far through the month we are. */
function paceBadge(report: Report) {
  const { total_budget: budget, total_spent_on_budgeted: spent, month } = report;
  if (spent > budget) return { label: "Over budget", Icon: TriangleAlert, tone: "alert" };
  const left = daysLeftInMonth(month);
  if (left === null) return { label: "Under budget", Icon: Check, tone: "ok" };
  const today = parseDate(todayIso());
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  const elapsedPct = (today.getDate() / daysInMonth) * 100;
  const usedPct = (spent / budget) * 100;
  return usedPct <= elapsedPct + 5
    ? { label: "On track", Icon: Check, tone: "ok" }
    : { label: "Spending fast", Icon: TrendingUp, tone: "warn" };
}

export default function Overview() {
  const { month } = useMonth();
  const navigate = useNavigate();
  const report = useApi(() => api.report(month), [month]);
  const activity = useApi(() => api.activity({ month, limit: 3 }), [month]);
  const r = report.data;

  return (
    <main className="page">
      <Header title="Overview" />

      {!r ? (
        <LoadState loading={report.loading} error={report.error} onRetry={report.reload} />
      ) : r.total_budget === 0 ? (
        <section className="hero">
          <p className="hero-label">Left to spend</p>
          <p className="hero-sub">Set a monthly budget for a few categories and we'll keep track of what's left.</p>
          <Link to="/budgets" className="hero-button">
            Set up budgets
          </Link>
        </section>
      ) : (
        <HeroCard report={r} />
      )}

      {r && r.budgets.length > 0 && (
        <>
          <SectionHead title="Your budgets" action={<Link to="/budgets" className="link">View all</Link>} />
          <div className="budget-cards">
            {r.budgets.map((b) => {
              const meta = categoryMeta(b.category);
              return (
                <button key={b.category} className={`budget-card tint-${meta.tint}`} onClick={() => navigate("/budgets")}>
                  <span className="budget-card-name">
                    <meta.Icon size={22} strokeWidth={1.6} />
                    {meta.label}
                  </span>
                  <span className={`budget-card-amount ${money(b.spent).length > 5 ? "long" : ""}`}>
                    {money(b.spent)} <small>/ {money(b.monthly_limit)}</small>
                  </span>
                  <Progress value={b.pct_used} />
                  <span className={`budget-card-left ${b.state === "over" ? "alert-text" : ""}`}>
                    {b.remaining >= 0 ? `${money(b.remaining)} left` : `${money(-b.remaining)} over`}
                  </span>
                </button>
              );
            })}
          </div>
        </>
      )}

      <SectionHead title="Recent activity" action={<Link to="/activity" className="link">See all</Link>} />
      {activity.data ? (
        activity.data.items.length ? (
          <div className="activity-list">
            {activity.data.items.map((item) => (
              <ActivityRow key={`${item.source}-${item.id}`} item={item} onClick={() => navigate("/activity")} />
            ))}
          </div>
        ) : (
          <Empty
            title="Nothing here yet"
            body="Scan a receipt or add an expense or income by hand."
            action={<Link to="/receipt" className="link">Add something</Link>}
          />
        )
      ) : (
        <LoadState loading={activity.loading} error={activity.error} onRetry={activity.reload} />
      )}
      {r && Object.keys(r.unbudgeted).length > 0 && (
        <p className="footnote">
          <IconTile category="other" />
          {money(Object.values(r.unbudgeted).reduce((a, b) => a + b, 0))} spent in categories without a budget.
        </p>
      )}
    </main>
  );
}

function HeroCard({ report }: { report: Report }) {
  const { total_budget: budget, total_spent_on_budgeted: spent, month } = report;
  const left = budget - spent;
  const badge = paceBadge(report);
  const daysLeft = daysLeftInMonth(month);
  return (
    <section className="hero">
      <div className="hero-top">
        <p className="hero-label">{left >= 0 ? "Left to spend" : "Over budget by"}</p>
        <span className={`badge badge-${badge.tone}`}>
          <badge.Icon size={14} strokeWidth={2} />
          {badge.label}
        </span>
      </div>
      <p className="hero-amount">{money(Math.abs(left), true)}</p>
      <p className="hero-sub">of your {money(budget)} monthly budget</p>
      <Progress value={(spent / budget) * 100} variant="hero" />
      <div className="hero-stats">
        <div>
          <strong>{money(spent)}</strong>
          <span>spent this month</span>
        </div>
        <div className="right">
          {daysLeft === null ? (
            <>
              <strong>Closed</strong>
              <span>this month has ended</span>
            </>
          ) : (
            <>
              <strong>
                {daysLeft} {daysLeft === 1 ? "day" : "days"}
              </strong>
              <span>until a fresh start</span>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
