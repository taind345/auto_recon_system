"""M8 tech & files: headers fingerprint + known files + OPTIONS + cookie/HSTS audit."""
from __future__ import annotations
from core.http import fetch
from core.parse import fingerprint

KNOWN = ["/robots.txt", "/sitemap.xml", "/security.txt", "/openapi.json",
         "/swagger.json", "/swagger/v1/swagger.json", "/.git/HEAD", "/.env"]


def run(ctx: dict, endpoints: dict, home_headers: dict, home_body: str) -> dict:
    fp = fingerprint(home_headers, home_body)
    files: list[dict] = []
    for k in KNOWN:
        if ctx["cancel"]():
            break
        r = fetch(ctx["target"] + k, timeout=8, proxy=ctx.get("proxy", ""))
        if r.get("status") in (200, 301, 302, 403):
            files.append({"path": k, "status": r.get("status"), "len": r.get("len", 0)})
    # OPTIONS on up to 5 main endpoints (Allow header, enum-only)
    methods: dict[str, str] = {}
    try:
        import requests
        from core.http import auth_headers, proxies_for
        for url in list(endpoints)[:5]:
            try:
                r = requests.options(url, timeout=8, verify=False,
                                     headers=auth_headers(None),
                                     proxies=proxies_for(ctx.get("proxy", "")))
                if r.headers.get("Allow"):
                    methods[url] = r.headers["Allow"][:120]
            except Exception:
                continue
    except ImportError:
        pass
    return {"tech": fp["tech"], "hsts": fp["hsts"], "cookie_flags": fp["cookie_flags"],
            "generator": fp.get("generator", ""),
            "files": files, "methods": methods,
            "msg": f"tech: {', '.join(fp['tech']) or 'unknown'}; {len(files)} known-files"}
