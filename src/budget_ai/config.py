"""Settings loaded from environment variables / .env."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str | None
    vision_model: str
    reasoning_model: str
    database_path: Path


def get_settings() -> Settings:
    return Settings(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        vision_model=os.getenv("VISION_MODEL", "claude-sonnet-5-5"),
        reasoning_model=os.getenv("REASONING_MODEL", "claude-sonnet-5-5"),
        database_path=Path(os.getenv("DATABASE_PATH", "data/budget.db")),
    )
