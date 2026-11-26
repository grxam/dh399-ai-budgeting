import argparse
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from budget_ai.db.database import Database
from budget_ai.reasoning.agent import ReasoningAgent
from budget_ai.vision.agent import VisionAgent
from budget_ai.models import Budget, Goal
from budget_ai.budgets import budget_status, unbudgeted_spending, goal_status


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

    # Budget Command
    budget_parser = subparsers.add_parser("budget", help="Budget management")
    budget_subparsers = budget_parser.add_subparsers(dest="budget_command", required=True)

    budget_set = budget_subparsers.add_parser("set", help="Set or update a budget")
    budget_set.add_argument("category", help="Category name")
    budget_set.add_argument("limit", type=float, help="Monthly limit")

    budget_list = budget_subparsers.add_parser("list", help="List budgets")

    budget_delete = budget_subparsers.add_parser("delete", help="Delete a budget")
    budget_delete.add_argument("category", help="Category name")

    # Goal Command
    goal_parser = subparsers.add_parser("goal", help="Goal management")
    goal_subparsers = goal_parser.add_subparsers(dest="goal_command", required=True)

    goal_add = goal_subparsers.add_parser("add", help="Add a goal")
    goal_add.add_argument("name", help="Goal name")
    goal_add.add_argument("target", type=float, help="Target amount")
    goal_add.add_argument("--date", help="Target date (YYYY-MM-DD)")

    goal_list = goal_subparsers.add_parser("list", help="List goals")

    goal_contribute = goal_subparsers.add_parser("contribute", help="Contribute to a goal")
    goal_contribute.add_argument("id", help="Goal ID")
    goal_contribute.add_argument("amount", type=float, help="Amount to contribute")

    goal_delete = goal_subparsers.add_parser("delete", help="Delete a goal")
    goal_delete.add_argument("id", help="Goal ID")

    args = parser.parse_args(argv)

    db = Database(db_path)
    try:
        if args.command == "ingest":
            agent = VisionAgent(client, vision_model)
            receipt = agent.extract(args.image)
            
            warnings = receipt.review_warnings()
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

        elif args.command == "budget":
            if args.budget_command == "set":
                budget = Budget(category=args.category, monthly_limit=args.limit)
                db.set_budget(budget)
                print(f"Budget set for {args.category} to {args.limit}")
            elif args.budget_command == "list":
                # budget_status returns status for current month by default
                status_list = budget_status(db)
                if not status_list:
                    print("No budgets set.")
                else:
                    print(f"{'Category':<15} | {'Limit':<10} | {'Spent':<10} | {'Remaining':<10} | {'State':<10}")
                    print("-" * 65)
                    for item in status_list:
                        print(f"{item['category']:<15} | {item['monthly_limit']:<10.2f} | {item['spent']:<10.2f} | {item['remaining']:<10.2f} | {item['state']:<10}")
                
                unbudgeted = unbudgeted_spending(db)
                if unbudgeted:
                    print("-" * 65)
                    for cat, amount in unbudgeted.items():
                        print(f"{cat:<15} | {amount:<10.2f} (unbudgeted)")

            elif args.budget_command == "delete":
                db.delete_budget(args.category)
                print(f"Budget for {args.category} deleted.")

        elif args.command == "goal":
            if args.goal_command == "add":
                goal = Goal(name=args.name, target_amount=args.target, target_date=args.date)
                db.add_goal(goal)
                print(f"Goal '{args.name}' added.")
            elif args.goal_command == "list":
                goals = goal_status(db)
                if not goals:
                    print("No goals set.")
                else:
                    print(f"{'ID':<5} | {'Name':<20} | {'Saved/Target':<15} | {'%':<5} | {'State':<10} | {'Monthly Needed':<15}")
                    print("-" * 85)
                    for g in goals:
                        print(f"{g['id']:<5} | {g['name']:<20} | {g['saved_amount']:<10.2f}/{g['target_amount']:<8.2f} | {g['pct_complete']:<4.1f} | {g['state']:<10} | {g['monthly_needed']:<14.2f}")
            elif args.goal_command == "contribute":
                db.contribute_to_goal(args.id, args.amount)
                print(f"Contributed {args.amount} to goal {args.id}.")
            elif args.goal_command == "delete":
                db.delete_goal(args.id)
                print(f"Goal {args.id} deleted.")

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
