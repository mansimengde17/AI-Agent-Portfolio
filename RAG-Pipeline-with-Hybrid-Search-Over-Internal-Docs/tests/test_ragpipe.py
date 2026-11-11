import sys
import unittest

sys.path.insert(0, "src")

from ragpipe.generate import generate
from ragpipe.index import HybridIndex, embed
from ragpipe.ingest import chunk_structural, dedupe
from ragpipe.retrieve import retrieve, rrf_fuse

DOC = """# Guide

## Error codes

Error E1001 means the API key is missing. Error E1002 means the key is revoked.

## Limits

The rate limit is 100 requests per second and returns HTTP 429 when exceeded.
"""


class RagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = HybridIndex()
        cls.index.add(chunk_structural("guide.md", DOC))

    def test_sparse_finds_exact_identifier(self):
        results = self.index.sparse("What does E1001 mean?")
        self.assertTrue(results)
        self.assertIn("E1001", self.index.chunks[results[0][0]].text)

    def test_rrf_prefers_agreement(self):
        fused = rrf_fuse([(0, 0.9), (1, 0.5)], [(0, 5.0), (2, 1.0)])
        self.assertGreater(fused[0], fused[1])
        self.assertGreater(fused[0], fused[2])

    def test_answer_with_verified_citation(self):
        retrieved = retrieve(self.index, "What does error E1001 mean?")
        answer = generate("What does error E1001 mean?", retrieved)
        self.assertTrue(answer.answered)
        self.assertIn("[1]", answer.text)
        self.assertTrue(all(c.verified for c in answer.citations))

    def test_refuses_when_not_in_corpus(self):
        retrieved = retrieve(self.index, "What is the vacation policy?")
        answer = generate("What is the vacation policy?", retrieved)
        self.assertFalse(answer.answered)

    def test_dedupe_drops_near_duplicates(self):
        chunks = chunk_structural("a.md", DOC) + chunk_structural("b.md", DOC)
        kept, dropped = dedupe(chunks, embed)
        self.assertEqual(dropped, len(chunks) // 2)


if __name__ == "__main__":
    unittest.main()
