import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpRight, MessageCircle, RefreshCw, Sparkles } from "lucide-react";
import { api, type Insights as InsightsData } from "../api";
import { categoryMeta } from "../categories";
import { money, monthName, parseDate, shortRange } from "../format";
import { useApi, useMonth } from "../hooks";
import { Header } from "../components/Header";
import { Empty, LoadState, SectionHead } from "../components/ui";

// Shades for "Where it went", darkest for the biggest category.
const SHADES = ["#55623f", "#97a77c", "#b9c79f", "#cbbcaa", "#dcded3"];

export default function Insights() {
  const { month } = useMonth();
  const insights = useApi(() => api.insights(month), [month]);
  const d = insights.data;

  return (
    <main className="page">
      <Header title="Insights" />
      {!d ? (
        <LoadState loading={insights.loading} error={insights.error} onRetry={insights.reload} />
      ) : (
        <>
          <SpendCard data={d} />
          <SectionHead title="Where it went" />
          {d.by_category.length === 0 ? (
            <Empty title="No spending yet" body={`Nothing recorded for ${monthName(month)} so far.`} />
          ) : (
            <WhereItWent data={d} />
          )}
          <TipCard data={d} />
        </>
      )}
    </main>
  );
}

function SpendCard({ data }: { data: InsightsData }) {
  const max = Math.max(...data.daily.map((d) => d.amount), 1);
  const down = data.change_pct !== null && data.change_pct <= 0;
  return (
    <section className="hero">
      <div className="hero-top">
        <p className="hero-label">Spent this month</p>
        <span className="hero-faint">{shortRange(data.period.start, data.period.end)}</span>
      </div>
      <div className="hero-top align-end">
        <p className="hero-amount small">{money(data.spent)}</p>
        {data.change_pct !== null && (
          <span className={`hero-change ${down ? "" : "up"}`}>
            {down ? <ArrowDown size={18} /> : <ArrowUp size={18} />}
            {Math.abs(Math.round(data.change_pct))}%
          </span>
        )}
      </div>
      <p className="hero-sub">
        {data.previous.spent > 0
          ? `vs. ${shortRange(data.previous.start, data.previous.end)}`
          : "Nothing recorded last month to compare with"}
      </p>

      <div className="bars" role="img" aria-label={`Spending over the last 7 days, ${money(data.last_7_days_total)} total`}>
        {data.daily.map((day, i) => (
          <div key={day.date} className="bar-col">
            <div
              className={`bar ${i === data.daily.length - 1 ? "bar-today" : ""}`}
              style={{ height: `${Math.max(8, (day.amount / max) * 100)}%` }}
              title={`${day.date}: ${money(day.amount, true)}`}
            />
            <span>{parseDate(day.date).getDate()}</span>
          </div>
        ))}
      </div>
      <div className="hero-top">
        <span className="hero-faint">Last 7 days</span>
        <span className="hero-accent">{money(data.last_7_days_total)} total</span>
      </div>
    </section>
  );
}

function WhereItWent({ data }: { data: InsightsData }) {
  const top = data.by_category.slice(0, 4);
  const rest = data.by_category.slice(4).reduce((sum, c) => sum + c.amount, 0);
  const rows = [
    ...top.map((c) => ({ label: categoryMeta(c.category).label, amount: c.amount })),
    ...(rest > 0 ? [{ label: "Other spending", amount: rest }] : []),
  ];
  const total = rows.reduce((sum, r) => sum + r.amount, 0) || 1;
  return (
    <>
      <div className="stacked" aria-hidden>
        {rows.map((r, i) => (
          <span key={r.label} style={{ width: `${(r.amount / total) * 100}%`, background: SHADES[i] }} />
        ))}
      </div>
      <ul className="legend">
        {rows.map((r, i) => (
          <li key={r.label}>
            <span className="legend-dot" style={{ background: SHADES[i] }} />
            <span>{r.label}</span>
            <strong>{money(r.amount)}</strong>
          </li>
        ))}
      </ul>
    </>
  );
}

const TIP_PREFIX = "stashflow.tip.";

// One request per month at a time: the local model is slow, and React's dev
// mode mounts components twice.
const pendingTips = new Map<string, Promise<string>>();

function requestTip(month: string, fresh: boolean): Promise<string> {
  const pending = pendingTips.get(month);
  if (pending && !fresh) return pending;
  const promise = api
    .advice(
      `Give me one practical tip for the rest of ${monthName(month)} based on my spending and budgets.`,
      true,
    )
    .then(({ answer }) => {
      const clean = cleanAnswer(answer);
      sessionStorage.setItem(TIP_PREFIX + month, clean);
      return clean;
    })
    .finally(() => pendingTips.delete(month));
  pendingTips.set(month, promise);
  return promise;
}

/** Strip reasoning text some local models wrap in <think> tags. */
function cleanAnswer(text: string): string {
  return text.replace(/<think>[\s\S]*?<\/think>/gi, "").trim();
}

function TipCard({ data }: { data: InsightsData }) {
  const { month } = data;
  const [tip, setTip] = useState<string | null>(() => sessionStorage.getItem(TIP_PREFIX + month));
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  const ahead = data.difference >= 0;
  const title = data.previous.spent === 0 ? "Your first look" : ahead ? "A little more breathing room" : "Running a little ahead";
  const fallback =
    data.previous.spent === 0
      ? "Keep adding receipts and next month we'll show how you're pacing."
      : ahead
        ? `You're ${money(data.difference)} below last month's pace. Small choices are adding up.`
        : `You're ${money(-data.difference)} above last month's pace. A few quiet days would even it out.`;

  const fetchTip = (fresh: boolean) => {
    let live = true;
    setLoading(true);
    setFailed(false);
    requestTip(month, fresh)
      .then((text) => live && setTip(text))
      .catch(() => live && setFailed(true))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  };

  useEffect(() => {
    const cached = sessionStorage.getItem(TIP_PREFIX + month);
    setTip(cached);
    if (!cached && data.spent > 0) return fetchTip(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [month]);

  return (
    <section className="tip-card">
      <h3>{title}</h3>
      <p>{fallback}</p>
      {tip && (
        <p className="tip-ai">
          <Sparkles size={16} /> {tip}
        </p>
      )}
      {loading && <p className="muted small">Thinking of a tip…</p>}
      {failed && <p className="muted small">Couldn't reach the AI for a tip right now.</p>}
      <div className="tip-actions">
        <Link to="/budgets" className="link">
          Keep it going <ArrowUpRight size={16} />
        </Link>
        <Link to="/ask" className="link">
          <MessageCircle size={16} /> Ask a question
        </Link>
        {data.spent > 0 && (
          <button className="link-button muted" onClick={() => fetchTip(true)} disabled={loading}>
            <RefreshCw size={14} /> New tip
          </button>
        )}
      </div>
      {tip && <p className="disclaimer">AI suggestion · general budgeting help, not financial advice</p>}
    </section>
  );
}
