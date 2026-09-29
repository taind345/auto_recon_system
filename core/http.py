"""HTTP fetch: single place for timeout/proxy/auth-headers/verify=False.

Truthful redirect handling: records FIRST status + Location (so anon 302 vs
auth 200 diffs work), then follows up to 3 hops manually for the body.
Never raises (fail-soft).
"""
from __future__ import annotations
import urllib.error
import urllib.request
from typing import Optional
from urllib.parse import urljoin

try:
    import requests  # preinstalled on Kali
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

UA = "Mozilla/5.0 Recon-Map/2.0 (enum-only; OSCP-safe)"
MAX_HOPS = 3


def auth_headers(auth: Optional[dict] = None) -> dict:
    h = {"User-Agent": UA}
    if not auth or auth.get("mode", "off") == "off":
        return h
    mode = auth.get("mode")
    if mode == "cookie" and auth.get("cookie"):
        h["Cookie"] = auth["cookie"]
    elif mode == "bearer" and auth.get("bearer"):
        h["Authorization"] = f"Bearer {auth['bearer']}"
    elif mode == "login" and auth.get("session_cookie"):
        h["Cookie"] = auth["session_cookie"]
    return h


def has_credential(auth: Optional[dict] = None) -> bool:
    """True when auth session actually carries something to send."""
    if not auth or auth.get("mode", "off") == "off":
        return False
    return bool(auth.get("cookie") or auth.get("bearer") or auth.get("session_cookie"))


def proxies_for(proxy: str = "") -> Optional[dict]:
    if not proxy:
        return None
    if "://" not in proxy:
        proxy = "http://" + proxy
    return {"http": proxy, "https": proxy}


def _blank(url: str, err: str = "") -> dict:
    d = {"url": url, "final": url, "status": 0, "location": "",
         "headers": {}, "body": "", "len": 0}
    if err:
        d["error"] = err[:300]
    return d


def fetch(url: str, timeout: int = 12, auth: Optional[dict] = None,
          proxy: str = "", max_body: int = 200_000) -> dict:
    """Fail-soft fetch. Returns {url,final,status,location,headers,body,len(,error)}.

    status = FIRST response status (302 stays 302). body = FINAL page body.
    """
    headers = auth_headers(auth)
    if not HAS_REQUESTS:
        return _urllib_fetch(url, timeout, headers, max_body)
    try:
        proxies = proxies_for(proxy)
        cur = url
        first_status, first_headers, location = 0, {}, ""
        body, final = "", url
        for _ in range(MAX_HOPS + 1):
            r = requests.get(cur, timeout=timeout, verify=False,
                             headers=headers, allow_redirects=False,
                             proxies=proxies)
            if first_status == 0:
                first_status = r.status_code
                first_headers = dict(list(r.headers.items())[:30])
            if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
                location = location or r.headers["Location"][:500]
                cur = urljoin(cur, r.headers["Location"])
                final = cur
                continue
            body = r.text[:max_body] if isinstance(r.text, str) else ""
            final = cur
            break
        else:
            body = ""
        return {"url": url, "final": final, "status": first_status or 200,
                "location": location, "headers": first_headers,
                "body": body, "len": len(body)}
    except Exception as e:  # noqa: BLE001 - fail-soft is the contract
        return _blank(url, str(e))


def _urllib_fetch(url: str, timeout: int, headers: dict, max_body: int) -> dict:
    class _NoRedir(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, hdrs, newurl):  # noqa: N802
            return None

    try:
        opener = urllib.request.build_opener(_NoRedir)
        req = urllib.request.Request(url, headers=headers)
        try:
            with opener.open(req, timeout=timeout) as r:
                raw = r.read()[:max_body].decode("utf-8", "ignore")
                return {"url": url, "final": r.geturl(), "status": getattr(r, "status", 200),
                        "location": "", "headers": {}, "body": raw, "len": len(raw)}
        except urllib.error.HTTPError as e:
            loc = (e.headers.get("Location") or "")[:500] if e.headers else ""
            return {"url": url, "final": url, "status": e.code, "location": loc,
                    "headers": {}, "body": "", "len": 0}
    except Exception as e:
        return _blank(url, str(e))


METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD")
# hop-by-hop / auto headers never forwarded from a pasted raw request
DROP_HEADERS = frozenset({
    "connection", "proxy-connection", "keep-alive", "transfer-encoding",
    "content-length", "upgrade", "te", "trailer",
})


def parse_raw_request(raw: str) -> dict:
    """Parse Burp-style raw HTTP text -> {method, path, headers, body}.

    Raises ValueError on malformed input. Never executes anything.
    """
    text = (raw or "").replace("\r\n", "\n").strip("\n")
    if not text or len(text) > 20000:
        raise ValueError("empty or oversized request (max 20KB)")
    head, _, body = text.partition("\n\n")
    lines = head.split("\n")
    parts = lines[0].split()
    if len(parts) < 2:
        raise ValueError("bad request line (need: METHOD /path HTTP/1.1)")
    method = parts[0].upper()
    if method not in METHODS:
        raise ValueError(f"method not allowed: {method}")
    path = parts[1][:2000]
    if not path.startswith("/"):
        raise ValueError("path must start with / (no absolute-URI / CONNECT)")
    headers: dict[str, str] = {}
    for ln in lines[1:]:
        if not ln.strip():
            continue
        if ":" not in ln:
            raise ValueError(f"bad header line: {ln[:60]}")
        k, v = ln.split(":", 1)
        k = k.strip()
        if not k or len(k) > 100:
            raise ValueError(f"bad header name: {k[:60]}")
        if k.lower() in DROP_HEADERS:
            continue
        headers[k] = v.strip()[:2000]
    if "Host" not in headers:
        raise ValueError("missing Host header")
    if len(body) > 50000:
        raise ValueError("body too large (max 50KB)")
    return {"method": method, "path": path, "headers": headers, "body": body}
