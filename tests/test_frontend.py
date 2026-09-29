"""TC-FRONTEND (static): every JS-referenced DOM id exists; i18n keys complete + VI/EN parity."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


class TestFrontendStatic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = read("static", "js", "app.js")
        cls.html = read("index.html")
        cls.i18n = read("static", "js", "i18n.js")

    def test_ids_exist(self):
        used = set(re.findall(r'\$\("#([\w-]+)"\)', self.js))
        used |= set(re.findall(r'getElementById\("([\w-]+)"\)', self.js))
        defined = set(re.findall(r'id="([\w-]+)"', self.html))
        defined |= set(re.findall(r'id="([\w-]+)"', self.js))  # created dynamically
        missing = sorted(u for u in used if u not in defined)
        self.assertEqual(missing, [], f"JS ids missing in HTML: {missing}")

    def test_i18n_keys_exist(self):
        used = set(re.findall(r'\bT\("([\w_]+)"\)', self.js))
        used |= set(re.findall(r'data-i18n(?:-ph)?="([\w_]+)"', self.html))
        used |= {"tab_" + t for t in ["info", "js", "hrefs", "forms", "diff", "raw", "burp"]}
        for lang in ("vi", "en"):
            for k in sorted(used):
                self.assertIn(f"{k}:", self.i18n, f"key {k} missing for {lang}")

    def test_i18n_parity(self):
        blocks = {}
        for lang in ("vi", "en"):
            m = re.search(lang + r":\{(.*?)\n\}", self.i18n, re.S)
            self.assertIsNotNone(m, f"lang block {lang} not found")
            blocks[lang] = set(re.findall(r"(\w+):\"", m.group(1)))
        self.assertEqual(blocks["vi"], blocks["en"],
                         f"VI/EN drift: {blocks['vi'] ^ blocks['en']}")

    def test_static_refs(self):
        for ref in ("/static/css/app.css", "/static/js/i18n.js", "/static/js/app.js"):
            self.assertIn(ref, self.html)


if __name__ == "__main__":
    unittest.main()
