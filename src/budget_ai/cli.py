"""Command line entry point: `budget-ai ingest|summary|advise`."""

import argparse
from pathlib import Path

from budget_ai.config import get_settings
from budget_ai.db import Database
from budget_ai.pipeline import ingest_receipt
from budget_ai.reasoning import ReasoningAgent
from budget_ai.vision import VisionAgent


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="budget-ai")
    sub = parser.add_subparsers(dest="command", required=True)
    p_ingest = sub.add_parser("ingest", help="Extract a receipt image into the database")
    p_ingest.add_argument("image", type=Path)
    sub.add_parser("summary", help="Show spending by category")
    p_advise = sub.add_parser("advise", help="Ask the reasoning agent for advice")
    p_advise.add_argument("question")
    args = parser.parse_args(argv)

    db = Database(get_settings().database_path)
    try:
        if args.command == "ingest":
            receipt_id, receipt = ingest_receipt(args.image, VisionAgent(), db)
            amount = f"{receipt.currency} {receipt.total}"
            print(f"Saved receipt #{receipt_id}: {receipt.merchant} {amount}")
        elif args.command == "summary":
            for category, spent in db.spending_by_category().items():
                print(f"{category:<15}{spent:>10.2f}")
        elif args.command == "advise":
            print(ReasoningAgent(db).advise(args.question))
    finally:
        db.close()


if __name__ == "__main__":
    main()
