"""TC-API: full scan flows against fixture (anon / cookie / login / misc).

Slow (~2-4 min): real nmap/katana/ffuf when installed; asserts tolerate
missing binaries via /api/health gates.
"""
import unittest

import app as appmod
import core.store as store
from tests._helpers import start_server, stop_server, api, wait_done
from tests.fixture_server import FixtureHandler, SESS


class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fsrv, _, cls.fport = start_server(FixtureHandler)
        cls.t = f"http://127.0.0.1:{cls.fport}"
        cls.asrv, _, cls.aport = start_server(appmod.Handler)
        cls.base = f"http://127.0.0.1:{cls.aport}"
        import tempfile
        cls._tmp = tempfile.TemporaryDirectory()
        cls._old = store.SCAN_DIR
        store.SCAN_DIR = cls._tmp.name
        h = api(cls.base, "/api/health")
        cls.HAS_FFUF = h.get("ffuf")

    @classmethod
    def tearDownClass(cls):
        stop_server(cls.fsrv)
        stop_server(cls.asrv)
        store.SCAN_DIR = cls._old
        cls._tmp.cleanup()

    def _scan(self, profile="fast", auth=None, proxy=""):
        r = api(self.base, "/api/scan",
                {"target": self.t, "profile": profile,
                 "auth": auth or {"mode": "off"}, "proxy": proxy})
        self.assertIn("job_id", r)
        return r["job_id"]

    def _eps(self, job):
        return api(self.base, f"/api/result?job={job}&cat=endpoints")["items"]

    # -- health / contract --
    def test_01_health(self):
        h = api(self.base, "/api/health")
        self.assertTrue(h["ok"])
        self.assertEqual(h["schema"], 2)

    def test_02_scan_requires_target(self):
        import urllib.request, urllib.error, json
        req = urllib.request.Request(self.base + "/api/scan", data=b"{}",
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code, 400)

    # -- anon scan --
    def test_03_fast_anon(self):
        job = self._scan()
        prog = wait_done(self.base, job)
        self.assertEqual(prog["status"], "done")
        eps = {e["url"]: e for e in self._eps(job)}
        for u in (self.t, self.t + "/login", self.t + "/s.js",
                  self.t + "/api/data", self.t + "/my-account"):
            self.assertIn(u, eps, f"missing {u}")
        acct = eps[self.t + "/my-account"]
        self.assertEqual(acct["status_anon"], 302)  # truthful, not laundered
        self.assertNotIn("auth-only", acct["tags"])
        names = {p["name"] for e in eps.values() for p in e["params"]}
        self.assertIn("returnPath", names)
        redir = [p for e in eps.values() for p in e["params"] if p["redirect_candidate"]]
        self.assertTrue(redir)
        js = api(self.base, f"/api/result?job={job}&cat=js")
        self.assertTrue(any("api/data" in a for a in js["apis"]))
        sec = [s for s in js["secrets"] if s["kind"] == "aws_key"]
        self.assertTrue(sec and "..." in sec[0]["masked"])
        tech = api(self.base, f"/api/result?job={job}&cat=tech")["items"]
        self.assertTrue(any("robots" in f["path"] for f in tech["files"]))

    # -- cookie auth scan --
    def test_04_cookie_auth_matrix(self):
        job = self._scan(auth={"mode": "cookie", "cookie": SESS, "user": "wiener"})
        wait_done(self.base, job)
        a = api(self.base, f"/api/result?job={job}&cat=auth")["items"]
        self.assertEqual(a["mode"], "cookie")
        self.assertIn(self.t + "/my-account", a["auth_only"])
        self.assertIn(self.t + "/my-account/change-email", a["auth_only"])
        m = {e["url"]: e for e in a["matrix"]}
        self.assertEqual((m[self.t + "/my-account"]["status_anon"],
                          m[self.t + "/my-account"]["status_auth"]), (302, 200))

    # -- check-session + login scan --
    def test_05_check_session(self):
        good = api(self.base, "/api/check-session",
                   {"target": self.t, "auth": {"mode": "cookie", "cookie": SESS, "user": "wiener"}})
        self.assertTrue(good["logged_in"])
        bad = api(self.base, "/api/check-session",
                  {"target": self.t, "auth": {"mode": "cookie", "cookie": "nope", "user": "x"}})
        self.assertFalse(bad["logged_in"])
        login = api(self.base, "/api/check-session",
                    {"target": self.t, "auth": {"mode": "login",
                                                "login_url": self.t + "/login",
                                                "user": "wiener", "pass": "peter"}})
        self.assertTrue(login["logged_in"])
        self.assertTrue(login.get("session_cookie"))
        wrong = api(self.base, "/api/check-session",
                    {"target": self.t, "auth": {"mode": "login",
                                                "login_url": self.t + "/login",
                                                "user": "wiener", "pass": "wrong"}})
        self.assertFalse(wrong["ok"])
        return login.get("session_cookie", "")

    def test_06_login_scan(self):
        sc = api(self.base, "/api/check-session",
                 {"target": self.t, "auth": {"mode": "login",
                                             "login_url": self.t + "/login",
                                             "user": "wiener", "pass": "peter"}})["session_cookie"]
        job = self._scan(auth={"mode": "login", "user": "wiener", "session_cookie": sc})
        wait_done(self.base, job)
        a = api(self.base, f"/api/result?job={job}&cat=auth")["items"]
        self.assertEqual(a["mode"], "login")
        self.assertIn(self.t + "/my-account", a["auth_only"])

    # -- misc APIs --
    def test_07_note_scans_diff_fetch(self):
        job = self._scan()
        wait_done(self.base, job)
        self.assertTrue(api(self.base, "/api/note",
                            {"job": job, "url": self.t + "/public", "text": "n1"})["ok"])
        notes = api(self.base, f"/api/result?job={job}&cat=notes")["items"]
        self.assertEqual(notes.get(self.t + "/public"), "n1")
        scans = api(self.base, "/api/scans")["items"]
        self.assertTrue(len(scans) >= 1)
        d = api(self.base, f"/api/diff?a={scans[0]['path']}&b={scans[0]['path']}")
        self.assertEqual((d["new"], d["lost"]), ([], []))
        f = api(self.base, f"/api/fetch?url={self.t}/my-account")
        self.assertEqual(f["status"], 302)
        self.assertIn("/login", f.get("location", ""))

    def test_08_cancel(self):
        job = self._scan(profile="exam")
        import time
        time.sleep(2)
        self.assertTrue(api(self.base, "/api/cancel", {"job_id": job})["ok"])
        prog = wait_done(self.base, job, timeout=120)
        self.assertIn(prog["status"], ("cancelled", "done"))

    def test_09_brute_hits_when_ffuf(self):
        if not self.HAS_FFUF:
            self.skipTest("ffuf missing")
        job = self._scan()
        wait_done(self.base, job)
        eps = {e["url"] for e in self._eps(job)}
        self.assertIn(self.t + "/login", eps)

    def _send(self, job, raw, use_session=True):
        return api(self.base, "/api/send",
                   {"job": job, "raw": raw, "use_session": use_session})

    def test_10_repeater(self):
        job = self._scan(auth={"mode": "cookie", "cookie": SESS, "user": "wiener"})
        wait_done(self.base, job)
        host = f"127.0.0.1:{self.fport}"
        get_pub = f"GET /public HTTP/1.1\nHost: {host}\nUser-Agent: t\nConnection: close"
        r = self._send(job, get_pub)
        self.assertEqual(r["status"], 200)
        self.assertIn("window.location", r["body"])
        self.assertGreaterEqual(r["ms"], 0)
        # truthful 302 without session, 200 with session
        get_acct = f"GET /my-account HTTP/1.1\nHost: {host}\nConnection: close"
        anon = self._send(job, get_acct, use_session=False)
        self.assertEqual(anon["status"], 302)
        self.assertIn("/login", anon.get("location", ""))
        authed = self._send(job, get_acct, use_session=True)
        self.assertEqual(authed["status"], 200)
        # POST login works through the repeater
        post = (f"POST /login HTTP/1.1\nHost: {host}\nContent-Type: application/x-www-form-urlencoded\n"
                f"Content-Length: 32\n\nusername=wiener&password=peter")
        self.assertEqual(self._send(job, post, use_session=False)["status"], 302)
        # guards
        oos = self._send(job, "GET / HTTP/1.1\nHost: evil.com\n\n")
        self.assertIn("error", oos)
        bad = self._send(job, "FROB / HTTP/1.1\nHost: %s\n\n" % host)
        self.assertIn("error", bad)
        nohost = self._send(job, "GET / HTTP/1.1\nUser-Agent: t\n\n")
        self.assertIn("error", nohost)
        big = self._send(job, f"GET / HTTP/1.1\nHost: {host}\n\n" + "A" * 60000)
        self.assertIn("error", big)
        ghost = api(self.base, "/api/send", {"job": "nope", "raw": get_pub})
        self.assertIn("error", ghost)


if __name__ == "__main__":
    unittest.main()
