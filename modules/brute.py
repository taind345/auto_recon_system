"""M5 brute: ffuf FUZZ + extensions + 1-level recurse. gobuster fallback message."""
from __future__ import annotations
import os
import re
import shutil
from . _runner import run_cmd
from core.http import auth_headers

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# system SecLists used for the "large" tier (never bundled into the repo)
SECLISTS_LARGE = [
    "/usr/share/seclists/Discovery/Web-Content/raft-medium-words.txt",
    "/usr/share/seclists/Discovery/Web-Content/raft-small-words.txt",
    "/usr/share/seclists/Discovery/Web-Content/directory-list-2.3-medium.txt",
]
DEFAULT_EXT = ".bak,.old,.json,.js"


def wordlist_for(ctx: dict) -> tuple[str, str]:
    """Resolve (path, label). Tier: custom upload > large seclists > bundled."""
    tier = ctx.get("wordlist") or ctx["profile_cfg"].get("ffuf_wordlist", "small")
    if tier == "custom":
        p = ctx.get("custom_wl_path", "")
        if p and os.path.isfile(p):
            return p, "custom(upload)"
        tier = "small"
    if tier == "large":
        for p in SECLISTS_LARGE:
            if os.path.isfile(p):
                return p, "seclists:" + os.path.basename(p)
        tier = "medium"  # seclists absent (non-Kali): fall back, never crash
    for cand in (f"words/{tier}.txt", f"words_{tier}.txt", "words.txt",
                 "words/medium.txt", "words/small.txt"):
        p = os.path.join(APP_DIR, cand)
        if os.path.isfile(p):
            return p, os.path.basename(p)
    return os.path.join(APP_DIR, "words.txt"), "words.txt"


def extensions_for(ctx: dict) -> str:
    raw = str(ctx.get("extensions") or DEFAULT_EXT)
    out: list[str] = []
    for e in raw.split(","):
        e = e.strip().lower().lstrip(".")
        if re.fullmatch(r"[a-z0-9]{1,8}", e or "") and e not in [x.lstrip(".") for x in out]:
            out.append("." + e)
        if len(out) >= 10:
            break
    return ",".join(out) if out else DEFAULT_EXT


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
    wl, label = wordlist_for(ctx)
    if not os.path.isfile(wl):
        return {"hits": [], "msg": "wordlist missing"}
    if not shutil.which("ffuf"):
        return {"hits": [], "msg": "ffuf not found (skip)"}
    cmd = ["ffuf", "-u", target.rstrip("/") + "/FUZZ", "-w", wl,
           "-mc", "200,301,302,403", "-s", "-t",
           str(min(ctx["profile_cfg"].get("threads", 20), 20)),
           "-timeout", "8", "-e", extensions_for(ctx),
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
    return {"hits": hits, "msg": f"ffuf: {len(hits)} hits ({label})"}
