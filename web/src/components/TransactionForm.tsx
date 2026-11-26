import { useState } from "react";
import type { NewTransaction } from "../api";
import { EXPENSE_CATEGORIES } from "../categories";
import { todayIso } from "../format";
import { CategoryPicker } from "./ui";

export interface TransactionInitial {
  kind?: "expense" | "income";
  amount?: number;
  description?: string | null;
  category?: string;
  date?: string | null;
}

/** Form for a manual expense or income, used both to add one and to edit one. */
export function TransactionForm({
  initial = {},
  submitLabel,
  autoFocus = false,
  onSubmit,
}: {
  initial?: TransactionInitial;
  submitLabel: (kind: "expense" | "income") => string;
  autoFocus?: boolean;
  onSubmit: (txn: NewTransaction) => Promise<void>;
}) {
  const [kind, setKind] = useState<"expense" | "income">(initial.kind ?? "expense");
  const [amount, setAmount] = useState(initial.amount !== undefined ? String(initial.amount) : "");
  const [description, setDescription] = useState(initial.description ?? "");
  const [category, setCategory] = useState(
    initial.category && initial.category !== "income" ? initial.category : "groceries",
  );
  const [date, setDate] = useState(initial.date || todayIso());
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = Number(amount);
    if (!(value > 0)) return setError("Enter an amount above zero.");
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit({
        kind,
        amount: value,
        category: kind === "expense" ? category : undefined,
        description: description.trim() || null,
        txn_date: date,
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="form manual" onSubmit={submit}>
      <div className="kind-toggle" role="radiogroup" aria-label="Type">
        {(["expense", "income"] as const).map((k) => (
          <button key={k} type="button" role="radio" aria-checked={kind === k} className={kind === k ? "on" : ""} onClick={() => setKind(k)}>
            {k === "expense" ? "Expense" : "Income"}
          </button>
        ))}
      </div>
      <label className="amount-field">
        <span>{kind === "income" ? "+" : "−"}$</span>
        <input inputMode="decimal" placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} aria-label="Amount" autoFocus={autoFocus} />
      </label>
      <label className="field">
        <span className="field-label">What was it?</span>
        <input
          className="text-input"
          placeholder={kind === "income" ? "Payday" : "Coffee break"}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          maxLength={200}
        />
      </label>
      {kind === "expense" && (
        <>
          <span className="field-label">Category</span>
          <CategoryPicker value={category} onChange={setCategory} options={EXPENSE_CATEGORIES} />
        </>
      )}
      <label className="field">
        <span className="field-label">Date</span>
        <input className="text-input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
      </label>
      {error && <p className="error-text">{error}</p>}
      <button className="primary-button" disabled={busy}>
        {busy ? "Saving…" : submitLabel(kind)}
      </button>
    </form>
  );
}
