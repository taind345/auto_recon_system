"""M1 ports: nmap -sV --top-ports 100 --open (fallback -F)."""
from __future__ import annotations
import re
import shutil
from urllib.parse import urlparse
from . _runner import run_cmd


def run(ctx: dict) -> dict:
    host = urlparse(ctx["target"]).hostname or ""
    args: list[str] = ctx["profile_cfg"].get("nmap_args", ["-F", "--open"])
    timeout: int = ctx["limits"]["per_tool_s"]
    proxy: str = ctx.get("proxy", "")
    if not shutil.which("nmap"):
        return {"ports": [], "msg": "nmap not found (skip)"}
    if proxy:
        return {"ports": [], "msg": "proxy on: nmap skipped (route via Burp manually)"}
    out = run_cmd(["nmap", *args, host], timeout=timeout)
    if "ERR" in out and "-F" not in args:
        out = run_cmd(["nmap", "-F", "--open", host], timeout=timeout)
    ports = [{"port": p, "svc": s[:60]} for p, s in re.findall(r"(\d+)/tcp\s+open\s+(\S*)", out)]
    return {"ports": ports[:50], "msg": f"nmap: {len(ports)} open"}
