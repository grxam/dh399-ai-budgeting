"""Vision agent: receipt image -> validated Receipt."""

import base64
import mimetypes
from pathlib import Path

import anthropic

from budget_ai.config import get_settings
from budget_ai.models import CATEGORIES, Receipt

SYSTEM_PROMPT = f"""You extract data from receipt images.
Reply with ONLY a JSON object matching this schema, no prose, no code fences:
{Receipt.model_json_schema()}
Rules:
- Dates as YYYY-MM-DD. Amounts as plain numbers.
- category and item categories must be one of: {", ".join(CATEGORIES)}.
- If a field is unreadable, use null (or omit it). Never invent values.
- Lower `confidence` when the image is blurry or partially cropped.
"""


def parse_receipt_json(text: str) -> Receipt:
    """Parse model output into a Receipt, tolerating stray code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    return Receipt.model_validate_json(cleaned)


class VisionAgent:
    def __init__(self, client: anthropic.Anthropic | None = None, model: str | None = None):
        settings = get_settings()
        self.client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.vision_model

    def extract(self, image_path: Path) -> Receipt:
        media_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
        data = base64.standard_b64encode(image_path.read_bytes()).decode()
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": data},
                        },
                        {"type": "text", "text": "Extract this receipt."},
                    ],
                }
            ],
        )
        return parse_receipt_json(response.content[0].text)
