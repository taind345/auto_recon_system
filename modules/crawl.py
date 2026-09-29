"""M3/M4 crawl: katana + internal requests/bs4 enrichment. Records via + follows 1x 302."""
from __future__ import annotations
import os
import re
import shutil
from urllib.parse import urljoin, urlparse
from . _runner import run_cmd
from core.http import fetch, auth_headers
from core.parse import parse_html, LOCATION_RE
from core.scope import in_scope, norm_url

KATANA_CANDIDATES = ("/tmp/opencode/katana-bin/katana", "katana")


def katana_bin() -> str:
    for c in KATANA_CANDIDATES:
        if os.path.exists(c) or shutil.which(c if "/" not in c else ""):
            return c
    return ""


def run_katana(target: str, depth: int, timeout: int, auth: dict | None,
               proxy: str) -> tuple[list[str], str]:
    b = katana_bin()
    if not b:
        return [], "katana not found (internal crawl only)"
    cmd = [b, "-u", target, "-d", str(depth), "-jc", "-aff", "-silent", "-ct", "45"]
    if auth and auth.get("mode") not in (None, "off"):
        for k, v in auth_headers(auth).items():
            if k.lower() in ("cookie", "authorization"):
                cmd += ["-H", f"{k}: {v}"]
    if proxy:
        cmd += ["-proxy", proxy if "://" in proxy else "http://" + proxy]
    out = run_cmd(cmd, timeout=timeout + 10)
    urls = sorted({u.split("#")[0] for u in
                   re.findall(r'https?://[^\s"\'<>]+', out) if in_scope(u, target)})
    return urls, f"katana(d{depth}): {len(urls)} urls"


def enrich(pages: list[str], ctx: dict, auth: dict | None, via_label: str) -> dict:
    """Fetch up to N pages. Records truthful first-status; extracts
    href/form/script only from HTTP 200 bodies (never from redirect targets)."""
    out: dict[str, dict] = {}
    target = ctx["target"]
    timeout = ctx["limits"]["fetch_s"]
    proxy = ctx.get("proxy", "")
    for url in pages[: ctx["limits"]["crawl_pages"]]:
        if ctx["cancel"]():
            break
        d = fetch(url, timeout=timeout, auth=auth, proxy=proxy,
                  max_body=ctx["limits"]["body_kb"] * 1024)
        status = d.get("status", 0)
        info: dict = {"status": status, "location": d.get("location", ""),
                      "headers": d.get("headers", {}),
                      "final_url": d.get("final", url),
                      "raw_len": d.get("len", 0),
                      "hrefs": [], "forms": [], "js_files": [],
                      "has_location_js": False, "sink_inline": False,
                      "inline": []}
        if status == 200 and d.get("body"):
            p = parse_html(url, d["body"])
            js_files = []
            for s in p["scripts"][:10]:
                ju = urljoin(url, s)
                if in_scope(ju, target):
                    js_files.append(ju)
            inline = p["inline"][:3]
            info.update({"hrefs": [h for h in p["hrefs"][:20]],
                         "forms": p["forms"][:5], "js_files": js_files,
                         "inline": inline})
            if LOCATION_RE.search(d["body"] or ""):
                info["has_location_js"] = True
                info["sink_inline"] = True
            for h in p["hrefs"][:15]:
                nxt = urljoin(url, h)
                if in_scope(nxt, target):
                    out.setdefault("__queue__:" + norm_url(nxt),
                                   {"via": f"href:{urlparse(url).path or '/'}"})
        out[url] = info
    return out


def run(ctx: dict, authed: bool = False) -> dict:
    target = ctx["target"]
    depth = ctx["profile_cfg"].get("katana_depth", 3)
    timeout = ctx["limits"]["per_tool_s"]
    auth = ctx.get("auth_session") if authed else None
    proxy = ctx.get("proxy", "")
    k_urls, msg = run_katana(target, depth, timeout, auth, proxy)
    seed = [target] + [u for u in k_urls if u.startswith(target)][: ctx["limits"]["urls"]]
    # home always first for forms/js baseline
    data = enrich(seed, ctx, auth, "auth" if authed else "anon")
    queued = [k.split("__:")[1] for k in list(data) if k.startswith("__queue__:")]
    for k in [k for k in data if k.startswith("__queue__:")]:
        del data[k]
    return {"urls": [u for u in seed if not u.startswith("__queue__:")],
            "queued": queued[: ctx["limits"]["urls"]],
            "enriched": data, "msg": msg,
            "mode": "auth" if authed else "anon"}
