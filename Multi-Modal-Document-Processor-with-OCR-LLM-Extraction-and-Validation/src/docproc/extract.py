"""LLM extraction engine: classify, extract to schema, score confidence.

The extraction parser plays the role of the LLM + instructor pair: it
maps OCR text into typed Pydantic models field by field and reports a
per field confidence based on how cleanly each value was found.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from .ocr import OCRResult


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float


class InvoiceExtraction(BaseModel):
    vendor_name: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    line_items: list[LineItem] = []


class ContractExtraction(BaseModel):
    parties: list[str] = []
    effective_date: str = ""
    term_months: int = 0
    auto_renews: bool = False
    termination_notice_days: int = 0
    governing_law: str = ""


class ReceiptExtraction(BaseModel):
    merchant: str = ""
    date: str = ""
    total: float = 0.0
    payment_method: str = ""


SCHEMAS = {"invoice": InvoiceExtraction, "contract": ContractExtraction,
           "receipt": ReceiptExtraction}

DATE = r"(\d{4}-\d{2}-\d{2})"
MONEY = r"([0-9][0-9,]*\.\d{2})"


def classify(text: str) -> str:
    upper = text.upper()
    if "INVOICE" in upper:
        return "invoice"
    if "AGREEMENT" in upper or "GOVERNING LAW" in upper.upper():
        return "contract"
    return "receipt"


def _num(value: str) -> float:
    return float(value.replace(",", ""))


def _field(pattern: str, text: str, group: int = 1) -> tuple[str, float]:
    """Return (value, confidence). Exact single match is high confidence,
    fuzzy recovery after collapsing OCR noise is lower, missing is zero."""
    match = re.search(pattern, text)
    if match:
        return match.group(group), 0.97
    collapsed = re.sub(r"\s+", " ", text.replace("l", "1").replace("O", "0"))
    match = re.search(pattern, collapsed)
    if match:
        return match.group(group), 0.72
    return "", 0.0


def extract(ocr: OCRResult) -> dict:
    text = ocr.text
    doc_type = classify(text)
    fields: dict = {}
    confidence: dict[str, float] = {}

    if doc_type == "invoice":
        for name, pattern in [
                ("invoice_number", r"INVOICE\s+([A-Z]+-?[\w-]+)"),
                ("vendor_name", r"Vendor:\s*([^\n]+)"),
                ("invoice_date", rf"Date:\s*{DATE}"),
                ("due_date", rf"Due:\s*{DATE}")]:
            value, conf = _field(pattern, text)
            fields[name] = value.strip()
            confidence[name] = conf
        for name, pattern in [("subtotal", rf"Subtotal:\s*{MONEY}"),
                              ("tax", rf"Tax:\s*{MONEY}"),
                              ("total", rf"TOTAL DUE:\s*{MONEY}")]:
            value, conf = _field(pattern, text)
            fields[name] = _num(value) if value else 0.0
            confidence[name] = conf
        items = []
        item_confs = []
        for match in re.finditer(
                rf"^\s+(.+?)\s+x(\d+)\s+@\s+{MONEY}\s+=\s+{MONEY}",
                text, re.MULTILINE):
            items.append({"description": match.group(1).strip(),
                          "quantity": float(match.group(2)),
                          "unit_price": _num(match.group(3)),
                          "amount": _num(match.group(4))})
            item_confs.append(0.95)
        fields["line_items"] = items
        confidence["line_items"] = round(
            sum(item_confs) / len(item_confs), 2) if item_confs else 0.0

    elif doc_type == "contract":
        parties, conf = _field(r"Between\s+(.+?)\s+and\s+(.+)", text)
        match = re.search(r"Between\s+(.+?)\s+and\s+(.+)", text)
        fields["parties"] = [match.group(1), match.group(2)] if match else []
        confidence["parties"] = 0.95 if match else 0.0
        for name, pattern, cast in [
                ("effective_date", rf"Effective Date:\s*{DATE}", str),
                ("term_months", r"Term:\s*(\d+)\s*months", int),
                ("termination_notice_days",
                 r"notice:\s*(\d+)\s*days", int),
                ("governing_law", r"Governing law:\s*([^\n]+)", str)]:
            value, conf = _field(pattern, text)
            fields[name] = cast(value) if value else \
                (0 if cast is int else "")
            confidence[name] = conf
        fields["auto_renews"] = "auto renewal: yes" in text
        confidence["auto_renews"] = 0.9

    else:
        for name, pattern, cast in [
                ("merchant", r"RECEIPT\s+([^\n]+)", str),
                ("date", rf"Date:\s*{DATE}", str),
                ("total", rf"Total\s+{MONEY}", _num),
                ("payment_method", r"Paid by\s+(\w+)", str)]:
            value, conf = _field(pattern, text)
            fields[name] = cast(value) if value else \
                (0.0 if cast is _num else "")
            confidence[name] = conf

    # Fold OCR agreement into every field's confidence: shaky pixels
    # cap how much we trust a clean looking regex hit.
    ocr_factor = min(1.0, ocr.engine_agreement + 0.05)
    confidence = {k: round(v * ocr_factor, 3) for k, v in confidence.items()}
    model = SCHEMAS[doc_type](**fields)
    overall = round(sum(confidence.values()) / max(1, len(confidence)), 3)
    return {"doc_type": doc_type, "fields": model.model_dump(),
            "field_confidence": confidence, "overall_confidence": overall,
            "ocr_agreement": ocr.engine_agreement,
            "used_vision_fallback": ocr.used_vision_fallback}
