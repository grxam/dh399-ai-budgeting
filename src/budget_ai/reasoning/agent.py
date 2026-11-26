import json
import re
from datetime import date

from openai import OpenAI

from budget_ai.db.database import Database
from budget_ai.budgets import budget_report, current_month
from budget_ai.insights import spending_insights

SYSTEM_PROMPT = (
    "You are a friendly personal budgeting assistant. You are given the user's spending data as JSON inside <data> tags, followed by their question. Use only the numbers in the data; quote specific amounts, categories and merchants; never invent transactions. If there is too little data (for example fewer than 5 receipts), say so and tell the user what to add. Structure every answer as: Summary (1-2 sentences), What I noticed (2-4 bullets, each backed by a number), Suggestions (2-3 realistic actions). Keep it under 200 words, plain language. Give general budgeting tips only; do not recommend specific investments and do not claim to be a financial advisor. If the question is not about the user's spending, say you can only help with budgeting. "
    "If a budget_report is present, compare spending to each budget using the spent, remaining and state fields, mention any category whose state is over or warning, and report progress toward each goal using pct_complete and monthly_needed. Never invent budgets or goals that are not in the data. If there are no budgets, suggest the user set one."
)

# Used for short tips in the app (e.g. the Insights card): same data rules, no report format.
BRIEF_PROMPT = (
    "You are a friendly personal budgeting assistant. You are given the user's spending data as JSON inside <data> tags, followed by their question. Use only the numbers in the data and never invent transactions, budgets or goals. "
    "Answer in at most two short sentences with one concrete, realistic suggestion, quoting a specific amount or category where it helps. No headings, no bullet points, no preamble. "
    "Give general budgeting tips only; do not recommend specific investments and do not claim to be a financial advisor."
)

# Used for the Ask chat: conversational, answers the question that was asked.
CHAT_PROMPT = (
    "You are stashflow, a friendly personal budgeting assistant chatting with the user about their own money. "
    "Their data is in the <data> JSON below: budgets and goals for the month being viewed (budget_report), "
    "spending this month against the same days last month (insights), recent activity including scanned receipts, "
    "manual expenses and income (recent_activity), and income for the month. "
    "Use only the numbers in the data and never invent transactions, budgets or goals. "
    "Answer the user's question directly in 2-4 short sentences of plain text, quoting specific amounts and categories. "
    "No headings, bullet points or markdown. If the data can't answer the question, say what is missing and what the user could add. "
    "Use the earlier messages to understand follow-up questions. "
    "Give general budgeting help only; do not recommend specific investments and do not claim to be a financial advisor. "
    "If a question is not about the user's money or budgeting, say you can only help with their budget."
)

# How many recent chat messages are sent to the model, to stay within its context window.
CHAT_HISTORY_LIMIT = 10


def clean_reply(text: str) -> str:
    """Remove reasoning blocks some local models emit, and markdown bold markers."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.replace("**", "").strip()


class ReasoningAgent:
    """Agent that provides budgeting advice based on transaction history."""
    def __init__(self, db: Database, client: OpenAI, model_name: str, temperature: float = 0.5):
        """Initialize with a database, client, and model name."""
        self.db = db
        self.client = client
        self.model_name = model_name
        self.temperature = temperature

    def build_context(self) -> dict:
        """Builds a dictionary of the user's spending summary and recent receipts."""
        return {
            "spending_by_category": self.db.spending_by_category(),
            "recent_receipts": self.db.recent_receipts(limit=50),
            "budget_report": budget_report(self.db)
        }

    def build_chat_context(self, month: str | None = None, today: date | None = None) -> dict:
        """Data for the Ask chat: everything the app's screens show for the month.

        Unlike build_context (used for advice and tips), this includes manual
        expenses, income and the comparison with last month.
        """
        today = today or date.today()
        month = month or current_month(today)
        month_activity = self.db.list_activity(month=month, limit=500)
        return {
            "today": today.isoformat(),
            "month": month,
            "budget_report": budget_report(self.db, month=month, today=today),
            "insights": spending_insights(self.db, month=month, today=today),
            "income_this_month": round(
                sum(a["amount"] for a in month_activity if a["kind"] == "income"), 2
            ),
            "recent_activity": self.db.list_activity(limit=50),
        }

    def chat(self, messages: list[dict], month: str | None = None) -> str:
        """Answer the latest question in a conversation about the user's budget.

        messages: [{"role": "user" | "assistant", "content": str}, ...], oldest
        first, ending with the user's new question.
        """
        history = messages[-CHAT_HISTORY_LIMIT:]
        # Keep turns alternating from a user message; some chat templates require it.
        while history and history[0]["role"] != "user":
            history = history[1:]

        context_json = json.dumps(self.build_chat_context(month))
        system = f"{CHAT_PROMPT}\n\nData: <data>{context_json}</data>"

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "system", "content": system}]
            + [{"role": m["role"], "content": m["content"]} for m in history],
            temperature=self.temperature,
        )
        return clean_reply(response.choices[0].message.content or "")

    def advise(self, question: str, brief: bool = False) -> str:
        """Provides a budget advice based on a user question.

        brief=True asks for a one- or two-sentence tip instead of the full
        Summary / What I noticed / Suggestions answer.
        """
        context = self.build_context()
        context_json = json.dumps(context)
        user_content = f"Data: <data>{context_json}</data>\n\nQuestion: {question}"
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": BRIEF_PROMPT if brief else SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=self.temperature
        )
        
        content = response.choices[0].message.content
        return content if content is not None else ""
