"""TC-PARSE: pure parsers — html, params, js-api, secrets, fingerprint, score."""
import unittest
from core import parse as P

HTML = """<html><head><script src="/s.js"></script></head><body>
<a href="/login">l</a><a href="https://evil.com/x">e</a>
<form action="/go" method="post"><input name="u"><input name="p" type="password"></form>
<script>const r=new URLSearchParams(location.search).get('next');</script>
</body></html>"""
JS = """fetch("/api/data"); const w=new WebSocket("wss://h.test/s");
if(x){window.location=y;} const k="AKIAIOSFODNN7EXAMPLE";"""


class TestParseHtml(unittest.TestCase):
    def test_hrefs_scripts_forms(self):
        o = P.parse_html("https://h.test/", HTML)
        self.assertIn("/login", o["hrefs"])
        self.assertIn("/s.js", o["scripts"])
        self.assertEqual(o["forms"][0]["action"], "/go")
        self.assertIn("u", o["forms"][0]["inputs"])

    def test_empty(self):
        self.assertEqual(P.parse_html("https://h.test/", "")["hrefs"], [])


class TestMineParams(unittest.TestCase):
    def test_query_form_js(self):
        forms = [{"action": "/go", "method": "POST", "inputs": ["u"]}]
        out = P.mine_params("https://h.test/p?a=1", forms, ["u.get('next')"], [])
        by = {p["name"]: p for p in out}
        self.assertEqual(by["a"]["via"], "query")
        self.assertEqual(by["u"]["via"], "form:POST")
        self.assertEqual(by["next"]["via"], "js")

    def test_redirect_candidate(self):
        out = P.mine_params("https://h.test/?returnPath=1", [], [], [])
        self.assertTrue(out[0]["redirect_candidate"])
        out2 = P.mine_params("https://h.test/?q=1", [], [], [])
        self.assertFalse(out2[0]["redirect_candidate"])


class TestJsApi(unittest.TestCase):
    def test_extract(self):
        o = P.extract_js_api(JS)
        self.assertIn("/api/data", o["apis"])
        self.assertTrue(o["has_location"])
        self.assertTrue(o["ws"])
        self.assertFalse(o["graphql"])


class TestSecrets(unittest.TestCase):
    def test_masked(self):
        hits = P.find_secrets(JS, "s.js")
        aws = [h for h in hits if h["kind"] == "aws_key"]
        self.assertEqual(len(aws), 1)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", aws[0]["masked"])
        self.assertTrue(aws[0]["masked"].startswith("AKIA"))

    def test_mask_short(self):
        self.assertEqual(P.mask("ab"), "ab***")


class TestFingerprint(unittest.TestCase):
    def test_headers(self):
        fp = P.fingerprint({"Server": "Apache", "Strict-Transport-Security": "max",
                            "Set-Cookie": "a=1; Secure; HttpOnly; SameSite=Lax"}, "")
        self.assertTrue(fp["hsts"])
        self.assertTrue(all(fp["cookie_flags"].values()))

    def test_tech_regex(self):
        fp = P.fingerprint({}, "wp-content foo")
        self.assertIn("WordPress", fp["tech"])


class TestClassifyScore(unittest.TestCase):
    def test_classify(self):
        self.assertIn("api", P.classify("https://h.test/api/x"))
        self.assertIn("js", P.classify("https://h.test/a.js"))
        self.assertIn("has-params", P.classify("https://h.test/a?b=1"))

    def test_score_inline_beats_inherited(self):
        inline = {"tags": [], "params": [], "sink_inline": True, "has_location_js": True}
        inherit = {"tags": [], "params": [], "sink_inline": False, "has_location_js": True}
        self.assertGreater(P.score_endpoint(inline), P.score_endpoint(inherit))

    def test_score_cap(self):
        ep = {"tags": ["auth-only", "api"], "sink_inline": True,
              "params": [{"redirect_candidate": True}]}
        self.assertLessEqual(P.score_endpoint(ep), 100)


if __name__ == "__main__":
    unittest.main()
