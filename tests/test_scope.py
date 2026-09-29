"""TC-SCOPE: target norm, rdn guard, IP exact-service guard, OOS hosts."""
import unittest
from core.scope import norm_target, registrable, in_scope, norm_url


class TestNormTarget(unittest.TestCase):
    def test_bare_domain_gets_https(self):
        self.assertEqual(norm_target("example.com"), "https://example.com")

    def test_keeps_scheme_path_stripped(self):
        self.assertEqual(norm_target("http://a.test/x?y=1"), "http://a.test")

    def test_empty(self):
        self.assertEqual(norm_target("  "), "")


class TestRegistrable(unittest.TestCase):
    def test_subdomain(self):
        self.assertEqual(registrable("www.example.com"), "example.com")

    def test_ip_literal_exact(self):
        self.assertEqual(registrable("127.0.0.1"), "127.0.0.1")

    def test_ipv6(self):
        self.assertEqual(registrable("::1"), "::1")


class TestInScope(unittest.TestCase):
    T = "https://portal.test/"

    def test_same_and_sub(self):
        self.assertTrue(in_scope("https://portal.test/a", self.T))
        self.assertTrue(in_scope("https://sub.portal.test/a", self.T))

    def test_foreign(self):
        self.assertFalse(in_scope("https://evil.com/a", self.T))

    def test_oos_hosts(self):
        self.assertFalse(in_scope("https://exploit-server.net/x", self.T))
        self.assertFalse(in_scope("https://www.w3.org/x", self.T))

    def test_non_http(self):
        self.assertFalse(in_scope("javascript:alert(1)", self.T))
        self.assertFalse(in_scope("ftp://portal.test/x", self.T))

    def test_ip_exact_service(self):
        t = "http://127.0.0.1:8899"
        self.assertTrue(in_scope("http://127.0.0.1:8899/a", t))
        self.assertFalse(in_scope("http://127.0.0.1:80/a", t))  # other service
        self.assertFalse(in_scope("http://127.0.0.2:8899/a", t))


class TestNormUrl(unittest.TestCase):
    def test_dedup_values(self):
        self.assertEqual(norm_url("https://h.test/p?a=1&b=2"), norm_url("https://h.test/p?b=9&a=8"))

    def test_drops_fragment(self):
        self.assertEqual(norm_url("https://h.test/p#x"), "https://h.test/p")


if __name__ == "__main__":
    unittest.main()
