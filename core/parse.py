"""Pure parsers: (url, body) -> dict. No network inside (unit-testable)."""
from __future__ import annotations
import re
from urllib.parse import urlparse, parse_qsl
from config import REDIRECT_HINTS, INTEREST_HINTS, SECRET_RES

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

JS_PARAM_RES = [
    re.compile(r'searchParams\.get\(\s*["\']([^"\']+)["\']'),
    re.compile(r'urlParams\.get\(\s*["\']([^"\']+)["\']'),
    re.compile(r'\.get\(\s*["\'](postId|next|url|redirect|return\w*|returnPath)["\']'),
    re.compile(r'decodeURIComponent\([^)]*\)'),
]
FETCH_RE = re.compile(r'(?:fetch|axios\.(?:get|post)|XMLHttpRequest|\.ajax)\s*\(\s*["\'`]([^"\'`]{1,200})["\'`]')
LOCATION_RE = re.compile(r'window\.location|document\.location|location\.href|location\.search|redirectOn\w+')
HREF_RE = re.compile(r'href="([^"]{1,300})"')
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src="([^"]{1,300})"')
WS_RE = re.compile(r'\bws[s]?://[^\s"\'<>]{1,120}')
GRAPHQL_HINT = re.compile(r'/graphql|__schema|introspection', re.I)


def mask(v: str) -> str:
    """Evidence hygiene: show head...tail only."""
    v = v or ""
    if len(v) <= 10:
        return v[:2] + "***"
    return v[:4] + "..." + v[-3:]


def parse_html(base: str, body: str) -> dict:
    out = {"hrefs": [], "scripts": [], "forms": [], "inline": []}
    if not body:
        return out
    if HAS_BS4:
        try:
            soup = BeautifulSoup(body, "html.parser")
            for a in soup.find_all("a", href=True):
                out["hrefs"].append(a["href"][:300])
            for f in soup.find_all("form"):
                out["forms"].append({
                    "action": (f.get("action") or "")[:300],
                    "method": (f.get("method") or "GET").upper(),
                    "inputs": [(i.get("name") or "") for i in
                               f.find_all(["input", "textarea", "select"]) if i.get("name")][:20],
                })
            for s in soup.find_all("script", src=True):
                out["scripts"].append(s["src"][:300])
            for s in soup.find_all("script", src=False):
                t = (s.string or "")[:5000]
                if t.strip():
                    out["inline"].append(t[:2000])
            return out
        except Exception:
            pass
    out["hrefs"] = HREF_RE.findall(body)[:50]
    out["scripts"] = SCRIPT_SRC_RE.findall(body)[:20]
    return out


def mine_params(url: str, forms: list, inline: list, js_bodies: list) -> list:
    found: dict[str, str] = {}
    try:
        for k, _ in parse_qsl(urlparse(url).query):
            found[k] = "query"
    except Exception:
        pass
    for f in forms or []:
        for n in f.get("inputs", []):
            found.setdefault(n, "form:" + f.get("method", "GET"))
    blob = "\n".join(inline or []) + "\n" + "\n".join((js_bodies or [])[:5])
    if blob.strip():
        for rx in JS_PARAM_RES[:3]:
            for m in rx.findall(blob):
                if isinstance(m, str) and 1 <= len(m) <= 40:
                    found.setdefault(m, "js")
        for m in re.findall(r'[?&]([a-zA-Z_][a-zA-Z0-9_]{1,30})=', blob):
            found.setdefault(m, "js")
    return [{"name": k, "via": v,
             "redirect_candidate": k in REDIRECT_HINTS or k.lower() in REDIRECT_HINTS}
            for k, v in sorted(found.items())]


def extract_js_api(js_body: str) -> dict:
    """Endpoints + sinks found inside one JS file."""
    if not js_body:
        return {"apis": [], "has_location": False, "ws": [], "graphql": False}
    return {
        "apis": sorted(set(FETCH_RE.findall(js_body)))[:30],
        "has_location": bool(LOCATION_RE.search(js_body)),
        "ws": sorted(set(WS_RE.findall(js_body)))[:10],
        "graphql": bool(GRAPHQL_HINT.search(js_body)),
    }


def find_secrets(blob: str, where: str) -> list:
    hits = []
    for kind, pat in SECRET_RES:
        try:
            for m in re.findall(pat, blob or "")[:5]:
                s = m if isinstance(m, str) else str(m)
                hits.append({"kind": kind, "file": where, "masked": mask(s)})
        except Exception:
            continue
    return hits


def fingerprint(headers: dict, body: str) -> dict:
    h = {k.lower(): v for k, v in (headers or {}).items()}
    tech: list[str] = []
    srv = h.get("server", "")
    if srv:
        tech.append(f"Server:{srv[:60]}")
    if h.get("x-powered-by"):
        tech.append(f"Powered:{h['x-powered-by'][:60]}")
    blob = (body or "")[:20000]
    for needle, name in (("wp-content", "WordPress"), ("__next", "Next.js"),
                         ("X-AspNet", "ASP.NET"), ("django", "Django"),
                         ("laravel", "Laravel"), ("_nuxt", "Nuxt"),
                         ("wp-json", "WP-REST"), ("csrf", "CSRF-token")):
        if needle.lower() in blob.lower() or needle.lower() in str(h).lower():
            tech.append(name)
    # header audit (enum-only, no exploit)
    cookies = h.get("set-cookie", "")
    cookie_flags = {
        "secure": "secure" in cookies.lower(),
        "httponly": "httponly" in cookies.lower(),
        "samesite": "samesite" in cookies.lower(),
    }
    return {"tech": sorted(set(tech))[:10],
            "hsts": "strict-transport-security" in h,
            "generator": h.get("x-generator", ""),
            "cookie_flags": cookie_flags}


def classify(url: str) -> list:
    u = urlparse(url)
    low = url.lower()
    tags: list[str] = []
    if any(h in low for h in INTEREST_HINTS):
        tags.append("interesting")
    if u.query:
        tags.append("has-params")
    if u.path.endswith(".js"):
        tags.append("js")
    if "/api" in u.path or u.path.startswith("/api"):
        tags.append("api")
    if "/admin" in u.path:
        tags.append("admin")
    return tags


def score_endpoint(ep: dict) -> int:
    """Heuristic sort only (never a vuln verdict). Inline DOM sink scores
    higher than a sink merely inherited from an included JS file."""
    s = 0
    tags = ep.get("tags", [])
    if "auth-only" in tags:
        s += 10
    if ep.get("sink_inline"):
        s += 10
    elif ep.get("has_location_js"):
        s += 4
    if any(p.get("redirect_candidate") for p in ep.get("params", [])):
        s += 8
    if "api" in tags or "admin" in tags:
        s += 5
    if ep.get("params"):
        s += 3
    return min(s, 100)
