import { useState } from "react";
import { Car, Gift, GraduationCap, Heart, House, Laptop, PiggyBank, Plane, Plus, ShieldCheck, Sparkle, Sun, type LucideIcon } from "lucide-react";
import { api, type GoalStatus } from "../api";
import type { Tint } from "../categories";
import { money, parseDate, pct } from "../format";
import { useApi } from "../hooks";
import { Header } from "../components/Header";
import { Empty, LoadState, Progress, SectionHead, Sheet } from "../components/ui";

export const GOAL_ICONS: Record<string, LucideIcon> = {
  shield: ShieldCheck,
  sun: Sun,
  laptop: Laptop,
  home: House,
  car: Car,
  plane: Plane,
  gift: Gift,
  piggy: PiggyBank,
  study: GraduationCap,
  heart: Heart,
};
const TINTS: Tint[] = ["green", "beige", "grey"];

export default function Goals() {
  const goals = useApi(() => api.report().then((r) => r.goals), []);
  const [selected, setSelected] = useState<GoalStatus | null>(null);
  const [creating, setCreating] = useState(false);
  const list = goals.data;

  const saved = list?.reduce((s, g) => s + g.saved_amount, 0) ?? 0;
  const target = list?.reduce((s, g) => s + g.target_amount, 0) ?? 0;
  const inProgress = list?.filter((g) => g.state !== "done").length ?? 0;

  return (
    <main className="page">
      <Header title="Goals" />
      {!list ? (
        <LoadState loading={goals.loading} error={goals.error} onRetry={goals.reload} />
      ) : (
        <>
          <section className="hero hero-compact">
            <div className="hero-top">
              <p className="hero-label">A little closer, every day</p>
              <Sparkle size={22} className="hero-accent" />
            </div>
            <p className="hero-amount small">
              {money(saved)} <span className="hero-inline">saved so far</span>
            </p>
            <Progress value={target ? (saved / target) * 100 : 0} variant="hero" />
            <div className="hero-top">
              <span className="hero-faint">
                {list.length ? `of ${money(target)} across ${list.length} ${list.length === 1 ? "goal" : "goals"}` : "No goals yet"}
              </span>
              {target > 0 && <span className="hero-accent">{pct((saved / target) * 100)}</span>}
            </div>
          </section>

          <SectionHead title="Your goals" action={list.length > 0 && <span className="muted">{inProgress} in progress</span>} />
          {list.length === 0 ? (
            <Empty title="Nothing saved for yet" body="A goal gives your savings somewhere to go. Start with something small." />
          ) : (
            <div className="goal-list">
              {list.map((g, i) => {
                const Icon = GOAL_ICONS[g.icon ?? ""] ?? PiggyBank;
                return (
                  <button key={g.id} className={`goal-card tint-${TINTS[i % 3]}`} onClick={() => setSelected(g)}>
                    <div className="goal-top">
                      <span className="icon-tile tint-white">
                        <Icon size={22} strokeWidth={1.6} />
                      </span>
                      <span className="goal-name">
                        <strong>{g.name}</strong>
                        {g.description && <span>{g.description}</span>}
                      </span>
                      <span className={`goal-pct ${g.state === "overdue" ? "alert-text" : ""}`}>
                        {g.state === "done" ? "Done" : pct(g.pct_complete)}
                      </span>
                    </div>
                    <Progress value={g.pct_complete} />
                    <div className="goal-bottom">
                      <strong>{money(g.saved_amount)} saved</strong>
                      <span>of {money(g.target_amount)}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          <p className="tagline-block">
            <strong>Make room for what matters.</strong>
            <span>Big plans start with small, steady steps.</span>
          </p>
          <button className="primary-button" onClick={() => setCreating(true)}>
            <Plus size={20} /> Create a new goal
          </button>

          <GoalSheet
            goal={selected}
            onClose={() => setSelected(null)}
            onChanged={() => {
              setSelected(null);
              goals.reload();
            }}
          />
          <CreateGoalSheet
            open={creating}
            onClose={() => setCreating(false)}
            onCreated={() => {
              setCreating(false);
              goals.reload();
            }}
          />
        </>
      )}
    </main>
  );
}

function GoalSheet({ goal, onClose, onChanged }: { goal: GoalStatus | null; onClose: () => void; onChanged: () => void }) {
  const [amount, setAmount] = useState("");
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const close = () => {
    setAmount("");
    setError(undefined);
    onClose();
  };

  if (!goal) return null;

  const add = async (value: number) => {
    if (!(value > 0)) return setError("Enter an amount above zero.");
    setBusy(true);
    try {
      await api.contribute(goal.id, value);
      setAmount("");
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!confirm(`Delete “${goal.name}”? This can't be undone.`)) return;
    try {
      await api.deleteGoal(goal.id);
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Sheet open onClose={close} title={goal.name}>
      <p className="muted">
        {money(goal.saved_amount)} saved of {money(goal.target_amount)}
        {goal.remaining > 0 && ` · ${money(goal.remaining)} to go`}
      </p>
      {goal.target_date && (
        <p className={`small ${goal.state === "overdue" ? "alert-text" : "muted"}`}>
          {goal.state === "overdue" ? "Target date passed: " : "Target: "}
          {parseDate(goal.target_date).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
          {goal.monthly_needed && goal.state !== "overdue" ? ` · about ${money(goal.monthly_needed)} a month` : ""}
        </p>
      )}
      {goal.state !== "done" && (
        <form
          className="form"
          onSubmit={(e) => {
            e.preventDefault();
            add(Number(amount));
          }}
        >
          <span className="field-label">Add money</span>
          <div className="chip-row">
            {[25, 50, 100].map((v) => (
              <button key={v} type="button" className="chip" disabled={busy} onClick={() => add(v)}>
                +{money(v)}
              </button>
            ))}
          </div>
          <span className="money-input">
            <span>$</span>
            <input inputMode="decimal" placeholder="Other amount" value={amount} onChange={(e) => setAmount(e.target.value)} aria-label="Amount to add" />
          </span>
          {error && <p className="error-text">{error}</p>}
          <button className="primary-button" disabled={busy || !amount}>
            {busy ? "Saving…" : "Add to goal"}
          </button>
        </form>
      )}
      <button className="danger-link" onClick={remove}>
        Delete goal
      </button>
    </Sheet>
  );
}

function CreateGoalSheet({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: () => void }) {
  const blank = { name: "", description: "", target: "", saved: "", date: "", icon: "piggy" };
  const [form, setForm] = useState(blank);
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const set = (key: keyof typeof blank) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  const close = () => {
    setForm(blank);
    setError(undefined);
    onClose();
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const target = Number(form.target);
    const saved = form.saved ? Number(form.saved) : 0;
    if (!form.name.trim()) return setError("Give your goal a name.");
    if (!(target > 0)) return setError("Enter a target above zero.");
    if (!(saved >= 0)) return setError("Already saved can't be negative.");
    setBusy(true);
    try {
      await api.addGoal({
        name: form.name.trim(),
        description: form.description.trim() || null,
        target_amount: target,
        saved_amount: saved,
        target_date: form.date || null,
        icon: form.icon,
      });
      setForm(blank);
      onCreated();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Sheet open={open} onClose={close} title="Create a new goal">
      <form className="form" onSubmit={submit}>
        <span className="field-label">Icon</span>
        <div className="icon-picker" role="radiogroup" aria-label="Icon">
          {Object.entries(GOAL_ICONS).map(([key, Icon]) => (
            <button
              key={key}
              type="button"
              role="radio"
              aria-checked={form.icon === key}
              aria-label={key}
              className={`icon-choice ${form.icon === key ? "chip-on" : ""}`}
              onClick={() => setForm({ ...form, icon: key })}
            >
              <Icon size={20} strokeWidth={1.6} />
            </button>
          ))}
        </div>
        <label className="field">
          <span className="field-label">Name</span>
          <input className="text-input" placeholder="Emergency fund" value={form.name} onChange={set("name")} maxLength={60} />
        </label>
        <label className="field">
          <span className="field-label">Short description (optional)</span>
          <input className="text-input" placeholder="Build your safety net" value={form.description} onChange={set("description")} maxLength={120} />
        </label>
        <div className="field-pair">
          <label className="field">
            <span className="field-label">Target</span>
            <span className="money-input">
              <span>$</span>
              <input inputMode="decimal" placeholder="6000" value={form.target} onChange={set("target")} />
            </span>
          </label>
          <label className="field">
            <span className="field-label">Already saved</span>
            <span className="money-input">
              <span>$</span>
              <input inputMode="decimal" placeholder="0" value={form.saved} onChange={set("saved")} />
            </span>
          </label>
        </div>
        <label className="field">
          <span className="field-label">Target date (optional)</span>
          <input className="text-input" type="date" value={form.date} onChange={set("date")} />
        </label>
        {error && <p className="error-text">{error}</p>}
        <button className="primary-button" disabled={busy}>
          {busy ? "Creating…" : "Create goal"}
        </button>
      </form>
    </Sheet>
  );
}
