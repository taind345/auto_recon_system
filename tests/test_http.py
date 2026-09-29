"""TC-HTTP: truthful redirect status, auth attach, fail-soft proxy. Needs fixture."""
import unittest
from core.http import fetch, auth_headers, has_credential, proxies_for
from tests._helpers import start_server, stop_server
from tests.fixture_server import FixtureHandler, SESS


class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.th, cls.port = start_server(FixtureHandler)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        stop_server(cls.srv)

    def test_200(self):
        d = fetch(self.base + "/public", timeout=8)
        self.assertEqual(d["status"], 200)
        self.assertIn("window.location", d["body"])

    def test_truthful_302(self):
        d = fetch(self.base + "/my-account", timeout=8)
        self.assertEqual(d["status"], 302)  # must NOT be laundered to 200
        self.assertIn("/login", d.get("location", ""))

    def test_auth_cookie_200(self):
        d = fetch(self.base + "/my-account", timeout=8,
                  auth={"mode": "cookie", "cookie": SESS})
        self.assertEqual(d["status"], 200)
        self.assertIn("logout", d["body"])

    def test_dead_proxy_failsoft(self):
        d = fetch(self.base + "/", timeout=8, proxy="127.0.0.1:9")
        self.assertEqual(d["status"], 0)
        self.assertIn("error", d)

    def test_auth_headers(self):
        self.assertEqual(auth_headers(None)["User-Agent"][:7], "Mozilla")
        self.assertIn("Cookie", auth_headers({"mode": "cookie", "cookie": "a=1"}))
        self.assertIn("Authorization", auth_headers({"mode": "bearer", "bearer": "t"}))
        self.assertNotIn("Cookie", auth_headers({"mode": "login", "session_cookie": ""}))

    def test_has_credential(self):
        self.assertFalse(has_credential(None))
        self.assertFalse(has_credential({"mode": "cookie", "cookie": ""}))
        self.assertTrue(has_credential({"mode": "cookie", "cookie": "a=1"}))
        self.assertTrue(has_credential({"mode": "login", "session_cookie": "s=1"}))

    def test_proxies_for(self):
        self.assertIsNone(proxies_for(""))
        self.assertEqual(proxies_for("127.0.0.1:8080")["http"], "http://127.0.0.1:8080")


if __name__ == "__main__":
    unittest.main()
