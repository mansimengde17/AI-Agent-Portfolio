import sys
import unittest

sys.path.insert(0, "src")

from selfheal.code_parser import parse_source
from selfheal.diff_detector import detect_changes
from selfheal.doc_parser import parse_markdown
from selfheal.linker import LinkGraph
from selfheal.repair import repair
from selfheal.staleness import verify

OLD = "def connect(host, port=8080, retries=3):\n    'Connect.'\n    return host\n"
NEW = "def connect(host, port=9090, max_retries=3):\n    'Connect.'\n    return host\n"
DOC = ("# API\n\n## Connecting\n\nCall `connect` with `retries` (default 3)."
       " The `port` defaults to 8080.\n")


class SelfHealTests(unittest.TestCase):
    def setUp(self):
        self.old_chunks = parse_source("m.py", OLD)
        self.new_chunks = parse_source("m.py", NEW)
        self.sections = parse_markdown("docs/api.md", DOC)
        self.changes = detect_changes(self.old_chunks, self.new_chunks)

    def test_signature_change_detected(self):
        self.assertEqual(len(self.changes), 1)
        self.assertEqual(self.changes[0].change_type, "signature")
        self.assertIn("retries -> max_retries", self.changes[0].detail)

    def test_link_graph_by_name_mention(self):
        graph = LinkGraph().build(self.new_chunks, self.sections)
        links = graph.sections_for_chunk("m.py::connect")
        self.assertTrue(any(l.reason == "name_mention" for l in links))

    def test_staleness_verified(self):
        section = [s for s in self.sections if "Connecting" in s.heading_path][0]
        finding = verify(self.changes[0], section)
        self.assertTrue(finding.stale)
        self.assertTrue(any("retries" in p for p in finding.problems))

    def test_repair_renames_and_updates_default(self):
        section = [s for s in self.sections if "Connecting" in s.heading_path][0]
        finding = verify(self.changes[0], section)
        fix = repair(self.changes[0], section, finding)
        self.assertIn("`max_retries`", fix.corrected)
        self.assertNotIn("`retries`", fix.corrected)
        self.assertIn("9090", fix.corrected)

    def test_comment_only_change_is_ignored(self):
        changed = OLD.replace("'Connect.'", "'Connect.'  # comment")
        changes = detect_changes(self.old_chunks, parse_source("m.py", changed))
        self.assertEqual(changes, [])


if __name__ == "__main__":
    unittest.main()
