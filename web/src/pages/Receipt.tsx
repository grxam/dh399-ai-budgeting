import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Camera, CircleCheck, ImagePlus, ScanLine, TriangleAlert } from "lucide-react";
import { api, type ExtractResult, type ReceiptData } from "../api";
import { categoryMeta } from "../categories";
import { money } from "../format";
import { Header } from "../components/Header";
import { ReceiptForm } from "../components/ReceiptForm";
import { TransactionForm } from "../components/TransactionForm";

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

function ScanFlow({ onSaved }: { onSaved: (message: string) => void }) {
  const cameraInput = useRef<HTMLInputElement>(null);
  const libraryInput = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [reading, setReading] = useState(false);
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [error, setError] = useState<string>();

  useEffect(() => () => void (preview && URL.revokeObjectURL(preview)), [preview]);

  const reset = () => {
    setPreview(null);
    setResult(null);
    setError(undefined);
  };

  const pick = async (file: File | undefined) => {
    if (!file) return;
    reset();
    setPreview(URL.createObjectURL(file));
    setReading(true);
    try {
      setResult(await api.extractReceipt(await shrinkImage(file)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setReading(false);
    }
  };

  const save = async (receipt: ReceiptData) => {
    await api.saveReceipt(receipt);
    reset();
    onSaved(`${receipt.merchant} saved`);
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
          ) : result ? (
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

      {result && (
        <ReceiptForm
          initial={result.receipt}
          submitLabel={(category) => `Save to ${categoryMeta(category).label}`}
          onSubmit={save}
        />
      )}

      {error && <p className="error-text">{error}</p>}
      {!reading && (
        <button className="secondary-button" onClick={reset}>
          {result ? "Discard" : "Start over"}
        </button>
      )}
    </section>
  );
}

// --- manual entry -----------------------------------------------------------

function ManualForm({ onSaved }: { onSaved: (message: string) => void }) {
  return (
    <TransactionForm
      autoFocus
      submitLabel={(kind) => (kind === "income" ? "Add income" : "Add expense")}
      onSubmit={async (txn) => {
        await api.addTransaction(txn);
        onSaved(`${money(txn.amount, true)} ${txn.kind === "income" ? "income" : "expense"} added`);
      }}
    />
  );
}
