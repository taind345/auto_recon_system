"""M5 brute: ffuf FUZZ + extensions + 1-level recurse. gobuster fallback message."""
from __future__ import annotations
import os
import re
import shutil
from . _runner import run_cmd
from core.http import auth_headers

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wordlist_for(ctx: dict) -> str:
    want = ctx["profile_cfg"].get("ffuf_wordlist", "small")
    for cand in (f"words/{want}.txt", f"words_{want}.txt", "words.txt",
                 "words/medium.txt", "words/small.txt"):
        p = os.path.join(APP_DIR, cand)
        if os.path.isfile(p):
            return p
    return os.path.join(APP_DIR, "words.txt")


def _auth_flags(auth: dict | None) -> list[str]:
    if not auth or auth.get("mode") in (None, "off"):
        return []
    for k, v in auth_headers(auth).items():
        if k.lower() == "cookie":
            return ["-b", v]
        if k.lower() == "authorization":
            return ["-H", f"Authorization: {v}"]
    return []


def _proxy_flags(proxy: str) -> list[str]:
    if not proxy:
        return []
    return ["-x", proxy if "://" in proxy else "http://" + proxy]


def _parse_hits(out: str, target: str) -> list[str]:
    """ffuf -s prints matched URLs (absolute) or paths (relative). Join cleanly."""
    hits: list[str] = []
    base = target.rstrip("/")
    for line in out.splitlines():
        line = line.strip().split()[0] if line.strip() else ""
        if not line:
            continue
        if line.startswith("http"):
            hits.append(line[:300])
        elif line.startswith("/"):
            hits.append((base + "/" + line.lstrip("/"))[:300])
    return hits


def run(ctx: dict) -> dict:
    target = ctx["target"]
    timeout = ctx["limits"]["per_tool_s"]
    wl = wordlist_for(ctx)
    if not os.path.isfile(wl):
        return {"hits": [], "msg": "wordlist missing"}
    if not shutil.which("ffuf"):
        return {"hits": [], "msg": "ffuf not found (skip)"}
    cmd = ["ffuf", "-u", target.rstrip("/") + "/FUZZ", "-w", wl,
           "-mc", "200,301,302,403", "-s", "-t",
           str(min(ctx["profile_cfg"].get("threads", 20), 20)),
           "-timeout", "8", "-e", ".bak,.old,.json,.js",
           *_auth_flags(ctx.get("auth_session")), *_proxy_flags(ctx.get("proxy", ""))]
    out = run_cmd(cmd, timeout=timeout + 10)
    hits = _parse_hits(out, target)
    # recurse 1 level on interesting prefixes (cheap, bounded, same flags)
    if ctx["profile_cfg"].get("recurse"):
        for prefix in ("/api", "/admin", "/post"):
            if ctx["cancel"]():
                break
            o2 = run_cmd(["ffuf", "-u", target.rstrip("/") + prefix + "/FUZZ", "-w", wl,
                          "-mc", "200,301,302,403", "-s", "-t", "10", "-timeout", "5",
                          *_auth_flags(ctx.get("auth_session")),
                          *_proxy_flags(ctx.get("proxy", ""))], timeout=30)
            hits += _parse_hits(o2, target)
    hits = sorted(set(hits))[: ctx["limits"]["brute_hits"]]
    # soft-404 calibrate note: caller compares len vs home len
    return {"hits": hits, "msg": f"ffuf: {len(hits)} hits ({os.path.basename(wl)})"}
