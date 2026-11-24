import os
from typing import Generator
from dotenv import load_dotenv
from openai import OpenAI
from budget_ai.db.database import Database

load_dotenv()

def get_db() -> Generator[Database, None, None]:
    db_path = os.getenv("DATABASE_PATH", "data/budget.db")
    db = Database(db_path)
    try:
        yield db
    finally:
        db.close()

def get_client() -> OpenAI:
    return OpenAI(
        base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        api_key="not-needed"
    )
