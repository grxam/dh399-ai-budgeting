import argparse
import os

import uvicorn


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Run the Budget AI JSON API")
    parser.add_argument("--db", help="Database file to use instead of DATABASE_PATH (e.g. data/demo.db)")
    args = parser.parse_args(argv)
    if args.db:
        os.environ["DATABASE_PATH"] = args.db
        print(f"Using database {args.db}")

    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("budget_ai.api.app:app", host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
