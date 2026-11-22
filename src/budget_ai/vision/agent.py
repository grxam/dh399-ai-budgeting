import base64
import json
import mimetypes
from typing import Optional
from openai import OpenAI
from budget_ai.models import Receipt

SYSTEM_PROMPT = """
You are a receipt data extractor. You will be shown one image of a receipt.
Read it carefully and output a single JSON object. Output the JSON only: no explanation, no markdown, no code fences.

Fields:
- "merchant": string, the store name
- "purchase_date": string "YYYY-MM-DD", or null if not visible
- "currency": 3-letter code such as "USD", "AUD", "GBP" (infer from the symbol; default "USD")
- "subtotal": number or null
- "tax": number or null
- "total": number, the final amount paid
- "category": one of: groceries, dining, transport, utilities, housing, health, entertainment, shopping, education, other
- "items": list of objects, each with "description" (string), "quantity" (number, default 1), "unit_price" (number or null), "total_price" (number), "category" (same list as above)
- "confidence": number from 0 to 1. Use below 0.6 if the image is blurry, cropped, or hard to read.

Rules:
1. Numbers must be plain numbers: 12.50, not "$12.50".
2. Never guess. If a value is unreadable, use null. Do not invent items.
3. The sum of all item prices (including negative discount items) should equal the subtotal. If it does not, lower the confidence.
4. "total" is the final amount including tax, not the subtotal.
5. If the image is not a receipt, return {"merchant": "UNKNOWN", "total": 0, "confidence": 0, "items": []}.
6. Discounts, coupons, and loyalty savings are line items with a NEGATIVE total_price (for example -0.80) and a description such as "Discount". Include them in "items" so that the item prices add up to the subtotal.

Example output:
{"merchant": "Corner Market", "purchase_date": "2026-03-01", "currency": "USD", "subtotal": 11.50, "tax": 1.00, "total": 12.50, "category": "groceries", "items": [{"description": "Milk 2L", "quantity": 1, "unit_price": 3.50, "total_price": 3.50, "category": "groceries"}, {"description": "Bread", "quantity": 2, "unit_price": 4.00, "total_price": 8.00, "category": "groceries"}], "confidence": 0.92}
{"merchant": "Corner Market", "purchase_date": "2026-03-01", "currency": "USD", "subtotal": 7.18, "tax": 0.00, "total": 7.18, "category": "groceries", "items": [{"description": "Milk 2L", "quantity": 1, "unit_price": 3.99, "total_price": 3.99, "category": "groceries"}, {"description": "Bread", "quantity": 1, "unit_price": 3.99, "total_price": 3.99, "category": "groceries"}, {"description": "Discount", "quantity": 1, "unit_price": -0.80, "total_price": -0.80, "category": "groceries"}], "confidence": 0.9}
"""

class VisionAgent:
    """Agent that extracts structured receipt data from images."""
    def __init__(self, client: OpenAI, model_name: str):
        """Initialize with a client and model name."""
        self.client = client
        self.model_name = model_name

    def extract(self, image_path: str) -> Receipt:
        """Extract receipt data from an image path."""
        try:
            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")
            
            mime_type, _ = mimetypes.guess_type(image_path)
            mime_type = mime_type or "image/jpeg"

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract the data from this receipt."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}}
                ]}
            ]

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1
            )
            
            content = response.choices[0].message.content or ""
            
            try:
                return self.parse_receipt_json(content)
            except ValueError as e:
                # Retry once
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": f"That was invalid: {e}. Return only the corrected JSON object."})
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.1
                )
                
                retry_content = response.choices[0].message.content or ""
                return self.parse_receipt_json(retry_content)

        except FileNotFoundError:
            raise FileNotFoundError(f"Image file not found: {image_path}") from None

    @staticmethod
    def parse_receipt_json(text: str) -> Receipt:
        """Parse raw JSON text into a Receipt model."""
        clean_text = text.replace("```json", "").replace("```", "").strip()
        try:
            return Receipt.model_validate_json(clean_text)
        except Exception as e:
            try:
                start = clean_text.find('{')
                end = clean_text.rfind('}')
                if start != -1 and end != -1:
                    return Receipt.model_validate_json(clean_text[start:end+1])
            except Exception:
                pass
            raise ValueError(f"Failed to parse receipt JSON: {e}") from None
