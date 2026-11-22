import json

from openai import OpenAI

from budget_ai.db.database import Database

SYSTEM_PROMPT = "You are a friendly personal budgeting assistant. You are given the user's spending data as JSON inside <data> tags, followed by their question. Use only the numbers in the data; quote specific amounts, categories and merchants; never invent transactions. If there is too little data (for example fewer than 5 receipts), say so and tell the user what to add. Structure every answer as: Summary (1-2 sentences), What I noticed (2-4 bullets, each backed by a number), Suggestions (2-3 realistic actions). Keep it under 200 words, plain language. Give general budgeting tips only; do not recommend specific investments and do not claim to be a financial advisor. If the question is not about the user's spending, say you can only help with budgeting."

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
            "recent_receipts": self.db.recent_receipts(limit=50)
        }

    def advise(self, question: str) -> str:
        """Provides a budget advice based on a user question."""
        context = self.build_context()
        context_json = json.dumps(context)
        user_content = f"Data: <data>{context_json}</data>\n\nQuestion: {question}"
        
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=self.temperature
        )
        
        content = response.choices[0].message.content
        return content if content is not None else ""
