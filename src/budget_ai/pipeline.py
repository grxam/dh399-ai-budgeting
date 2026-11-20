"""End-to-end flow: image -> vision agent -> database."""

from pathlib import Path

from budget_ai.db import Database
from budget_ai.models import Receipt
from budget_ai.vision import VisionAgent


def ingest_receipt(image_path: Path, vision: VisionAgent, db: Database) -> tuple[int, Receipt]:
    receipt = vision.extract(image_path)
    return db.save_receipt(receipt), receipt
