"""Scan persistence: scans/<host>/<ts>.json + diff two scans."""
from __future__ import annotations
import json
import os
from datetime import datetime
from urllib.parse import urlparse

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_DIR = os.path.join(APP_DIR, "scans")


def save_scan(target: str, payload: dict) -> str:
    host = (urlparse(target).hostname or "unknown").replace(":", "_")
    day = os.path.join(SCAN_DIR, host)
    os.makedirs(day, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(day, f"{ts}.json")
    # never persist secrets: strip session cookie/bearer/pass
    safe = {k: v for k, v in payload.items() if k != "auth_secret"}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(safe, f, ensure_ascii=False)
    except OSError:
        return ""
    return path


def list_scans(host: str = "") -> list:
    out = []
    if not os.path.isdir(SCAN_DIR):
        return out
    hosts = [host] if host else sorted(os.listdir(SCAN_DIR))
    for h in hosts:
        d = os.path.join(SCAN_DIR, h)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d), reverse=True)[:20]:
            out.append({"host": h, "file": fn, "path": os.path.join(h, fn)})
    return out


def load_scan(rel: str) -> dict:
    p = os.path.join(SCAN_DIR, rel)
    if ".." in rel or not os.path.isfile(p):
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def diff_scans(a: dict, b: dict) -> dict:
    au = {e.get("url") for e in a.get("endpoints", [])}
    bu = {e.get("url") for e in b.get("endpoints", [])}
    return {"new": sorted(bu - au)[:200], "lost": sorted(au - bu)[:200],
            "count_a": len(au), "count_b": len(bu)}
