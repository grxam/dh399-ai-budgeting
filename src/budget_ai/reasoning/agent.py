"""Reasoning agent: stored spending data + question -> budgeting advice."""

import json

import anthropic

from budget_ai.config import get_settings
from budget_ai.db import Database

SYSTEM_PROMPT = """You are a careful personal-budgeting assistant.
You are given the user's real spending data (from receipts) as JSON.
- Ground every claim in the data; cite numbers and merchants.
- Say so when there is too little data to conclude anything.
- Give practical, specific suggestions.
- You are not a licensed financial advisor; do not recommend specific investments.
"""


class ReasoningAgent:
    def __init__(
        self, db: Database, client: anthropic.Anthropic | None = None, model: str | None = None
    ):
        settings = get_settings()
        self.db = db
        self.client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.reasoning_model

    def build_context(self) -> str:
        return json.dumps(
            {
                "spending_by_category": self.db.spending_by_category(),
                "recent_receipts": self.db.recent_receipts(limit=50),
            },
            default=str,
        )

    def advise(self, question: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"<data>{self.build_context()}</data>\n\nQuestion: {question}",
                }
            ],
        )
        return response.content[0].text
