import argparse
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from budget_ai.db.database import Database
from budget_ai.reasoning.agent import ReasoningAgent
from budget_ai.vision.agent import VisionAgent


def main(argv: list[str] | None = None):
    load_dotenv()

    base_url = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    vision_model = os.getenv("VISION_MODEL", "gemma")
    reasoning_model = os.getenv("REASONING_MODEL", "gemma")
    db_path = os.getenv("DATABASE_PATH", "data/budget.db")

    client = OpenAI(
        base_url=base_url,
        api_key="not-needed"
    )

    parser = argparse.ArgumentParser(description="AI Budgeting App CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest Command
    ingest_parser = subparsers.add_parser("ingest", help="Process a receipt image")
    ingest_parser.add_argument("image", help="Path to the receipt image")

    # Summary Command
    summary_parser = subparsers.add_parser("summary", help="Print spending summary")

    # Advise Command
    advise_parser = subparsers.add_parser("advise", help="Get budgeting advice")
    advise_parser.add_argument("question", help="Your budgeting question")

    args = parser.parse_args(argv)

    db = Database(db_path)
    try:
        if args.command == "ingest":
            agent = VisionAgent(client, vision_model)
            receipt = agent.extract(args.image)
            
            warnings = receipt.arithmetic_warnings()
            for w in warnings:
                print(f"WARNING: {w}")
            
            if receipt.confidence < 0.6 or warnings:
                user_input = input("Save anyway? [y/N]: ").lower()
                if user_input != 'y':
                    print("Operation cancelled.")
                    return

            receipt_id = db.save_receipt(receipt)
            print(f"Saved Receipt ID: {receipt_id}")
            print(f"Merchant: {receipt.merchant}")
            print(f"Total: {receipt.total} {receipt.currency}")

        elif args.command == "summary":
            totals = db.spending_by_category()
            if not totals:
                print("No receipts yet.")
            else:
                print(f"{'Category':<15} | {'Total':<10}")
                print("-" * 30)
                for cat, total in totals.items():
                    print(f"{cat:<15} | {total:<10.2f}")

        elif args.command == "advise":
            agent = ReasoningAgent(db, client, reasoning_model)
            advice = agent.advise(args.question)
            print(f"\nAdvice:\n{advice}")

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
