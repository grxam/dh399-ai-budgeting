import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Camera, CircleCheck, ImagePlus, ScanLine, TriangleAlert } from "lucide-react";
import { api, type ExtractResult, type ReceiptData } from "../api";
import { EXPENSE_CATEGORIES, categoryMeta } from "../categories";
import { money, todayIso } from "../format";
import { Header } from "../components/Header";
import { CategoryPicker } from "../components/ui";

type Mode = "scan" | "manual";

export default function Receipt() {
  const [mode, setMode] = useState<Mode>("scan");
  const [done, setDone] = useState<string | null>(null);

  return (
    <main className="page">
      <Header title="Receipt" showMonth={false} />
      {done ? (
        <section className="done-card">
          <CircleCheck size={40} strokeWidth={1.4} />
          <h2>{done}</h2>
          <p className="muted">It's in your activity and counted toward your budgets.</p>
          <button className="primary-button" onClick={() => setDone(null)}>
            Add another
          </button>
          <Link to="/" className="link center">
            Back to overview
          </Link>
        </section>
      ) : (
        <>
          <div className="segmented" role="tablist">
            <button role="tab" aria-selected={mode === "scan"} className={mode === "scan" ? "on" : ""} onClick={() => setMode("scan")}>
              Scan a receipt
            </button>
            <button role="tab" aria-selected={mode === "manual"} className={mode === "manual" ? "on" : ""} onClick={() => setMode("manual")}>
              Add manually
            </button>
          </div>
          {mode === "scan" ? <ScanFlow onSaved={setDone} /> : <ManualForm onSaved={setDone} />}
        </>
      )}
    </main>
  );
}

// --- scanning ---------------------------------------------------------------

// Phone photos are 12 MP or more; the vision model reads receipts fine at a
// fraction of that and runs much faster, and the upload is smaller too.
const MAX_EDGE = 1600;

/** Scale a photo down to MAX_EDGE on its longest side as a JPEG. Returns the original if it's already small or can't be decoded. */
async function shrinkImage(file: File): Promise<File> {
  const url = URL.createObjectURL(file);
  try {
    const img = new Image();
    img.src = url;
    await img.decode(); // the browser applies the photo's rotation (EXIF) here
    const scale = MAX_EDGE / Math.max(img.naturalWidth, img.naturalHeight);
    if (scale >= 1) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    if (!blob) return file;
    return new File([blob], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch {
    return file; // e.g. a format this browser can't draw; let the server try
  } finally {
    URL.revokeObjectURL(url);
  }
}

interface Draft {
  merchant: string;
  date: string;
  total: string;
  category: string;
}

function ScanFlow({ onSaved }: { onSaved: (message: string) => void }) {
  const cameraInput = useRef<HTMLInputElement>(null);
  const libraryInput = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string>();
  const [saving, setSaving] = useState(false);

  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  const reset = () => {
    setPreview(null);
    setResult(null);
    setDraft(null);
    setError(undefined);
  };

  const pick = async (file: File | undefined) => {
    if (!file) return;
    reset();
    setPreview(URL.createObjectURL(file));
    setReading(true);
    try {
      const res = await api.extractReceipt(await shrinkImage(file));
      setResult(res);
      setDraft({
        merchant: res.receipt.merchant,
        date: res.receipt.purchase_date ?? "",
        total: String(res.receipt.total),
        category: res.receipt.category,
      });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReading(false);
    }
  };

  const save = async () => {
    if (!result || !draft) return;
    const total = Number(draft.total);
    if (!draft.merchant.trim()) return setError("Add the store name.");
    if (!(total > 0)) return setError("Enter the total paid.");
    setSaving(true);
    setError(undefined);
    try {
      const receipt: ReceiptData = {
        ...result.receipt,
        merchant: draft.merchant.trim(),
        purchase_date: draft.date || null,
        total,
        category: draft.category,
      };
      await api.saveReceipt(receipt);
      reset();
      onSaved(`${receipt.merchant} saved`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const inputs = (
    <>
      <input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden onChange={(e) => pick(e.target.files?.[0])} />
      <input ref={libraryInput} type="file" accept="image/*" hidden onChange={(e) => pick(e.target.files?.[0])} />
    </>
  );

  if (!preview) {
    return (
      <section className="scan-card">
        {inputs}
        <span className="scan-icon">
          <ScanLine size={36} strokeWidth={1.4} />
        </span>
        <h2>Snap a receipt</h2>
        <p className="muted">We'll read the store, date, total and items for you. You can check everything before it's saved.</p>
        <button className="primary-button" onClick={() => cameraInput.current?.click()}>
          <Camera size={20} /> Take a photo
        </button>
        <button className="secondary-button" onClick={() => libraryInput.current?.click()}>
          <ImagePlus size={20} /> Choose from library
        </button>
      </section>
    );
  }

  return (
    <section className="review">
      {inputs}
      <div className="review-top">
        <img src={preview} alt="Receipt photo" className={`receipt-thumb ${reading ? "reading" : ""}`} />
        <div>
          {reading ? (
            <>
              <strong>Reading your receipt…</strong>
              <p className="muted small">This can take a little while on a local model.</p>
            </>
          ) : draft ? (
            <>
              <strong>Check the details</strong>
              <p className="muted small">Fix anything we got wrong, then save.</p>
            </>
          ) : (
            <strong>We couldn't read that one</strong>
          )}
          <button className="link-button" onClick={() => libraryInput.current?.click()} disabled={reading}>
            Use a different photo
          </button>
        </div>
      </div>

      {result?.needs_review && (
        <div className="notice notice-warn">
          <TriangleAlert size={18} />
          <div>
            <strong>Please double-check this one</strong>
            {result.receipt.confidence < 0.6 && <p>The photo was hard to read, so some details may be off.</p>}
            {result.warnings.map((w) => (
              <p key={w}>{w}</p>
            ))}
          </div>
        </div>
      )}

      {draft && result && (
        <div className="form">
          <label className="field">
            <span className="field-label">Store</span>
            <input className="text-input" value={draft.merchant} onChange={(e) => setDraft({ ...draft, merchant: e.target.value })} />
          </label>
          <div className="field-pair">
            <label className="field">
              <span className="field-label">Date</span>
              <input className="text-input" type="date" value={draft.date} onChange={(e) => setDraft({ ...draft, date: e.target.value })} />
            </label>
            <label className="field">
              <span className="field-label">Total ({result.receipt.currency})</span>
              <span className="money-input">
                <span>$</span>
                <input inputMode="decimal" value={draft.total} onChange={(e) => setDraft({ ...draft, total: e.target.value })} />
              </span>
            </label>
          </div>
          <span className="field-label">Category</span>
          <CategoryPicker value={draft.category} onChange={(category) => setDraft({ ...draft, category })} options={EXPENSE_CATEGORIES} />

          {result.receipt.items.length > 0 && (
            <details className="items">
              <summary>{result.receipt.items.length} items</summary>
              <ul>
                {result.receipt.items.map((item, i) => (
                  <li key={i}>
                    <span>
                      {item.quantity !== 1 && `${item.quantity} × `}
                      {item.description}
                    </span>
                    <span>{money(item.total_price, true)}</span>
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {error && <p className="error-text">{error}</p>}
      {draft && (
        <>
          <button className="primary-button" onClick={save} disabled={saving}>
            {saving ? "Saving…" : `Save to ${categoryMeta(draft.category).label}`}
          </button>
          <button className="secondary-button" onClick={reset} disabled={saving}>
            Discard
          </button>
        </>
      )}
      {!reading && !draft && (
        <button className="secondary-button" onClick={reset}>
          Start over
        </button>
      )}
    </section>
  );
}

// --- manual entry -----------------------------------------------------------

function ManualForm({ onSaved }: { onSaved: (message: string) => void }) {
  const [kind, setKind] = useState<"expense" | "income">("expense");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("groceries");
  const [date, setDate] = useState(todayIso());
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = Number(amount);
    if (!(value > 0)) return setError("Enter an amount above zero.");
    setBusy(true);
    setError(undefined);
    try {
      await api.addTransaction({
        kind,
        amount: value,
        category: kind === "expense" ? category : undefined,
        description: description.trim() || null,
        txn_date: date,
      });
      onSaved(kind === "income" ? `${money(value, true)} income added` : `${money(value, true)} expense added`);
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
        <input inputMode="decimal" placeholder="0.00" value={amount} onChange={(e) => setAmount(e.target.value)} aria-label="Amount" autoFocus />
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
        {busy ? "Saving…" : kind === "income" ? "Add income" : "Add expense"}
      </button>
    </form>
  );
}
