import { createContext, useContext, useEffect, useState } from "react";

// --- selected month (shared by every screen's month picker) ---------------

export function currentMonth(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

/** The current month and the 11 before it, newest first. */
export function recentMonths(count = 12): string[] {
  const now = new Date();
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
}

export const MonthContext = createContext<{ month: string; setMonth: (m: string) => void }>({
  month: currentMonth(),
  setMonth: () => {},
});

export const useMonth = () => useContext(MonthContext);

// --- data loading ----------------------------------------------------------

interface ApiState<T> {
  data?: T;
  error?: string;
  loading: boolean;
}

/** Run an API call when deps change; reload() runs it again (after a save, say). */
export function useApi<T>(load: () => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<ApiState<T>>({ loading: true });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let live = true;
    setState((s) => ({ ...s, loading: true, error: undefined }));
    load()
      .then((data) => live && setState({ data, loading: false }))
      .catch((e: Error) => live && setState({ error: e.message, loading: false }));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, version]);

  return { ...state, reload: () => setVersion((v) => v + 1) };
}
