"""Validation: type rules, business rules, and the anomaly detector."""

from __future__ import annotations

import statistics
from datetime import date

from .documents import KNOWN_VENDORS, VENDOR_HISTORY

TODAY = date(2026, 7, 5)


def _parse(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def type_checks(doc_type: str, fields: dict) -> list[dict]:
    issues = []

    def issue(field, message, severity="error"):
        issues.append({"field": field, "message": message,
                       "severity": severity, "kind": "type"})

    if doc_type == "invoice":
        for name in ("vendor_name", "invoice_number", "invoice_date",
                     "due_date"):
            if not fields.get(name):
                issue(name, "required field missing")
        for name in ("subtotal", "tax", "total"):
            if fields.get(name, 0) < 0:
                issue(name, "monetary amount is negative")
        issued, due = _parse(fields.get("invoice_date", "")), \
            _parse(fields.get("due_date", ""))
        if issued and due and due < issued:
            issue("due_date", "due date before invoice date")
        items_total = round(sum(i["amount"]
                                for i in fields.get("line_items", [])), 2)
        if fields.get("line_items") and \
                abs(items_total - fields.get("subtotal", 0)) > 0.01:
            issue("subtotal", f"line items sum to {items_total},"
                              f" subtotal says {fields.get('subtotal')}")
        expected_total = round(fields.get("subtotal", 0)
                               + fields.get("tax", 0), 2)
        if abs(expected_total - fields.get("total", 0)) > 0.01:
            issue("total", f"subtotal + tax = {expected_total},"
                           f" total says {fields.get('total')}")
    elif doc_type == "contract":
        if len(fields.get("parties", [])) != 2:
            issues.append({"field": "parties", "severity": "error",
                           "kind": "type",
                           "message": "expected exactly two parties"})
        if fields.get("term_months", 0) <= 0:
            issues.append({"field": "term_months", "severity": "error",
                           "kind": "type",
                           "message": "term must be positive"})
    else:
        if fields.get("total", 0) <= 0:
            issues.append({"field": "total", "severity": "error",
                           "kind": "type", "message": "total must be positive"})
    return issues


def business_rules(doc_type: str, fields: dict) -> list[dict]:
    issues = []

    def issue(field, message, severity="warning"):
        issues.append({"field": field, "message": message,
                       "severity": severity, "kind": "business"})

    if doc_type == "invoice":
        vendor = fields.get("vendor_name", "")
        if vendor and vendor not in KNOWN_VENDORS:
            issue("vendor_name",
                  f"vendor '{vendor}' not in the approved vendor list",
                  severity="error")
    if doc_type == "contract":
        effective = _parse(fields.get("effective_date", ""))
        if effective and effective < TODAY:
            issue("effective_date",
                  f"effective date {effective} is in the past")
        if fields.get("termination_notice_days", 0) > 90:
            issue("termination_notice_days",
                  "termination notice unusually long")
    return issues


def anomaly_checks(doc_type: str, fields: dict) -> list[dict]:
    """Compare against historical totals for the same vendor."""
    if doc_type != "invoice":
        return []
    vendor = fields.get("vendor_name", "")
    history = VENDOR_HISTORY.get(vendor)
    if not history or len(history) < 3:
        return []
    mean = statistics.mean(history)
    stdev = statistics.pstdev(history) or 1.0
    z = (fields.get("total", 0) - mean) / stdev
    if abs(z) > 3:
        return [{"field": "total", "kind": "anomaly", "severity": "warning",
                 "message": f"total {fields.get('total'):.2f} is"
                            f" {z:.1f} standard deviations from this"
                            f" vendor's mean {mean:.2f}"}]
    return []


def validate(doc_type: str, fields: dict) -> dict:
    issues = (type_checks(doc_type, fields)
              + business_rules(doc_type, fields)
              + anomaly_checks(doc_type, fields))
    errors = [i for i in issues if i["severity"] == "error"]
    return {"issues": issues, "error_count": len(errors),
            "warning_count": len(issues) - len(errors),
            "passed": not errors}
