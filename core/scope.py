"""Scope helpers: pure functions, no network."""
from __future__ import annotations
import ipaddress
from urllib.parse import urlparse
from config import OUT_OF_SCOPE_HOSTS


def norm_target(raw: str) -> str:
    t = (raw or "").strip()
    if not t:
        return ""
    if not t.startswith(("http://", "https://")):
        t = "https://" + t
    u = urlparse(t)
    if not u.netloc:
        return ""
    return f"{u.scheme}://{u.netloc}"


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def registrable(host: str) -> str:
    """Naive rdn: last 2 labels (good enough for scope guard, no deps).
    IP literals (v4/v6) match exactly (no rdn logic, no :port split)."""
    h = (host or "").lower().strip().strip("[]").split("%")[0]
    if _is_ip(h):
        return h
    h = h.split(":")[0]  # drop :port for DNS names only
    parts = [p for p in h.split(".") if p]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return h


def in_scope(url: str, target: str) -> bool:
    try:
        tu, uu = urlparse(target), urlparse(url)
    except Exception:
        return False
    if uu.scheme not in ("http", "https"):
        return False
    if not uu.netloc:
        return False
    low = url.lower()
    if any(h in low for h in OUT_OF_SCOPE_HOSTS):
        return False
    # IP targets: exact service only (host:port). Junk archives for 127.0.0.1:80
    # must not pollute a scan of 127.0.0.1:8899.
    if _is_ip((tu.hostname or "")):
        return (uu.netloc or "").lower() == (tu.netloc or "").lower()
    # domains: keep same registrable domain (allows www/sub merge, drops foreign)
    return registrable(uu.hostname or "") == registrable(tu.hostname or "")


def norm_url(url: str) -> str:
    """Dedup ?a=1 vs ?a=2 -> keep path + sorted param NAMES only."""
    try:
        u = urlparse(url.split("#")[0])
    except Exception:
        return url
    if not u.query:
        return f"{u.scheme}://{u.netloc}{u.path or '/'}"
    names = sorted({kv.split("=")[0] for kv in u.query.split("&") if kv})
    q = "&".join(f"{n}=X" for n in names if n)
    return f"{u.scheme}://{u.netloc}{u.path or '/'}?{q}" if q else f"{u.scheme}://{u.netloc}{u.path or '/'}"
