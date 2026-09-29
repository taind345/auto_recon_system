"""JobEngine: async 8-module pipeline, progress streaming, cancel, fail-soft."""
from __future__ import annotations
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from config import LIMITS, PROFILES, MODULES
from core.http import fetch, has_credential
from core.parse import parse_html, classify, score_endpoint
from core.scope import in_scope, norm_url
from core.store import save_scan
from modules import ports as m_ports, passive as m_passive, crawl as m_crawl
from modules import brute as m_brute, params_js as m_pjs, tech as m_tech


def _mod_state(state="queued", pct=0, msg="", count=0) -> dict:
    return {"state": state, "pct": pct, "msg": msg, "count": count}


class JobEngine:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    # -- public API --
    def create(self, target: str, profile: str, auth: dict, proxy: str,
               opts: dict | None = None) -> str:
        jid = uuid.uuid4().hex[:10]
        profile = profile if profile in PROFILES else "exam"
        opts = opts or {}
        tier = opts.get("wordlist") if opts.get("wordlist") in ("small", "medium", "large", "custom") else None
        custom_path = self._store_custom_words(jid, opts.get("custom_words") or [])
        job = {
            "id": jid, "target": target, "profile": profile,
            "profile_cfg": dict(PROFILES[profile]), "limits": dict(LIMITS),
            "wordlist": tier, "custom_wl_path": custom_path,
            "extensions": str(opts.get("extensions") or "")[:200],
            "auth": {k: v for k, v in (auth or {}).items() if k != "pass"},
            "auth_secret": (auth or {}).get("pass", ""),
            "auth_session": None,  # memory-only: {mode, cookie/bearer, user}
            "proxy": (proxy or "").strip(),
            "status": "running", "created": time.time(), "finished": 0,
            "cancel_flag": False,
            "modules": {m: _mod_state() for m, _, _ in MODULES},
            "endpoints": {},  # norm_url -> ep record
            "subdomains": [], "ports": [], "js_apis": [], "secrets": [],
            "tech": {}, "ws": [], "auth_check": {}, "notes": {},
            "logs": [], "home": {}, "counts": {},
            "save_path": "",
        }
        # build auth_session (memory only)
        mode = (auth or {}).get("mode", "off")
        if mode == "cookie" and (auth or {}).get("cookie"):
            job["auth_session"] = {"mode": "cookie", "cookie": auth["cookie"],
                                   "user": (auth or {}).get("user", "")}
        elif mode == "bearer" and (auth or {}).get("bearer"):
            job["auth_session"] = {"mode": "bearer", "bearer": auth["bearer"],
                                   "user": (auth or {}).get("user", "")}
        elif mode == "login":
            job["auth_session"] = {"mode": "login",
                                   "session_cookie": (auth or {}).get("session_cookie", ""),
                                   "user": (auth or {}).get("user", "")}
        with self._lock:
            self._jobs[jid] = job
        t = threading.Thread(target=self._run, args=(jid,), daemon=True)
        t.start()
        return jid

    @staticmethod
    def _store_custom_words(jid: str, words) -> str:
        """Persist uploaded wordlist to a temp file (deleted in _finish)."""
        import tempfile
        lines: list[str] = []
        for w in (words or [])[: LIMITS.get("custom_wl_lines", 5000)]:
            w = str(w or "").strip().lstrip("/")[:128]
            if w and " " not in w and w not in lines:
                lines.append(w)
        if not lines:
            return ""
        try:
            fd, path = tempfile.mkstemp(prefix=f"ar_wl_{jid}_", suffix=".txt")
            with open(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            return path
        except OSError:
            return ""

    def get(self, jid: str) -> dict | None:
        with self._lock:
            return self._jobs.get(jid)

    def cancel(self, jid: str) -> bool:
        with self._lock:
            j = self._jobs.get(jid)
            if not j:
                return False
            j["cancel_flag"] = True
            j["status"] = "cancelled"
            return True

    # -- internals --
    def _log(self, job: dict, msg: str) -> None:
        ts = time.strftime("%H:%M:%S")
        with self._lock:
            job["logs"].append(f"[{ts}] {msg}")
            job["logs"] = job["logs"][-120:]

    def _setmod(self, job: dict, name: str, **kw) -> None:
        with self._lock:
            job["modules"][name].update(kw)

    def _cancelled(self, job: dict) -> bool:
        return bool(job.get("cancel_flag"))

    def _ensure_ep(self, job: dict, url: str, via: str) -> dict | None:
        url = (url or "").strip().split("#")[0]
        if not url or url.startswith(("javascript:", "mailto:", "data:")):
            return None
        if url.startswith("/"):
            url = job["target"] + url
        if not in_scope(url, job["target"]):
            return None
        key = norm_url(url)
        eps = job["endpoints"]
        if key not in eps:
            if len(eps) >= job["limits"]["urls"]:
                return None
            path = urlparse(url).path or "/"
            eps[key] = {"url": url, "path": path, "status_anon": 0, "status_auth": 0,
                        "len_anon": 0, "len_auth": 0, "via": via, "tags": classify(url),
                        "method": "GET",
                        "params": [], "js_files": [], "hrefs": [], "forms": [],
                        "headers": {}, "has_location_js": False, "sink_inline": False,
                        "location": "", "score": 0,
                        "final_url": url, "_inline": []}
        return eps[key]

    def _mark_post_forms(self, job: dict, page_url: str, forms: list) -> None:
        """A POST form targeting URL X means X accepts POST (method chip)."""
        from urllib.parse import urljoin as _uj
        for f in forms or []:
            try:
                if (f.get("method") or "GET").upper() != "POST":
                    continue
                action = f.get("action") or page_url
                tgt = self._ensure_ep(job, _uj(page_url, action), "form")
                if tgt is not None and tgt.get("method") == "GET":
                    tgt["method"] = "POST"
            except Exception:
                continue

    def _run(self, jid: str) -> None:
        job = self.get(jid)
        if not job:
            return
        ctx = {"target": job["target"], "profile_cfg": job["profile_cfg"],
               "limits": job["limits"], "proxy": job["proxy"],
               "auth_session": job.get("auth_session"),
               "wordlist": job.get("wordlist"), "custom_wl_path": job.get("custom_wl_path", ""),
               "extensions": job.get("extensions", ""),
               "cancel": lambda: self._cancelled(job)}
        target, has_auth = job["target"], has_credential(job.get("auth_session"))
        self._log(job, f"scan start {target} profile={job['profile']} auth={'on' if has_auth else 'off'}")

        # Phase 0: home fetch (baseline for soft-404 + tech)
        home = fetch(target, timeout=ctx["limits"]["fetch_s"], proxy=ctx["proxy"])
        job["home"] = {"status": home.get("status", 0), "len": home.get("len", 0),
                       "headers": home.get("headers", {}), "body": (home.get("body", "") or "")[:20000]}
        self._ensure_ep(job, target, "input")

        # Phase 1: ports + passive + crawl_anon in parallel
        self._setmod(job, "ports", state="running", pct=10)
        self._setmod(job, "passive", state="running", pct=10)
        self._setmod(job, "crawl_anon", state="running", pct=5)
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_ports = ex.submit(self._safe, job, "ports", m_ports.run, ctx)
            f_pas = ex.submit(self._safe, job, "passive", m_passive.run, ctx)
            f_crawl = ex.submit(self._safe, job, "crawl_anon", m_crawl.run, ctx, False)
            r_ports = f_ports.result()
            r_pas = f_pas.result()
            r_crawl = f_crawl.result()
        job["ports"] = r_ports.get("ports", [])
        self._setmod(job, "ports", state="done", pct=100,
                     msg=r_ports.get("msg", ""), count=len(job["ports"]))
        job["subdomains"] = r_pas.get("subdomains", [])
        # merge order matters: active enum first (katana), passive last, so the
        # URL cap never evicts real findings in favour of archive junk.
        for u in r_crawl.get("urls", []) + r_crawl.get("queued", []):
            self._ensure_ep(job, u, "katana")
        for u in r_pas.get("urls", []):
            self._ensure_ep(job, u, "passive")
        self._setmod(job, "passive", state="done" if r_pas.get("subdomains") or r_pas.get("urls") else "skipped",
                     pct=100, msg=r_pas.get("msg", ""), count=len(job["subdomains"]) + len(r_pas.get("urls", [])))
        # merge crawl enrichment (anon statuses)
        self._merge_enrich(job, r_crawl.get("enriched", {}), authed=False)
        self._setmod(job, "crawl_anon", state="done", pct=100,
                     msg=r_crawl.get("msg", ""), count=len(r_crawl.get("urls", [])))
        self._log(job, f"phase1: ports={len(job['ports'])} subs={len(job['subdomains'])} eps={len(job['endpoints'])}")
        if self._cancelled(job):
            return self._finish(job, cancelled=True)

        # Phase 2: crawl_auth (only if session) + brute in parallel
        if has_auth:
            self._setmod(job, "crawl_auth", state="running", pct=10)
        else:
            self._setmod(job, "crawl_auth", state="skipped", pct=100, msg="auth off")
        self._setmod(job, "brute", state="running", pct=10)
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_auth = ex.submit(self._safe_auth_crawl, job, ctx) if has_auth else None
            f_brute = ex.submit(self._safe, job, "brute", m_brute.run, ctx)
            r_auth = f_auth.result() if f_auth else {}
            r_brute = f_brute.result()
        if has_auth and r_auth:
            for u in r_auth.get("urls", []) + r_auth.get("queued", []):
                self._ensure_ep(job, u, "katana-auth")
            self._merge_enrich(job, r_auth.get("enriched", {}), authed=True)
            n_authonly = sum(1 for e in job["endpoints"].values() if "auth-only" in e.get("tags", []))
            self._setmod(job, "crawl_auth", state="done", pct=100,
                         msg=f"{r_auth.get('msg','')} (+{n_authonly} auth-only)", count=len(r_auth.get("urls", [])))
        for h in r_brute.get("hits", []):
            self._ensure_ep(job, h, "ffuf")
        self._setmod(job, "brute", state="done", pct=100,
                     msg=r_brute.get("msg", ""), count=len(r_brute.get("hits", [])))
        if self._cancelled(job):
            return self._finish(job, cancelled=True)

        # Phase 3: enrich statuses for endpoints lacking them (bounded, threaded)
        self._fill_statuses(job, ctx)
        self._tag_soft404(job, ctx)
        # Phase 4: params + js + tech
        self._setmod(job, "params", state="running", pct=30)
        self._setmod(job, "js", state="running", pct=20)
        rp = m_pjs.run_params(job["endpoints"])
        self._setmod(job, "params", state="done", pct=100, msg=rp["msg"], count=rp["inputs"])
        rj = m_pjs.run_js(ctx, job["endpoints"])
        job["js_apis"], job["secrets"], job["ws"] = rj["apis"], rj["secrets"], rj["ws"]
        self._setmod(job, "js", state="done", pct=100, msg=rj["msg"], count=rj["files"])
        # re-run params now that JS bodies arrived (cheap, pure)
        rp2 = m_pjs.run_params(job["endpoints"])
        # score + auth-only tagging (302/401/403 anon but 200 auth)
        for ep in job["endpoints"].values():
            sa, su = ep.get("status_auth", 0), ep.get("status_anon", 0)
            if (has_auth and su in (301, 302, 303, 307, 308, 401, 403, 0)
                    and sa == 200 and "auth-only" not in ep["tags"]):
                ep["tags"].append("auth-only")
            ep["score"] = score_endpoint(ep)
        self._setmod(job, "tech", state="running", pct=40)
        rt = m_tech.run(ctx, job["endpoints"], job["home"].get("headers", {}), job["home"].get("body", ""))
        job["tech"] = rt
        self._setmod(job, "tech", state="done", pct=100, msg=rt["msg"], count=len(rt.get("files", [])))
        self._log(job, f"phase3: eps={len(job['endpoints'])} params={rp2['inputs']} js={rj['files']}")
        self._finish(job)

    def _safe(self, job: dict, mod: str, fn, *a) -> dict:
        try:
            return fn(*a) or {}
        except Exception as e:  # fail-soft: scan continues
            self._setmod(job, mod, state="fail", pct=100, msg=str(e)[:160])
            self._log(job, f"{mod} FAIL: {e}"[:200])
            return {}

    def _safe_auth_crawl(self, job: dict, ctx: dict) -> dict:
        try:
            return m_crawl.run(ctx, authed=True) or {}
        except Exception as e:
            self._setmod(job, "crawl_auth", state="fail", pct=100, msg=str(e)[:160])
            return {}

    def _merge_enrich(self, job: dict, enriched: dict, authed: bool) -> None:
        """Merge crawl data using truthful first-status. Non-200 pages keep
        status + Location only (never inherit the redirect target's forms)."""
        for url, info in enriched.items():
            ep = self._ensure_ep(job, url, "katana-auth" if authed else "katana")
            if not ep:
                continue
            st = info.get("status", 0)
            if authed:
                ep["status_auth"] = st
                ep["len_auth"] = info.get("raw_len", 0)
            else:
                ep["status_anon"] = st
                ep["len_anon"] = info.get("raw_len", 0)
            ep["location"] = info.get("location", "")
            ep["final_url"] = info.get("final_url", url)
            if st != 200:
                continue
            ep["hrefs"] = info.get("hrefs", [])[:20]
            ep["forms"] = info.get("forms", [])[:5]
            self._mark_post_forms(job, url, ep["forms"])
            for j in info.get("js_files", []):
                if j not in ep["js_files"]:
                    ep["js_files"].append(j)
            if info.get("sink_inline"):
                ep["sink_inline"] = True
                ep["has_location_js"] = True
                if "client-redirect" not in ep["tags"]:
                    ep["tags"].append("client-redirect")
            ep["headers"] = info.get("headers", {})
            ep["_inline"] = info.get("inline", [])

    def _fill_statuses(self, job: dict, ctx: dict) -> None:
        """Status fill via fetch for eps missing it (bounded threads).
        Parses hrefs/forms only from HTTP 200 bodies."""
        todo = [e for e in job["endpoints"].values()
                if not e.get("status_anon") and not (e["url"].endswith((".jpg", ".png", ".svg", ".css", ".ico")))]
        todo = todo[:60]
        if not todo:
            return
        has_auth = has_credential(job.get("auth_session"))

        def one(ep: dict) -> None:
            if self._cancelled(job):
                return
            d = fetch(ep["url"], timeout=8, proxy=ctx["proxy"])
            ep["status_anon"] = d.get("status", 0)
            ep["len_anon"] = d.get("len", 0)
            ep["location"] = d.get("location", "")
            ep["final_url"] = d.get("final", ep["url"])
            if d.get("status") == 200 and d.get("body"):
                p = parse_html(ep["url"], d["body"])
                if not ep["hrefs"]:
                    ep["hrefs"] = p["hrefs"][:20]
                if not ep["forms"]:
                    ep["forms"] = p["forms"][:5]
                    self._mark_post_forms(job, ep["url"], ep["forms"])
                if not ep["_inline"]:
                    ep["_inline"] = p["inline"][:3]
            if has_auth:
                d2 = fetch(ep["url"], timeout=8, auth=job["auth_session"], proxy=ctx["proxy"])
                ep["status_auth"] = d2.get("status", 0)
                ep["len_auth"] = d2.get("len", 0)

        with ThreadPoolExecutor(max_workers=min(ctx["profile_cfg"].get("threads", 10), 20)) as ex:
            list(ex.map(one, todo))

    def _soft404_len(self, job: dict, ctx: dict) -> int | None:
        """Fetch 2 random non-existent paths. If both 200 with equal len,
        that's the soft-404 signature length (else None)."""
        import random
        import string
        lens: set[int] = set()
        for _ in range(2):
            rnd = "".join(random.choice(string.ascii_lowercase) for _ in range(14))
            d = fetch(job["target"].rstrip("/") + f"/{rnd}.html",
                      timeout=8, proxy=ctx["proxy"])
            if d.get("status") == 200:
                lens.add(d.get("len", 0))
            else:
                return None
        return lens.pop() if len(lens) == 1 else None

    def _tag_soft404(self, job: dict, ctx: dict) -> None:
        try:
            sig = self._soft404_len(job, ctx)
        except Exception:
            return
        if sig is None:
            return
        n = 0
        for ep in job["endpoints"].values():
            if (ep.get("via") == "ffuf" and ep.get("status_anon") == 200
                    and ep.get("len_anon") == sig and "soft404" not in ep["tags"]):
                ep["tags"].append("soft404")
                n += 1
        if n:
            self._log(job, f"soft-404 calibrate: {n} ffuf hits tagged (len={sig})")

    def _finish(self, job: dict, cancelled: bool = False) -> None:
        # custom wordlist temp file: remove, never keep uploads on disk
        try:
            if job.get("custom_wl_path"):
                os.remove(job["custom_wl_path"])
        except OSError:
            pass
        with self._lock:
            job["status"] = "cancelled" if cancelled else "done"
            job["finished"] = time.time()
            for m, s in job["modules"].items():
                if s["state"] in ("running", "queued"):
                    s.update(state="skipped", pct=100)
            # counts for progress bar
            eps = list(job["endpoints"].values())
            job["counts"] = {"endpoints": len(eps),
                             "auth_only": sum(1 for e in eps if "auth-only" in e.get("tags", [])),
                             "params": sum(len(e.get("params", [])) for e in eps),
                             "js": sum(len(e.get("js_files", [])) for e in eps),
                             "ports": len(job.get("ports", [])),
                             "subdomains": len(job.get("subdomains", []))}
        # persist (strip _private keys + secrets: never store bodies/inline)
        try:
            clean = [{k: v for k, v in e.items() if not k.startswith("_")}
                     for e in job["endpoints"].values()][: LIMITS["urls"]]
            payload = {"target": job["target"], "profile": job["profile"],
                       "endpoints": clean,
                       "ports": job.get("ports", []), "subdomains": job.get("subdomains", []),
                       "tech": job.get("tech", {}), "counts": job.get("counts", {}),
                       "auth_user": (job.get("auth_session") or {}).get("user", "")}
            job["save_path"] = save_scan(job["target"], payload)
        except Exception:
            pass
        self._log(job, "cancelled" if cancelled else f"done: {len(job['endpoints'])} endpoints -> {job['save_path']}")

    # -- result builders (frozen cats) --
    def result(self, jid: str, cat: str) -> dict:
        job = self.get(jid)
        if not job:
            return {"error": "unknown job"}
        eps = sorted(job["endpoints"].values(), key=lambda e: (-e.get("score", 0), e.get("url", "")))
        if cat == "endpoints":
            return {"items": [{k: v for k, v in e.items() if not k.startswith("_")} for e in eps]}
        if cat == "params":
            rows = []
            for e in eps:
                for p in e.get("params", []):
                    rows.append({"endpoint": e["url"], **p})
            return {"items": rows}
        if cat == "js":
            return {"items": [{"url": e["url"], "js_files": e.get("js_files", []),
                               "has_location_js": e.get("has_location_js", False)} for e in eps if e.get("js_files")],
                    "apis": job.get("js_apis", []), "secrets": job.get("secrets", []),
                    "ws": job.get("ws", [])}
        if cat == "ports":
            return {"items": job.get("ports", [])}
        if cat == "subdomains":
            return {"items": job.get("subdomains", [])}
        if cat == "tech":
            return {"items": job.get("tech", {})}
        if cat == "auth":
            auth_only = [e["url"] for e in eps if "auth-only" in e.get("tags", [])]
            return {"items": {"session": job.get("auth_check", {}),
                              "user": (job.get("auth_session") or {}).get("user", ""),
                              "mode": (job.get("auth_session") or {}).get("mode", "off"),
                              "auth_only": auth_only,
                              "matrix": [{k: v for k, v in e.items() if not k.startswith("_")}
                                         for e in eps if e.get("status_auth") or "auth-only" in e.get("tags", [])][:100]}}
        if cat == "notes":
            return {"items": job.get("notes", {})}
        # overview
        edges = []
        for e in eps[:80]:
            for j in e.get("js_files", [])[:3]:
                edges.append({"from": e["url"], "to": j, "kind": "page->js"})
        for a in (job.get("js_apis") or [])[:40]:
            edges.append({"from": "js", "to": a, "kind": "js->api"})
        home_safe = {k: v for k, v in job.get("home", {}).items() if k != "body"}
        return {"items": {"target": job["target"], "profile": job["profile"],
                          "counts": job.get("counts", {}), "home": home_safe,
                          "graph": edges,
                          "top": [{k: v for k, v in e.items() if not k.startswith("_")}
                                  for e in eps[:15]]}}
