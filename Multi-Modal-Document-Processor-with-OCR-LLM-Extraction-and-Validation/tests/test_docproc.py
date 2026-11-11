import sys
import unittest

sys.path.insert(0, "src")

from docproc.documents import DOCUMENTS
from docproc.extract import classify, extract
from docproc.ocr import run_ocr
from docproc.pipeline import Processor
from docproc.validate import validate


def doc(doc_id: str) -> dict:
    return next(d for d in DOCUMENTS if d["doc_id"] == doc_id)


class OCRTests(unittest.TestCase):
    def test_good_scan_high_agreement(self):
        result = run_ocr(doc("inv-1001"))
        self.assertGreater(result.engine_agreement, 0.95)

    def test_poor_scan_triggers_more_preprocessing(self):
        result = run_ocr(doc("inv-1002"))
        self.assertIn("deskew", result.preprocessing)


class ExtractionTests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(classify("INVOICE INV-1"), "invoice")
        self.assertEqual(classify("SERVICES AGREEMENT"), "contract")

    def test_invoice_fields_extracted(self):
        result = extract(run_ocr(doc("inv-1001")))
        self.assertEqual(result["fields"]["vendor_name"],
                         "Northwind Supplies")
        self.assertEqual(result["fields"]["total"], 1987.20)
        self.assertEqual(len(result["fields"]["line_items"]), 2)

    def test_per_field_confidence_present(self):
        result = extract(run_ocr(doc("inv-1001")))
        self.assertIn("total", result["field_confidence"])
        self.assertGreater(result["field_confidence"]["total"], 0.5)


class ValidationTests(unittest.TestCase):
    def test_unknown_vendor_flagged(self):
        result = extract(run_ocr(doc("inv-1004")))
        validation = validate(result["doc_type"], result["fields"])
        fields = [i["field"] for i in validation["issues"]]
        self.assertIn("vendor_name", fields)
        self.assertFalse(validation["passed"])

    def test_total_anomaly_flagged(self):
        result = extract(run_ocr(doc("inv-1003")))
        validation = validate(result["doc_type"], result["fields"])
        kinds = [i["kind"] for i in validation["issues"]]
        self.assertIn("anomaly", kinds)

    def test_past_effective_date_flagged(self):
        result = extract(run_ocr(doc("con-2002")))
        validation = validate(result["doc_type"], result["fields"])
        fields = [i["field"] for i in validation["issues"]]
        self.assertIn("effective_date", fields)


class RoutingTests(unittest.TestCase):
    def test_clean_invoice_auto_approves(self):
        processor = Processor()
        record = processor.process(doc("inv-1001"))
        self.assertEqual(record["route"]["lane"], "auto_approve")

    def test_unknown_vendor_gets_detailed_review(self):
        processor = Processor()
        record = processor.process(doc("inv-1004"))
        self.assertEqual(record["route"]["lane"], "detailed_review")

    def test_correction_logged(self):
        processor = Processor()
        processor.process(doc("inv-1004"))
        entry = processor.review.correct(
            "inv-1004", "vendor_name", "Approved Vendor",
            "reviewer", "extraction_error")
        self.assertEqual(entry["original"], "Phantom Trading LLC")
        report = processor.review.feedback_report()
        self.assertEqual(report["total_corrections"], 1)


if __name__ == "__main__":
    unittest.main()
