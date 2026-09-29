"""TC-WORDLIST: bundled lists valid, tier resolve, ext sanitize."""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from modules import brute


def ctx(**kw):
    d = {"profile_cfg": {"ffuf_wordlist": "small"}, "proxy": ""}
    d.update(kw)
    return d


class TestBundled(unittest.TestCase):
    def _check(self, name, minimum):
        p = os.path.join(ROOT, "words", name)
        self.assertTrue(os.path.isfile(p), name)
        lines = [l for l in open(p, encoding="utf-8").read().splitlines() if l.strip()]
        self.assertGreaterEqual(len(lines), minimum, name)
        for w in lines:
            self.assertFalse(w.startswith("/"), f"leading slash: {w}")
            self.assertNotIn(" ", w)
            self.assertLessEqual(len(w), 64)

    def test_small(self):
        self._check("small.txt", 100)

    def test_medium(self):
        self._check("medium.txt", 800)


class TestResolve(unittest.TestCase):
    def test_small_bundled(self):
        p, label = brute.wordlist_for(ctx())
        self.assertTrue(p.endswith("words/small.txt"))
        self.assertTrue(os.path.isfile(p))

    def test_large_seclists_or_fallback(self):
        p, label = brute.wordlist_for(ctx(wordlist="large"))
        self.assertTrue(os.path.isfile(p))
        self.assertTrue(label.startswith("seclists:") or label.endswith(".txt"))

    def test_custom_missing_falls_back(self):
        p, _ = brute.wordlist_for(ctx(wordlist="custom", custom_wl_path="/no/such"))
        self.assertTrue(os.path.isfile(p))

    def test_extensions(self):
        self.assertEqual(brute.extensions_for(ctx()), ".bak,.old,.json,.js")
        self.assertEqual(brute.extensions_for(ctx(extensions=".PHP, .bak,,xx!toolongext")),
                         ".php,.bak")
        self.assertEqual(brute.extensions_for(ctx(extensions=",,,")),
                         ".bak,.old,.json,.js")


if __name__ == "__main__":
    unittest.main()
