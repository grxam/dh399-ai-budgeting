from types import SimpleNamespace
from unittest.mock import MagicMock

from budget_ai.db import Database
from budget_ai.models import Receipt
from budget_ai.reasoning import ReasoningAgent


def test_advise_sends_db_data_to_model():
    db = Database(":memory:")
    db.save_receipt(Receipt(merchant="Cafe", total=4.0, category="dining"))
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(text="Cut coffee.")]
    )

    answer = ReasoningAgent(db, client=client, model="test-model").advise("Where to save?")

    assert answer == "Cut coffee."
    sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "dining" in sent and "Where to save?" in sent
