"""TC-STORE: save/list/load/diff (isolated SCAN_DIR). TC-JOBS-UNIT: soft404 calibrate."""
import os
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler

import core.store as store
from core.jobs import JobEngine
from tests._helpers import start_server, stop_server
from tests.fixture_server import FixtureHandler


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = store.SCAN_DIR
        store.SCAN_DIR = self.tmp.name

    def tearDown(self):
        store.SCAN_DIR = self.old
        self.tmp.cleanup()

    def test_save_strips_secret(self):
        p = store.save_scan("https://h.test/", {"endpoints": [], "auth_secret": "pw"})
        self.assertTrue(os.path.isfile(p))
        import json
        with open(p, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertNotIn("auth_secret", saved)

    def test_list_load(self):
        store.save_scan("https://h.test/", {"endpoints": [{"url": "https://h.test/"}]})
        items = store.list_scans("h.test")
        self.assertEqual(len(items), 1)
        loaded = store.load_scan(items[0]["path"])
        self.assertEqual(loaded["endpoints"][0]["url"], "https://h.test/")

    def test_load_bad(self):
        self.assertEqual(store.load_scan("../evil"), {})
        self.assertEqual(store.load_scan("no/such.json"), {})

    def test_diff(self):
        a = {"endpoints": [{"url": u} for u in ["u1", "u2"]]}
        b = {"endpoints": [{"url": u} for u in ["u2", "u3"]]}
        d = store.diff_scans(a, b)
        self.assertEqual(d["new"], ["u3"])
        self.assertEqual(d["lost"], ["u1"])
        self.assertEqual((d["count_a"], d["count_b"]), (2, 2))


class CatchAll200(BaseHTTPRequestHandler):
    BODY = b"X" * 137

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.BODY)))
        self.end_headers()
        self.wfile.write(self.BODY)


class TestSoft404(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s200, _, cls.p200 = start_server(CatchAll200)
        cls.s404, _, cls.p404 = start_server(FixtureHandler)

    @classmethod
    def tearDownClass(cls):
        stop_server(cls.s200)
        stop_server(cls.s404)

    def _job(self, base, length):
        return {"target": base, "logs": [],
                "endpoints": {"k": {"url": base + "/ffufguess", "via": "ffuf",
                                    "status_anon": 200, "len_anon": length, "tags": []}}}

    def test_positive_tags_ffuf_hit(self):
        eng = JobEngine()
        base = f"http://127.0.0.1:{self.p200}"
        job = self._job(base, 137)
        eng._tag_soft404(job, {"proxy": ""})
        self.assertIn("soft404", job["endpoints"]["k"]["tags"])

    def test_negative_real_404(self):
        eng = JobEngine()
        base = f"http://127.0.0.1:{self.p404}"
        job = self._job(base, 0)
        eng._tag_soft404(job, {"proxy": ""})
        self.assertNotIn("soft404", job["endpoints"]["k"]["tags"])


if __name__ == "__main__":
    unittest.main()
