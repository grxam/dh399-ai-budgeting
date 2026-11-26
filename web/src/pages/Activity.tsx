import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, Pencil, Search, SlidersHorizontal, X } from "lucide-react";
import { api, type ActivityItem, type ActivityQuery, type ReceiptData } from "../api";
import { EXPENSE_CATEGORIES, categoryMeta } from "../categories";
import { money, monthName, parseDate } from "../format";
import { useApi, useMonth } from "../hooks";
import { Header } from "../components/Header";
import { ReceiptForm } from "../components/ReceiptForm";
import { TransactionForm } from "../components/TransactionForm";
import { ActivityRow, CategoryPicker, Empty, LoadState, Sheet } from "../components/ui";

const LIMIT = 200;

interface Filters {
  category: string | null;
  kind: "expense" | "income" | null;
  min: string;
  max: string;
}

const NO_FILTERS: Filters = { category: null, kind: null, min: "", max: "" };

function countFilters(f: Filters): number {
  return [f.category, f.kind, f.min.trim(), f.max.trim()].filter(Boolean).length;
}

const amountOrUndefined = (text: string) => {
  const value = Number(text);
  return text.trim() !== "" && value >= 0 ? value : undefined;
};

export default function Activity() {
  const { month } = useMonth();
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState(""); // search text after a short pause in typing
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [onlyMonth, setOnlyMonth] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selected, setSelected] = useState<ActivityItem | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setQuery(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // With no search or filters this is the month's list, as before. Searching
  // or filtering looks through all history unless narrowed to the month.
  const searching = query !== "" || countFilters(filters) > 0;
  const params: ActivityQuery = {
    limit: LIMIT,
    month: !searching || onlyMonth ? month : undefined,
    q: query || undefined,
    category: filters.category ?? undefined,
    kind: filters.kind ?? undefined,
    minAmount: amountOrUndefined(filters.min),
    maxAmount: amountOrUndefined(filters.max),
  };
  const activity = useApi(() => api.activity(params), [JSON.stringify(params)]);
  const items = activity.data?.items;

  const income = items?.filter((i) => i.kind === "income").reduce((s, i) => s + i.amount, 0) ?? 0;
  const spent = items?.filter((i) => i.kind === "expense").reduce((s, i) => s + i.amount, 0) ?? 0;

  const clearAll = () => {
    setSearch("");
    setQuery("");
    setFilters(NO_FILTERS);
  };

  const chips: { label: string; clear: () => void }[] = [];
  if (filters.category) chips.push({ label: categoryMeta(filters.category).label, clear: () => setFilters({ ...filters, category: null }) });
  if (filters.kind) chips.push({ label: filters.kind === "income" ? "Income" : "Expenses", clear: () => setFilters({ ...filters, kind: null }) });
  if (filters.min.trim()) chips.push({ label: `From ${money(Number(filters.min))}`, clear: () => setFilters({ ...filters, min: "" }) });
  if (filters.max.trim()) chips.push({ label: `Up to ${money(Number(filters.max))}`, clear: () => setFilters({ ...filters, max: "" }) });

  return (
    <main className="page">
      <Link to="/" className="back-link">
        <ChevronLeft size={18} /> Overview
      </Link>
      <Header title="Activity" />

      <div className="search-row">
        <label className="search-box">
          <Search size={18} />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search stores, items, notes"
            aria-label="Search activity"
            maxLength={100}
            enterKeyHint="search"
          />
          {search && (
            <button type="button" className="icon-button small" onClick={() => setSearch("")} aria-label="Clear search">
              <X size={16} />
            </button>
          )}
        </label>
        <button className="filter-button" onClick={() => setFiltersOpen(true)} aria-label={`Filters${countFilters(filters) ? `, ${countFilters(filters)} on` : ""}`}>
          <SlidersHorizontal size={20} />
          {countFilters(filters) > 0 && <span className="filter-count">{countFilters(filters)}</span>}
        </button>
      </div>

      {searching && (
        <>
          {chips.length > 0 && (
            <div className="active-filters">
              {chips.map((chip) => (
                <button key={chip.label} className="chip chip-on" onClick={chip.clear} aria-label={`Remove filter ${chip.label}`}>
                  {chip.label} <X size={14} />
                </button>
              ))}
            </div>
          )}
          <div className="segmented scope" role="tablist" aria-label="Search where">
            <button role="tab" aria-selected={!onlyMonth} className={!onlyMonth ? "on" : ""} onClick={() => setOnlyMonth(false)}>
              All time
            </button>
            <button role="tab" aria-selected={onlyMonth} className={onlyMonth ? "on" : ""} onClick={() => setOnlyMonth(true)}>
              Only {monthName(month)}
            </button>
          </div>
        </>
      )}

      {!items ? (
        <LoadState loading={activity.loading} error={activity.error} onRetry={activity.reload} />
      ) : items.length === 0 ? (
        searching ? (
          <Empty
            title="No matches"
            body="Nothing matches that search and those filters."
            action={<button className="link-button" onClick={clearAll}>Clear search and filters</button>}
          />
        ) : (
          <Empty
            title="Nothing recorded"
            body={`No receipts or transactions in ${monthName(month)}.`}
            action={<Link to="/receipt" className="link">Add something</Link>}
          />
        )
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
          {items.length === LIMIT && <p className="muted small center">Showing the first {LIMIT}. Narrow your search to see more.</p>}
        </>
      )}

      <FilterSheet open={filtersOpen} value={filters} onClose={() => setFiltersOpen(false)} onApply={setFilters} />
      <DetailSheet
        key={selected ? `${selected.source}-${selected.id}` : "none"}
        item={selected}
        onClose={() => setSelected(null)}
        onChanged={() => {
          setSelected(null);
          activity.reload();
        }}
      />
    </main>
  );
}

function FilterSheet({ open, value, onClose, onApply }: { open: boolean; value: Filters; onClose: () => void; onApply: (f: Filters) => void }) {
  const [draft, setDraft] = useState(value);
  useEffect(() => {
    if (open) setDraft(value);
  }, [open, value]);

  const min = amountOrUndefined(draft.min);
  const max = amountOrUndefined(draft.max);
  const rangeError =
    (draft.min.trim() && min === undefined) || (draft.max.trim() && max === undefined)
      ? "Amounts must be numbers of 0 or more."
      : min !== undefined && max !== undefined && min > max
        ? "The minimum is higher than the maximum."
        : null;

  return (
    <Sheet open={open} onClose={onClose} title="Filters">
      <div className="form">
        <span className="field-label">Type</span>
        <div className="kind-toggle three" role="radiogroup" aria-label="Type">
          {([null, "expense", "income"] as const).map((k) => (
            <button
              key={k ?? "all"}
              type="button"
              role="radio"
              aria-checked={draft.kind === k}
              className={draft.kind === k ? "on" : ""}
              onClick={() => setDraft({ ...draft, kind: k, category: k === "income" ? null : draft.category })}
            >
              {k === null ? "All" : k === "expense" ? "Expenses" : "Income"}
            </button>
          ))}
        </div>

        {draft.kind !== "income" && (
          <>
            <span className="field-label">Category</span>
            <CategoryPicker
              value={draft.category ?? ""}
              onChange={(category) => setDraft({ ...draft, category: category || null })}
              options={EXPENSE_CATEGORIES}
              allLabel="All"
            />
          </>
        )}

        <span className="field-label">Amount</span>
        <div className="field-pair">
          <label className="money-input">
            <span>$</span>
            <input inputMode="decimal" placeholder="Min" value={draft.min} onChange={(e) => setDraft({ ...draft, min: e.target.value })} aria-label="Minimum amount" />
          </label>
          <label className="money-input">
            <span>$</span>
            <input inputMode="decimal" placeholder="Max" value={draft.max} onChange={(e) => setDraft({ ...draft, max: e.target.value })} aria-label="Maximum amount" />
          </label>
        </div>
        {rangeError && <p className="error-text">{rangeError}</p>}

        <button
          className="primary-button"
          disabled={!!rangeError}
          onClick={() => {
            onApply(draft);
            onClose();
          }}
        >
          Show results
        </button>
        <button
          className="secondary-button"
          onClick={() => {
            onApply(NO_FILTERS);
            onClose();
          }}
        >
          Clear filters
        </button>
      </div>
    </Sheet>
  );
}

function DetailSheet({ item, onClose, onChanged }: { item: ActivityItem | null; onClose: () => void; onChanged: () => void }) {
  const [error, setError] = useState<string>();
  const [editing, setEditing] = useState(false);
  const [receipt, setReceipt] = useState<ReceiptData | null>(null);
  const [loadingReceipt, setLoadingReceipt] = useState(false);
  if (!item) return null;
  const meta = categoryMeta(item.category);

  const startEdit = async () => {
    setError(undefined);
    if (item.source === "manual") return setEditing(true);
    setLoadingReceipt(true);
    try {
      setReceipt(await api.getReceipt(item.id));
      setEditing(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingReceipt(false);
    }
  };

  const remove = async () => {
    const what = item.source === "receipt" ? "receipt and its items" : item.kind;
    if (!confirm(`Delete this ${what}? This can't be undone.`)) return;
    try {
      if (item.source === "receipt") await api.deleteReceipt(item.id);
      else await api.deleteTransaction(item.id);
      setError(undefined);
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (editing) {
    return (
      <Sheet open onClose={onClose} title={item.source === "receipt" ? "Edit receipt" : `Edit ${item.kind}`}>
        {item.source === "manual" ? (
          <TransactionForm
            initial={{ kind: item.kind, amount: item.amount, description: item.title, category: item.category, date: item.date }}
            submitLabel={() => "Save changes"}
            onSubmit={async (txn) => {
              await api.updateTransaction(item.id, txn);
              onChanged();
            }}
          />
        ) : (
          receipt && (
            <ReceiptForm
              initial={receipt}
              submitLabel={() => "Save changes"}
              onSubmit={async (data) => {
                await api.updateReceipt(item.id, data);
                onChanged();
              }}
            />
          )
        )}
        <button className="secondary-button" onClick={() => setEditing(false)}>
          Cancel
        </button>
      </Sheet>
    );
  }

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
      <button className="primary-button" onClick={startEdit} disabled={loadingReceipt}>
        <Pencil size={18} /> {loadingReceipt ? "Loading…" : "Edit"}
      </button>
      <button className="danger-link" onClick={remove}>
        Delete
      </button>
    </Sheet>
  );
}
