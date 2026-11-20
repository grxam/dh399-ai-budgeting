from budget_ai.vision.agent import parse_receipt_json

RAW = '{"merchant": "Cafe", "purchase_date": "2026-03-01", "total": 4.0, "category": "dining"}'


def test_parse_plain_json():
    r = parse_receipt_json(RAW)
    assert r.merchant == "Cafe" and r.total == 4.0


def test_parse_fenced_json():
    r = parse_receipt_json(f"```json\n{RAW}\n```")
    assert r.category == "dining"
