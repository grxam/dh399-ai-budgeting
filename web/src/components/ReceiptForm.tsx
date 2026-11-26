import { useState } from "react";
import { Plus, X } from "lucide-react";
import type { LineItem, ReceiptData } from "../api";
import { EXPENSE_CATEGORIES } from "../categories";
import { money } from "../format";
import { CategoryPicker } from "./ui";

interface ItemDraft {
  description: string;
  quantity: string;
  price: string;
  original?: LineItem;
}

// Prices are kept as text; a leading "-" marks a discount.
const isNegative = (price: string) => price.trim().startsWith("-");
const flipSign = (price: string) => (isNegative(price) ? price.trim().slice(1) : `-${price.trim()}`);
/** Apply what was typed while keeping the current sign; typing "-" (on a real keyboard) makes it negative. */
const withSign = (typed: string, current: string) => {
  const negative = typed.includes("-") || isNegative(current);
  const digits = typed.replace(/-/g, "");
  return negative ? `-${digits}` : digits;
};

const toDraft = (item: LineItem): ItemDraft => ({
  description: item.description,
  quantity: String(item.quantity),
  price: String(item.total_price),
  original: item,
});

/**
 * Form for a receipt's details and line items. Used to review a scan before
 * saving it and to edit a saved receipt.
 */
export function ReceiptForm({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial: ReceiptData;
  submitLabel: (category: string) => string;
  onSubmit: (receipt: ReceiptData) => Promise<void>;
}) {
  const [merchant, setMerchant] = useState(initial.merchant);
  const [date, setDate] = useState(initial.purchase_date ?? "");
  const [total, setTotal] = useState(String(initial.total));
  const [category, setCategory] = useState(initial.category);
  const [items, setItems] = useState<ItemDraft[]>(initial.items.map(toDraft));
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const setItem = (index: number, change: Partial<ItemDraft>) =>
    setItems(items.map((item, i) => (i === index ? { ...item, ...change } : item)));

  const itemSum = items.reduce((sum, item) => sum + (Number(item.price) || 0), 0);
  const totalValue = Number(total);
  const mismatch = items.length > 0 && totalValue > 0 && Math.abs(itemSum - totalValue) > 0.05;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!merchant.trim()) return setError("Add the store name.");
    if (!(totalValue > 0)) return setError("Enter the total paid.");
    const kept = items.filter((item) => item.description.trim() || item.price.trim());
    if (kept.some((item) => !item.description.trim())) return setError("Every item needs a description.");
    if (kept.some((item) => item.price.trim() === "" || Number.isNaN(Number(item.price)))) {
      return setError("Every item needs a price (it can be negative for a discount).");
    }
    setBusy(true);
    setError(undefined);
    try {
      await onSubmit({
        ...initial,
        merchant: merchant.trim(),
        purchase_date: date || null,
        total: totalValue,
        category,
        items: kept.map((item) => ({
          description: item.description.trim(),
          quantity: Number(item.quantity) > 0 ? Number(item.quantity) : 1,
          unit_price: item.original && String(item.original.total_price) === item.price ? item.original.unit_price : null,
          total_price: Number(item.price),
          category: item.original?.category ?? category,
        })),
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="form" onSubmit={submit}>
      <label className="field">
        <span className="field-label">Store</span>
        <input className="text-input" value={merchant} onChange={(e) => setMerchant(e.target.value)} />
      </label>
      <div className="field-pair">
        <label className="field">
          <span className="field-label">Date</span>
          <input className="text-input" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label className="field">
          <span className="field-label">Total ({initial.currency})</span>
          <span className="money-input">
            <span>$</span>
            <input inputMode="decimal" value={total} onChange={(e) => setTotal(e.target.value)} />
          </span>
        </label>
      </div>
      <span className="field-label">Category</span>
      <CategoryPicker value={category} onChange={setCategory} options={EXPENSE_CATEGORIES} />

      <div className="item-editor">
        <div className="item-editor-head">
          <span className="field-label">Items</span>
          {items.length > 0 && <span className="muted small">add up to {money(itemSum, true)}</span>}
        </div>
        {items.map((item, i) => (
          <div key={i} className="item-row">
            <input
              className="text-input item-desc"
              value={item.description}
              placeholder="Item"
              aria-label={`Item ${i + 1} description`}
              onChange={(e) => setItem(i, { description: e.target.value })}
            />
            <input
              className="text-input item-qty"
              inputMode="decimal"
              value={item.quantity}
              aria-label={`Item ${i + 1} quantity`}
              onChange={(e) => setItem(i, { quantity: e.target.value })}
            />
            <span className={`money-input item-price ${isNegative(item.price) ? "negative" : ""}`}>
              {/* Phone number keypads have no minus key, so the sign is a toggle. */}
              <button
                type="button"
                className="sign-toggle"
                aria-label={isNegative(item.price) ? `Item ${i + 1} is a discount; make it a charge` : `Make item ${i + 1} a discount (negative)`}
                aria-pressed={isNegative(item.price)}
                onClick={() => setItem(i, { price: flipSign(item.price) })}
              >
                {isNegative(item.price) ? "−$" : "$"}
              </button>
              <input
                inputMode="decimal"
                value={item.price.replace(/^-/, "")}
                aria-label={`Item ${i + 1} price`}
                onChange={(e) => setItem(i, { price: withSign(e.target.value, item.price) })}
              />
            </span>
            <button
              type="button"
              className="icon-button small"
              aria-label={`Remove ${item.description || `item ${i + 1}`}`}
              onClick={() => setItems(items.filter((_, j) => j !== i))}
            >
              <X size={16} />
            </button>
          </div>
        ))}
        <button
          type="button"
          className="link-button add-item"
          onClick={() => setItems([...items, { description: "", quantity: "1", price: "" }])}
        >
          <Plus size={16} /> Add item
        </button>
        {mismatch && (
          <p className="muted small warn-text">
            Items add up to {money(itemSum, true)}, but the total is {money(totalValue, true)}. That's fine if
            there was tax or a discount.
          </p>
        )}
      </div>

      {error && <p className="error-text">{error}</p>}
      <button className="primary-button" disabled={busy}>
        {busy ? "Saving…" : submitLabel(category)}
      </button>
    </form>
  );
}
