import { useEffect, type ReactNode } from "react";
import { X } from "lucide-react";
import { categoryMeta, type Tint } from "../categories";
import { money, relativeDay } from "../format";
import type { ActivityItem } from "../api";

export function Progress({ value, variant = "light" }: { value: number; variant?: "light" | "hero" }) {
  const width = Math.max(0, Math.min(100, value));
  return (
    <div className={`progress progress-${variant}`} role="progressbar" aria-valuenow={Math.round(width)} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress-fill" style={{ width: `${width}%` }} />
    </div>
  );
}

export function IconTile({ category, tint, children }: { category?: string; tint?: Tint; children?: ReactNode }) {
  const meta = category ? categoryMeta(category) : undefined;
  const Icon = meta?.Icon;
  return (
    <span className={`icon-tile tint-${tint ?? meta?.tint ?? "grey"}`} aria-hidden>
      {children ?? (Icon && <Icon size={22} strokeWidth={1.6} />)}
    </span>
  );
}

export function SectionHead({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="section-head">
      <h2>{title}</h2>
      {action}
    </div>
  );
}

export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <h3>{title}</h3>
          <button className="icon-button small" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function LoadState({ loading, error, onRetry }: { loading: boolean; error?: string; onRetry?: () => void }) {
  if (error)
    return (
      <div className="notice notice-error">
        <p>{error}</p>
        {onRetry && (
          <button className="link-button" onClick={onRetry}>
            Try again
          </button>
        )}
      </div>
    );
  if (loading) return <div className="skeleton" aria-label="Loading" />;
  return null;
}

export function Empty({ title, body, action }: { title: string; body: string; action?: ReactNode }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      <p className="muted">{body}</p>
      {action}
    </div>
  );
}

export function ActivityRow({ item, onClick }: { item: ActivityItem; onClick?: () => void }) {
  const meta = categoryMeta(item.category);
  const income = item.kind === "income";
  const content = (
    <>
      <IconTile category={item.category} />
      <span className="row-main">
        <span className="row-title">{item.title || meta.label}</span>
        <span className="row-sub">
          {meta.label} · {relativeDay(item.date)}
        </span>
      </span>
      <span className={`row-amount ${income ? "positive" : ""}`}>
        {income ? "+" : "−"}
        {money(item.amount, true)}
      </span>
    </>
  );
  return onClick ? (
    <button className="activity-row" onClick={onClick}>
      {content}
    </button>
  ) : (
    <div className="activity-row">{content}</div>
  );
}

export function CategoryPicker({
  value,
  onChange,
  options,
  allLabel,
}: {
  value: string;
  onChange: (c: string) => void;
  options: string[];
  /** Adds a first chip with this label that selects "" (no category). */
  allLabel?: string;
}) {
  return (
    <div className="chip-row" role="radiogroup" aria-label="Category">
      {allLabel && (
        <button type="button" role="radio" aria-checked={value === ""} className={`chip ${value === "" ? "chip-on" : ""}`} onClick={() => onChange("")}>
          {allLabel}
        </button>
      )}
      {options.map((key) => {
        const { label, Icon } = categoryMeta(key);
        return (
          <button
            key={key}
            type="button"
            role="radio"
            aria-checked={value === key}
            className={`chip ${value === key ? "chip-on" : ""}`}
            onClick={() => onChange(key)}
          >
            <Icon size={16} strokeWidth={1.8} />
            {label}
          </button>
        );
      })}
    </div>
  );
}
