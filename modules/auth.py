"""Auth-session: login once (CSRF-aware) + check session. Memory-only, never disk."""
from __future__ import annotations
import re
import urllib.parse
from core.http import fetch

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def do_login(login_url: str, user: str, pwd: str, proxy: str = "") -> dict:
    """Single POST, fetch CSRF token once. No brute-force."""
    if not HAS_REQUESTS:
        return {"ok": False, "msg": "requests lib missing"}
    try:
        proxies = None
        if proxy:
            px = proxy if "://" in proxy else "http://" + proxy
            proxies = {"http": px, "https": px}
        s = requests.Session()
        s.verify = False
        s.headers.update({"User-Agent": "Mozilla/5.0 Recon-Map/2.0"})
        # 1. GET login page for CSRF token
        token = ""
        try:
            g = s.get(login_url, timeout=12, proxies=proxies)
            m = re.search(r'name=["\'](?:csrf|_token|authenticity_token)["\']\s+value=["\']([^"\']+)', g.text)
            if m:
                token = m.group(1)
        except Exception:
            pass
        # 2. POST once with common field names
        data = {"username": user, "user": user, "email": user,
                "password": pwd, "pass": pwd}
        if token:
            data["csrf"] = token
            data["_token"] = token
        r = s.post(login_url, data=data, timeout=12, allow_redirects=True, proxies=proxies)
        cookie = "; ".join(f"{c.name}={c.value}" for c in s.cookies)[:2000]
        ok = bool(cookie) and r.status_code < 400
        return {"ok": ok, "cookie": cookie, "status": r.status_code,
                "msg": "login POST done" if ok else f"login got {r.status_code} (check fields manually)"}
    except Exception as e:
        return {"ok": False, "msg": str(e)[:200]}


def check_session(target: str, auth: dict, proxy: str = "") -> dict:
    """GET /my-account: username/logout present vs 302->login."""
    probe = target.rstrip("/") + "/my-account"
    r = fetch(probe, timeout=10, auth=auth, proxy=proxy)
    body = (r.get("body") or "")[:20000].lower()
    status = r.get("status", 0)
    if status == 0:
        return {"ok": False, "logged_in": False, "msg": "probe failed: " + str(r.get("error", ""))[:120]}
    if status in (301, 302) or "/login" in str(r.get("final", "")).lower():
        if "logout" not in body and (auth or {}).get("user", "") not in body:
            return {"ok": True, "logged_in": False, "status": status,
                    "msg": "session invalid (redirect to login)"}
    user = (auth or {}).get("user", "")
    logged = ("logout" in body) or (user and user.lower() in body)
    return {"ok": True, "logged_in": bool(logged), "status": status,
            "msg": f"logged-in as {user}" if logged else "no login marker (paste cookie manually)"}
