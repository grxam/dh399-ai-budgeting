import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronLeft, RotateCcw, SendHorizontal, Sparkles } from "lucide-react";
import { api, type ChatMessage } from "../api";
import { monthName } from "../format";
import { useMonth } from "../hooks";

const STORAGE_KEY = "stashflow.chat";
const MAX_SENT = 20; // the API accepts up to 20 messages

const SUGGESTIONS = [
  "How am I doing this month?",
  "Where can I cut back?",
  "Am I on track for my goals?",
  "How does this month compare to last month?",
];

function loadHistory(): ChatMessage[] {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

// The local model can take a while. Keep the request outside the component so
// an answer still lands if the user switches tabs and comes back.
let inflight: { promise: Promise<string>; forLength: number } | null = null;

export default function Ask() {
  const { month } = useMonth();
  const [messages, setMessages] = useState<ChatMessage[]>(loadHistory);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, pending, error]);

  const waitFor = (job: NonNullable<typeof inflight>) => {
    setPending(true);
    setError(null);
    job.promise
      .then((answer) => {
        setMessages((current) =>
          current.length === job.forLength ? [...current, { role: "assistant", content: answer }] : current,
        );
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => {
        if (inflight === job) inflight = null;
        setPending(false);
      });
  };

  // Pick up a request that was still running when the user left the page.
  useEffect(() => {
    if (inflight && inflight.forLength === messages.length) waitFor(inflight);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ask = (history: ChatMessage[]) => {
    const job = {
      promise: api.chat(history.slice(-MAX_SENT), month).then((r) => r.answer),
      forLength: history.length,
    };
    inflight = job;
    waitFor(job);
  };

  const send = (text: string) => {
    const question = text.trim();
    if (!question || pending) return;
    const next: ChatMessage[] = [...messages, { role: "user", content: question }];
    setMessages(next);
    setDraft("");
    ask(next);
  };

  const newChat = () => {
    inflight = null;
    setMessages([]);
    setError(null);
    setPending(false);
  };

  const last = messages[messages.length - 1];
  const unanswered = !pending && last?.role === "user";

  return (
    <main className="page ask-page">
      <div className="ask-top">
        <Link to="/insights" className="back-link">
          <ChevronLeft size={18} /> Insights
        </Link>
        {messages.length > 0 && (
          <button className="link-button muted" onClick={newChat}>
            <RotateCcw size={14} /> New chat
          </button>
        )}
      </div>
      <header className="ask-head">
        <h1>Ask stashflow</h1>
        <p className="muted">
          Questions about your spending, budgets and goals for {monthName(month)}.
        </p>
      </header>

      {messages.length === 0 ? (
        <section className="ask-empty">
          <span className="scan-icon">
            <Sparkles size={32} strokeWidth={1.4} />
          </span>
          <p className="muted">Try one of these, or type your own.</p>
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="chip" onClick={() => send(s)}>
                {s}
              </button>
            ))}
          </div>
        </section>
      ) : (
        <div className="chat-log" aria-live="polite">
          {messages.map((m, i) => (
            <div key={i} className={`bubble bubble-${m.role}`}>
              {m.content}
            </div>
          ))}
          {pending && (
            <div className="bubble bubble-assistant typing" aria-label="Thinking">
              <span />
              <span />
              <span />
            </div>
          )}
          {unanswered && (
            <div className="bubble bubble-error">
              {error ?? "No answer yet."}{" "}
              <button className="link-button" onClick={() => ask(messages)}>
                Retry
              </button>
            </div>
          )}
        </div>
      )}
      <div ref={endRef} />

      <form
        className="ask-bar"
        onSubmit={(e) => {
          e.preventDefault();
          send(draft);
        }}
      >
        <div className="ask-input">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about your money…"
            aria-label="Your question"
            maxLength={2000}
            enterKeyHint="send"
          />
          <button className="send-button" disabled={pending || !draft.trim()} aria-label="Send">
            <SendHorizontal size={20} />
          </button>
        </div>
        <p className="disclaimer">AI answers use your data · general budgeting help, not financial advice</p>
      </form>
    </main>
  );
}
