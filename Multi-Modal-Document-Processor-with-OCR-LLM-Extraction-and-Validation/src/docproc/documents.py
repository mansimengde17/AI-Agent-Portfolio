"""Sample document corpus: invoices, contracts, and receipts.

Each document is stored as ground truth fields plus a rendered text
body. The scan simulator degrades the body with the kinds of noise a
real scanner pipeline produces (character confusion, dropped spaces,
smudges), which gives the dual engine OCR layer something honest to fix.
"""

from __future__ import annotations

import random

KNOWN_VENDORS = ["Northwind Supplies", "Acme Industrial", "Globex Paper Co",
                 "Initech Services", "Stark Logistics"]

DOCUMENTS = [
    {
        "doc_id": "inv-1001", "doc_type": "invoice", "scan_quality": "good",
        "truth": {"vendor_name": "Northwind Supplies",
                  "invoice_number": "INV-2026-0117",
                  "invoice_date": "2026-05-14", "due_date": "2026-06-13",
                  "subtotal": 1840.00, "tax": 147.20, "total": 1987.20,
                  "line_items": [
                      {"description": "Copy paper A4", "quantity": 40,
                       "unit_price": 32.00, "amount": 1280.00},
                      {"description": "Toner cartridge", "quantity": 8,
                       "unit_price": 70.00, "amount": 560.00}]},
    },
    {
        "doc_id": "inv-1002", "doc_type": "invoice", "scan_quality": "poor",
        "truth": {"vendor_name": "Acme Industrial",
                  "invoice_number": "INV-88413",
                  "invoice_date": "2026-05-20", "due_date": "2026-06-19",
                  "subtotal": 5300.00, "tax": 424.00, "total": 5724.00,
                  "line_items": [
                      {"description": "Hydraulic pump", "quantity": 2,
                       "unit_price": 2100.00, "amount": 4200.00},
                      {"description": "Seal kit", "quantity": 11,
                       "unit_price": 100.00, "amount": 1100.00}]},
    },
    {
        "doc_id": "inv-1003", "doc_type": "invoice", "scan_quality": "good",
        # anomaly: total far above this vendor's history
        "truth": {"vendor_name": "Globex Paper Co",
                  "invoice_number": "INV-55020",
                  "invoice_date": "2026-05-22", "due_date": "2026-06-21",
                  "subtotal": 48000.00, "tax": 3840.00, "total": 51840.00,
                  "line_items": [
                      {"description": "Bulk newsprint rolls", "quantity": 300,
                       "unit_price": 160.00, "amount": 48000.00}]},
    },
    {
        "doc_id": "inv-1004", "doc_type": "invoice", "scan_quality": "poor",
        # unknown vendor triggers the business rule check
        "truth": {"vendor_name": "Phantom Trading LLC",
                  "invoice_number": "INV-00913",
                  "invoice_date": "2026-05-25", "due_date": "2026-06-24",
                  "subtotal": 950.00, "tax": 76.00, "total": 1026.00,
                  "line_items": [
                      {"description": "Consulting retainer", "quantity": 1,
                       "unit_price": 950.00, "amount": 950.00}]},
    },
    {
        "doc_id": "con-2001", "doc_type": "contract", "scan_quality": "good",
        "truth": {"parties": ["Initech Services", "Wayne Enterprises"],
                  "effective_date": "2026-08-01", "term_months": 24,
                  "auto_renews": True,
                  "termination_notice_days": 60,
                  "governing_law": "Delaware"},
    },
    {
        "doc_id": "con-2002", "doc_type": "contract", "scan_quality": "poor",
        # effective date in the past triggers validation
        "truth": {"parties": ["Stark Logistics", "Oscorp"],
                  "effective_date": "2024-01-15", "term_months": 12,
                  "auto_renews": False,
                  "termination_notice_days": 30,
                  "governing_law": "New York"},
    },
    {
        "doc_id": "rec-3001", "doc_type": "receipt", "scan_quality": "poor",
        "truth": {"merchant": "Corner Cafe", "date": "2026-06-02",
                  "total": 42.75, "payment_method": "card"},
    },
]

VENDOR_HISTORY = {
    "Northwind Supplies": [1650.0, 2100.0, 1987.2, 1750.0],
    "Acme Industrial": [4900.0, 6100.0, 5724.0, 5350.0],
    "Globex Paper Co": [2100.0, 1900.0, 2450.0, 2300.0],
    "Initech Services": [8000.0, 8000.0],
    "Stark Logistics": [3300.0, 3100.0],
}


def render_text(doc: dict) -> str:
    truth = doc["truth"]
    if doc["doc_type"] == "invoice":
        lines = [f"INVOICE {truth['invoice_number']}",
                 f"Vendor: {truth['vendor_name']}",
                 f"Date: {truth['invoice_date']}  Due: {truth['due_date']}"]
        for item in truth["line_items"]:
            lines.append(f"  {item['description']}  x{item['quantity']}"
                         f" @ {item['unit_price']:.2f}"
                         f" = {item['amount']:.2f}")
        lines += [f"Subtotal: {truth['subtotal']:.2f}",
                  f"Tax: {truth['tax']:.2f}",
                  f"TOTAL DUE: {truth['total']:.2f}"]
        return "\n".join(lines)
    if doc["doc_type"] == "contract":
        return "\n".join([
            "SERVICES AGREEMENT",
            f"Between {truth['parties'][0]} and {truth['parties'][1]}",
            f"Effective Date: {truth['effective_date']}",
            f"Term: {truth['term_months']} months,"
            f" auto renewal: {'yes' if truth['auto_renews'] else 'no'}",
            f"Termination notice: {truth['termination_notice_days']} days",
            f"Governing law: {truth['governing_law']}"])
    return "\n".join([f"RECEIPT {truth['merchant']}",
                      f"Date: {truth['date']}",
                      f"Paid by {truth['payment_method']}",
                      f"Total {truth['total']:.2f}"])


CONFUSIONS = {"0": "O", "1": "l", "5": "S", "8": "B", "rn": "m", "cl": "d"}


def simulate_scan(doc: dict, engine_seed: int) -> str:
    """Degrade rendered text the way a noisy scan + OCR engine would.
    Different seeds model different OCR engines misreading different
    characters, which is what dual engine agreement recovers from."""
    text = render_text(doc)
    if doc["scan_quality"] == "good":
        noise_rate = 0.005
    else:
        noise_rate = 0.03
    rng = random.Random(doc["doc_id"] + str(engine_seed))
    output = []
    for char in text:
        roll = rng.random()
        if roll < noise_rate and char in CONFUSIONS:
            output.append(CONFUSIONS[char])
        elif roll < noise_rate * 1.5 and char == " ":
            continue  # dropped space
        else:
            output.append(char)
    return "".join(output)
