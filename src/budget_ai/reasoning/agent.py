import json

from openai import OpenAI

from budget_ai.db.database import Database
from budget_ai.budgets import budget_report

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
