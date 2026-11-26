import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { api, type ActivityItem } from "../api";
import { categoryMeta } from "../categories";
import { money, monthName, parseDate } from "../format";
import { useApi, useMonth } from "../hooks";
import { Header } from "../components/Header";
import { ActivityRow, Empty, LoadState, Sheet } from "../components/ui";

export default function Activity() {
  const { month } = useMonth();
  const activity = useApi(() => api.activity({ month, limit: 200 }), [month]);
  const [selected, setSelected] = useState<ActivityItem | null>(null);
  const items = activity.data?.items;

  const income = items?.filter((i) => i.kind === "income").reduce((s, i) => s + i.amount, 0) ?? 0;
  const spent = items?.filter((i) => i.kind === "expense").reduce((s, i) => s + i.amount, 0) ?? 0;

  return (
    <main className="page">
      <Link to="/" className="back-link">
        <ChevronLeft size={18} /> Overview
      </Link>
      <Header title="Activity" />
      {!items ? (
        <LoadState loading={activity.loading} error={activity.error} onRetry={activity.reload} />
      ) : items.length === 0 ? (
        <Empty
          title="Nothing recorded"
          body={`No receipts or transactions in ${monthName(month)}.`}
          action={<Link to="/receipt" className="link">Add something</Link>}
        />
      ) : (
        <>
          <div className="totals-row">
            <div>
              <span className="muted small">In</span>
              <strong className="positive">+{money(income, true)}</strong>
            </div>
            <div>
              <span className="muted small">Out</span>
              <strong>−{money(spent, true)}</strong>
            </div>
          </div>
          <div className="activity-list">
            {items.map((item) => (
              <ActivityRow key={`${item.source}-${item.id}`} item={item} onClick={() => setSelected(item)} />
            ))}
          </div>
        </>
      )}
      <DetailSheet
        item={selected}
        onClose={() => setSelected(null)}
        onDeleted={() => {
          setSelected(null);
          activity.reload();
        }}
      />
    </main>
  );
}

function DetailSheet({ item, onClose, onDeleted }: { item: ActivityItem | null; onClose: () => void; onDeleted: () => void }) {
  const [error, setError] = useState<string>();
  if (!item) return null;
  const meta = categoryMeta(item.category);

  const remove = async () => {
    const what = item.source === "receipt" ? "receipt and its items" : item.kind;
    if (!confirm(`Delete this ${what}? This can't be undone.`)) return;
    try {
      if (item.source === "receipt") await api.deleteReceipt(item.id);
      else await api.deleteTransaction(item.id);
      setError(undefined);
      onDeleted();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Sheet open onClose={onClose} title={item.title || meta.label}>
      <dl className="details">
        <dt>Amount</dt>
        <dd className={item.kind === "income" ? "positive" : ""}>
          {item.kind === "income" ? "+" : "−"}
          {money(item.amount, true)}
        </dd>
        <dt>Category</dt>
        <dd>{meta.label}</dd>
        <dt>Date</dt>
        <dd>{item.date ? parseDate(item.date).toLocaleDateString("en-US", { weekday: "short", month: "long", day: "numeric", year: "numeric" }) : "Not on the receipt"}</dd>
        <dt>Added by</dt>
        <dd>{item.source === "receipt" ? "Scanned receipt" : "Entered by hand"}</dd>
      </dl>
      {error && <p className="error-text">{error}</p>}
      <button className="danger-link" onClick={remove}>
        Delete
      </button>
    </Sheet>
  );
}
