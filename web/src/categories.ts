import {
  ArrowUpDown,
  Bus,
  Clapperboard,
  Coffee,
  Ellipsis,
  GraduationCap,
  HeartPulse,
  House,
  ReceiptText,
  ShoppingBag,
  ShoppingBasket,
  type LucideIcon,
} from "lucide-react";

export type Tint = "green" | "beige" | "grey";

interface CategoryMeta {
  label: string;
  Icon: LucideIcon;
  tint: Tint;
}

// The backend's fixed category keys, shown with the design's friendly names.
// Order here is the order used in pickers.
export const CATEGORY_META: Record<string, CategoryMeta> = {
  housing: { label: "Rent", Icon: House, tint: "green" },
  groceries: { label: "Groceries", Icon: ShoppingBasket, tint: "green" },
  dining: { label: "Dining out", Icon: Coffee, tint: "beige" },
  transport: { label: "Transport", Icon: Bus, tint: "grey" },
  utilities: { label: "Bills", Icon: ReceiptText, tint: "beige" },
  shopping: { label: "Shopping", Icon: ShoppingBag, tint: "green" },
  health: { label: "Health", Icon: HeartPulse, tint: "beige" },
  entertainment: { label: "Entertainment", Icon: Clapperboard, tint: "grey" },
  education: { label: "Education", Icon: GraduationCap, tint: "grey" },
  other: { label: "Other", Icon: Ellipsis, tint: "grey" },
};

const INCOME: CategoryMeta = { label: "Income", Icon: ArrowUpDown, tint: "green" };

export const EXPENSE_CATEGORIES = Object.keys(CATEGORY_META);

export function categoryMeta(key: string): CategoryMeta {
  if (key === "income") return INCOME;
  return CATEGORY_META[key] ?? CATEGORY_META.other;
}
