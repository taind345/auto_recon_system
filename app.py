#!/usr/bin/env python3
"""AUTO_RECON v2 — enum-only, OSCP-safe, offline-first.

Usage: python3 app.py [port]   ->  http://127.0.0.1:8000
Routes only (logic lives in core/ + modules/). See PLAN-v2.en.md frozen contract.
"""
from __future__ import annotations
import json
import mimetypes
import os
import shutil
import time
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from config import SCHEMA
from core.scope import norm_target, in_scope
from core.http import fetch, HAS_REQUESTS, has_credential, parse_raw_request, proxies_for
from core.parse import HAS_BS4
from core.jobs import JobEngine
from core.store import list_scans, load_scan, diff_scans
from modules import auth as m_auth

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE = JobEngine()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet; telemetry lives in job logs
        pass

    # -- helpers --
    def _json(self, obj, code: int = 200) -> None:
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body_json(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n <= 0 or n > 1_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _static(self, rel: str) -> bool:
        """Serve index.html + static/ offline (no CDN). Returns True if handled."""
        safe = rel.lstrip("/")
        if safe in ("", "index.html"):
            safe = "index.html"
        elif not safe.startswith("static/"):
            return False
        if ".." in safe:
            return False
        path = os.path.join(APP_DIR, safe)
        if not os.path.isfile(path):
            return False
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        try:
            with open(path, "rb") as f:
                b = f.read()
        except OSError:
            return False
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b)
        return True

    # -- GET --
    def do_GET(self):  # noqa: C901 (route table, kept flat on purpose)
        u = urlparse(self.path)
        q = parse_qs(u.query)

        if u.path in ("/", "/index.html") or u.path.startswith("/static/"):
            if self._static(u.path):
                return
            self._json({"error": "not found"}, 404)
            return

        if u.path == "/api/health":
            self._json({"ok": True, "schema": SCHEMA, "has_requests": HAS_REQUESTS,
                        "has_bs4": HAS_BS4,
                        "katana": shutil.which("katana") is not None,
                        "ffuf": shutil.which("ffuf") is not None,
                        "nmap": shutil.which("nmap") is not None})
            return

        if u.path == "/api/progress":
            job = ENGINE.get((q.get("job") or [""])[0])
            if not job:
                self._json({"error": "unknown job"}, 404)
                return
            mods = job["modules"]
            pct = int(sum(m.get("pct", 0) for m in mods.values()) / max(len(mods), 1))
            self._json({"job": job["id"], "status": job["status"], "pct": pct,
                        "modules": mods, "counts": job.get("counts", {}),
                        "logs": job["logs"][-50:], "target": job["target"]})
            return

        if u.path == "/api/result":
            jid = (q.get("job") or [""])[0]
            cat = (q.get("cat") or ["endpoints"])[0]
            self._json(ENGINE.result(jid, cat))
            return

        if u.path == "/api/fetch":
            url = (q.get("url") or [""])[0]
            if not url.startswith(("http://", "https://")):
                self._json({"error": "need ?url=http(s)://..."}, 400)
                return
            d = fetch(url, timeout=12)
            d["body"] = d.get("body", "")[:50_000]
            # never leak session: fetch here is always anon
            self._json(d)
            return

        if u.path == "/api/scans":
            host = (q.get("host") or [""])[0]
            self._json({"items": list_scans(host)})
            return

        if u.path == "/api/diff":
            a = load_scan((q.get("a") or [""])[0])
            b = load_scan((q.get("b") or [""])[0])
            self._json(diff_scans(a, b))
            return

        self._json({"error": "not found"}, 404)

    # -- POST --
    def do_POST(self):  # noqa: C901
        u = urlparse(self.path)

        if u.path == "/api/scan":
            req = self._body_json()
            target = norm_target(req.get("target", ""))
            if not target:
                self._json({"error": "missing target"}, 400)
                return
            profile = req.get("profile", "exam")
            auth = req.get("auth", {"mode": "off"}) or {"mode": "off"}
            proxy = (req.get("proxy") or "").strip()
            jid = ENGINE.create(target, profile, auth, proxy)
            self._json({"job_id": jid, "schema": SCHEMA})
            return

        if u.path == "/api/cancel":
            req = self._body_json()
            ok = ENGINE.cancel(req.get("job_id", "") or req.get("job", ""))
            self._json({"ok": ok})
            return

        if u.path == "/api/check-session":
            req = self._body_json()
            target = norm_target(req.get("target", ""))
            auth = req.get("auth", {}) or {}
            proxy = (req.get("proxy") or "").strip()
            mode = auth.get("mode", "off")
            session = None
            if mode == "login" and not auth.get("login_url"):
                self._json({"ok": False, "msg": "login needs login_url + user + pass"})
                return
            if mode == "login" and auth.get("login_url"):
                r = m_auth.do_login(auth["login_url"], auth.get("user", ""),
                                    auth.get("pass", ""), proxy)
                if r.get("ok"):
                    session = {"mode": "login", "session_cookie": r["cookie"],
                               "user": auth.get("user", "")}
                else:
                    self._json({"ok": False, **r})
                    return
            elif mode == "cookie":
                session = {"mode": "cookie", "cookie": auth.get("cookie", ""),
                           "user": auth.get("user", "")}
            elif mode == "bearer":
                session = {"mode": "bearer", "bearer": auth.get("bearer", ""),
                           "user": auth.get("user", "")}
            else:
                self._json({"ok": False, "msg": "auth off"})
                return
            res = m_auth.check_session(target, session, proxy)
            # stash into job if provided (so crawl_auth picks it up on retry)
            jid = req.get("job", "")
            job = ENGINE.get(jid) if jid else None
            if job and res.get("logged_in"):
                job["auth_session"] = session
                job["auth_check"] = res
            # redact cookie in logs but return session_cookie to the caller:
            # it's their own session and the scan job needs it for crawl_auth.
            safe = {**res, "cookie_set": bool(session.get("cookie") or session.get("session_cookie"))}
            if session.get("session_cookie"):
                safe["session_cookie"] = session["session_cookie"]
            self._json({"ok": res.get("ok", False), **safe})
            return

        if u.path == "/api/note":
            req = self._body_json()
            job = ENGINE.get(req.get("job", ""))
            if not job:
                self._json({"error": "unknown job"}, 404)
                return
            job["notes"][req.get("url", "")] = req.get("text", "")[:2000]
            self._json({"ok": True})
            return

        if u.path == "/api/send":
            self._handle_send()
            return

        self._json({"error": "not found"}, 404)

    def _handle_send(self) -> None:
        """Manual repeater: send one user-edited raw request, return raw response.

        Guardrails: needs a scan job (scope = job target, in_scope enforced),
        method whitelist + size caps in parse_raw_request, 15s timeout,
        no redirect follow (truthful status), session attached only from the
        job's memory-only auth_session and only when asked.
        """
        req = self._body_json()
        job = ENGINE.get(req.get("job", ""))
        if not job:
            self._json({"error": "unknown job (scan first)"}, 404)
            return
        try:
            rq = parse_raw_request(req.get("raw", ""))
        except ValueError as e:
            self._json({"error": str(e)[:200]}, 400)
            return
        scheme = (urlparse(job["target"]).scheme or "https")
        url = f"{scheme}://{rq['headers']['Host']}{rq['path']}"
        if not in_scope(url, job["target"]):
            self._json({"error": "out of scope for this job"}, 403)
            return
        headers = dict(rq["headers"])
        headers.setdefault("User-Agent", "Mozilla/5.0 Recon-Map/2.0")
        if req.get("use_session") and has_credential(job.get("auth_session")):
            sess = job["auth_session"]
            if sess.get("mode") == "bearer" and sess.get("bearer"):
                headers.setdefault("Authorization", f"Bearer {sess['bearer']}")
            else:
                ck = sess.get("cookie") or sess.get("session_cookie") or ""
                if ck:
                    headers.setdefault("Cookie", ck)
        t0 = time.time()
        try:
            if HAS_REQUESTS:
                import requests
                r = requests.request(rq["method"], url, headers=headers,
                                     data=rq["body"].encode() if rq["body"] else None,
                                     timeout=15, verify=False, allow_redirects=False,
                                     proxies=proxies_for(job.get("proxy", "")))
                body = r.text[:50000] if isinstance(r.text, str) else ""
                self._json({"status": r.status_code, "headers": dict(list(r.headers.items())[:30]),
                            "body": body, "len": len(body), "ms": int((time.time() - t0) * 1000),
                            "final": url, "location": r.headers.get("Location", "")[:500]})
            else:
                import urllib.request
                data = rq["body"].encode() if rq["body"] else None
                q2 = urllib.request.Request(url, data=data, headers=headers, method=rq["method"])
                try:
                    with urllib.request.urlopen(q2, timeout=15) as r:  # noqa: S310 (local lab tool)
                        raw = r.read()[:50000].decode("utf-8", "ignore")
                        self._json({"status": getattr(r, "status", 200), "headers": {},
                                    "body": raw, "len": len(raw),
                                    "ms": int((time.time() - t0) * 1000),
                                    "final": url, "location": ""})
                except urllib.error.HTTPError as e:
                    raw = e.read()[:50000].decode("utf-8", "ignore") if e.fp else ""
                    self._json({"status": e.code, "headers": {}, "body": raw, "len": len(raw),
                                "ms": int((time.time() - t0) * 1000), "final": url,
                                "location": (e.headers.get("Location") or "")[:500] if e.headers else ""})
        except Exception as e:  # fail-soft: show the error as the "response"
            self._json({"status": 0, "headers": {}, "body": "", "len": 0,
                        "ms": int((time.time() - t0) * 1000), "final": url,
                        "error": str(e)[:300]})


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"AUTO_RECON v2 (schema {SCHEMA}) on http://127.0.0.1:{port}  [{APP_DIR}]")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
