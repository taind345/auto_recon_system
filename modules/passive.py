"""M2 passive: crt.sh + wayback + gau (robots/sitemap included). OFF in exam/fast."""
from __future__ import annotations
import json
import re
import urllib.request
from urllib.parse import urlparse
from core.scope import in_scope


def _get(url: str, timeout: int = 15) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return r.read().decode("utf-8", "ignore")[:200_000]
    except Exception:
        return ""


def run(ctx: dict) -> dict:
    if not ctx["profile_cfg"].get("passive"):
        return {"subdomains": [], "urls": [], "msg": "passive OFF (profile)"}
    target = ctx["target"]
    host = urlparse(target).hostname or ""
    timeout = 15
    subs: set[str] = set()
    urls: set[str] = set()
    # crt.sh
    try:
        raw = _get(f"https://crt.sh/?q=%25.{host}&output=json", timeout)
        for row in json.loads(raw or "[]")[:100]:
            name = (row.get("name_value") or "")
            for s in name.splitlines():
                s = s.strip().lower()
                if s and "*" not in s:
                    subs.add(s)
    except Exception:
        pass
    # waybackurls-style CDX
    try:
        raw = _get(f"https://web.archive.org/cdx/search/cdx?url={host}/*&output=text&fl=original&collapse=urlkey&limit=200",
                   timeout)
        for line in raw.splitlines()[:200]:
            u = line.strip()
            if u.startswith(("http://", "https://")) and in_scope(u, target):
                urls.add(u.split("#")[0])
    except Exception:
        pass
    # robots + sitemap (live, safe)
    from core.http import fetch
    for extra in ("/robots.txt", "/sitemap.xml", "/security.txt"):
        r = fetch(target + extra, timeout=10)
        if r.get("status") == 200:
            urls.add(target + extra)
            for m in re.findall(r"https?://[^\s\"'<>]+", r.get("body", ""))[:50]:
                if in_scope(m, target):
                    urls.add(m)
    alive = [u for u in sorted(urls)][: ctx["limits"].get("passive_urls", 60)]
    return {"subdomains": sorted(subs)[:100], "urls": alive,
            "msg": f"passive: {len(subs)} subs, {len(alive)} urls"}
