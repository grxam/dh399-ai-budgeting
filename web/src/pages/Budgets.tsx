import { useState } from "react";
import { Check, Plus, Trash2 } from "lucide-react";
import { api, type Report } from "../api";
import { EXPENSE_CATEGORIES, categoryMeta } from "../categories";
import { money, pct } from "../format";
import { useApi, useMonth } from "../hooks";
import { Header } from "../components/Header";
import { CategoryPicker, Empty, IconTile, LoadState, Progress, SectionHead, Sheet } from "../components/ui";

export default function Budgets() {
  const { month } = useMonth();
  const report = useApi(() => api.report(month), [month]);
  const [editing, setEditing] = useState(false);
  const [adding, setAdding] = useState<string | null>(null); // null = closed, "" = open with no preset
  const r = report.data;

  return (
    <main className="page">
      <Header title="Budgets" />
      {!r ? (
        <LoadState loading={report.loading} error={report.error} onRetry={report.reload} />
      ) : (
        <>
          <section className="hero hero-compact">
            <div className="hero-top">
              <p className="hero-label">Monthly budget</p>
              {r.total_budget > 0 && (
                <span className="hero-accent">{pct((r.total_spent_on_budgeted / r.total_budget) * 100)} used</span>
              )}
            </div>
            <div className="hero-top">
              <p className="hero-amount small">{money(r.total_budget)}</p>
              {r.total_budget > 0 && (
                <span className="hero-accent large">
                  {r.total_budget >= r.total_spent_on_budgeted
                    ? `${money(r.total_budget - r.total_spent_on_budgeted)} left`
                    : `${money(r.total_spent_on_budgeted - r.total_budget)} over`}
                </span>
              )}
            </div>
            <Progress value={r.total_budget ? (r.total_spent_on_budgeted / r.total_budget) * 100 : 0} variant="hero" />
          </section>

          <SectionHead
            title="Categories"
            action={
              r.budgets.length > 0 && (
                <button className="link-button" onClick={() => setEditing((e) => !e)}>
                  {editing ? "Done" : "Edit budgets"}
                </button>
              )
            }
          />

          {r.budgets.length === 0 ? (
            <Empty title="No budgets yet" body="Pick a category and set how much you want to spend on it each month." />
          ) : editing ? (
            <EditList report={r} onChanged={report.reload} />
          ) : (
            <ul className="category-list">
              {r.budgets.map((b) => {
                const meta = categoryMeta(b.category);
                return (
                  <li key={b.category} className="category-row">
                    <IconTile category={b.category} />
                    <div className="category-main">
                      <div className="category-top">
                        <span>{meta.label}</span>
                        <span className={`muted ${b.state === "over" ? "alert-text" : ""}`}>
                          {money(b.spent)} / {money(b.monthly_limit)}
                        </span>
                      </div>
                      <Progress value={b.pct_used} />
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {Object.keys(r.unbudgeted).length > 0 && (
            <>
              <h3 className="subhead">Spent without a budget</h3>
              <ul className="category-list">
                {Object.entries(r.unbudgeted).map(([category, amount]) => (
                  <li key={category} className="category-row">
                    <IconTile category={category} />
                    <div className="category-main">
                      <div className="category-top">
                        <span>{categoryMeta(category).label}</span>
                        <span className="muted">{money(amount)}</span>
                      </div>
                    </div>
                    <button className="link-button" onClick={() => setAdding(category)}>
                      Set budget
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          <p className="tagline">
            <Check size={18} /> A little planning. A lot more peace.
          </p>
          <button className="primary-button" onClick={() => setAdding("")}>
            <Plus size={20} /> Add a category
          </button>

          <AddBudgetSheet
            preset={adding}
            report={r}
            onClose={() => setAdding(null)}
            onSaved={() => {
              setAdding(null);
              report.reload();
            }}
          />
        </>
      )}
    </main>
  );
}

function EditList({ report, onChanged }: { report: Report; onChanged: () => void }) {
  const [limits, setLimits] = useState<Record<string, string>>(
    Object.fromEntries(report.budgets.map((b) => [b.category, String(b.monthly_limit)])),
  );
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState<string>();

  const save = async (category: string) => {
    const value = Number(limits[category]);
    if (!(value > 0)) return setError("Enter an amount above zero.");
    setError(undefined);
    setSaving(category);
    try {
      await api.setBudget(category, value);
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(undefined);
    }
  };

  const remove = async (category: string) => {
    if (!confirm(`Remove the ${categoryMeta(category).label} budget? Your spending stays recorded.`)) return;
    try {
      await api.deleteBudget(category);
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <>
      {error && <div className="notice notice-error">{error}</div>}
      <ul className="category-list">
        {report.budgets.map((b) => (
          <li key={b.category} className="category-row editing">
            <IconTile category={b.category} />
            <span className="category-name">{categoryMeta(b.category).label}</span>
            <label className="money-input small">
              <span>$</span>
              <input
                inputMode="decimal"
                value={limits[b.category]}
                aria-label={`${categoryMeta(b.category).label} monthly limit`}
                onChange={(e) => setLimits({ ...limits, [b.category]: e.target.value })}
                onBlur={() => Number(limits[b.category]) !== b.monthly_limit && save(b.category)}
                onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
                disabled={saving === b.category}
              />
            </label>
            <button className="icon-button small" onClick={() => remove(b.category)} aria-label={`Remove ${categoryMeta(b.category).label} budget`}>
              <Trash2 size={18} />
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}

function AddBudgetSheet({
  preset,
  report,
  onClose,
  onSaved,
}: {
  preset: string | null;
  report: Report;
  onClose: () => void;
  onSaved: () => void;
}) {
  const budgeted = new Set(report.budgets.map((b) => b.category));
  const options = EXPENSE_CATEGORIES.filter((c) => !budgeted.has(c));
  const [category, setCategory] = useState("");
  const [limit, setLimit] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const chosen = category || preset || options[0] || "";

  const close = () => {
    setCategory("");
    setLimit("");
    setError(undefined);
    onClose();
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = Number(limit);
    if (!(value > 0)) return setError("Enter a monthly amount above zero.");
    setBusy(true);
    try {
      await api.setBudget(chosen, value);
      setCategory("");
      setLimit("");
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet open={preset !== null} onClose={close} title="Add a category">
      {options.length === 0 ? (
        <p className="muted">Every category already has a budget. Use “Edit budgets” to change the amounts.</p>
      ) : (
        <form onSubmit={submit} className="form">
          <span className="field-label">Category</span>
          <CategoryPicker value={chosen} onChange={setCategory} options={options} />
          {report.unbudgeted[chosen] !== undefined && (
            <p className="muted small">You've spent {money(report.unbudgeted[chosen])} on this so far this month.</p>
          )}
          <label className="field">
            <span className="field-label">Monthly limit</span>
            <span className="money-input">
              <span>$</span>
              <input inputMode="decimal" placeholder="500" value={limit} onChange={(e) => setLimit(e.target.value)} autoFocus />
            </span>
          </label>
          {error && <p className="error-text">{error}</p>}
          <button className="primary-button" disabled={busy}>
            {busy ? "Saving…" : `Add ${categoryMeta(chosen).label}`}
          </button>
        </form>
      )}
    </Sheet>
  );
}
