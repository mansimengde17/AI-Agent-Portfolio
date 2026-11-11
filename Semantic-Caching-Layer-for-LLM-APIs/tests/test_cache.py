import sys
import time
import unittest

sys.path.insert(0, "src")

from semcache.cache import SemanticCache, namespace_key
from semcache.policies import threshold_for, ttl_for


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = SemanticCache()
        self.ns = namespace_key("sys", "gpt-4o-mini", 0.0, None)
        self.response = {"usage": {"total_tokens": 100},
                         "choices": [{"finish_reason": "stop"}]}

    def test_semantically_similar_prompt_hits(self):
        self.cache.store("What is Python and what is it used for",
                         self.response, self.ns, "gpt-4o-mini", 3600)
        result = self.cache.lookup(
            "Explain what is Python and what is it used for",
            self.ns, threshold=0.80)
        self.assertTrue(result.hit)

    def test_different_system_prompt_never_shares(self):
        other_ns = namespace_key("other sys", "gpt-4o-mini", 0.0, None)
        self.cache.store("What is Python", self.response, self.ns,
                         "gpt-4o-mini", 3600)
        result = self.cache.lookup("What is Python", other_ns, threshold=0.5)
        self.assertFalse(result.hit)

    def test_ttl_expiry(self):
        self.cache.store("What is Python", self.response, self.ns,
                         "gpt-4o-mini", ttl_s=0.01)
        time.sleep(0.02)
        result = self.cache.lookup("What is Python", self.ns, threshold=0.9)
        self.assertFalse(result.hit)
        self.assertEqual(self.cache.evict_expired(), 1)

    def test_invalidate_by_model(self):
        self.cache.store("a question", self.response, self.ns, "gpt-4o", 3600)
        self.cache.store("b question", self.response, self.ns,
                         "gpt-4o-mini", 3600)
        self.assertEqual(self.cache.invalidate(model="gpt-4o"), 1)
        self.assertEqual(self.cache.size, 1)

    def test_policies(self):
        self.assertIsNone(ttl_for("Write a poem about the sea"))
        self.assertEqual(ttl_for("What is the latest news"), 3600.0)
        self.assertEqual(ttl_for("What is a database index"), 86400.0)
        self.assertEqual(threshold_for("Classify this email"), 0.90)
        self.assertEqual(threshold_for("What is a mutex"), 0.95)


if __name__ == "__main__":
    unittest.main()
