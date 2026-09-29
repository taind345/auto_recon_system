"""External tool runner: timeout + cap + fail-soft (shared by modules)."""
from __future__ import annotations
import subprocess


def run_cmd(cmd: list[str], timeout: int = 60, cap: int = 50_000) -> str:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (p.stdout[:cap] + p.stderr[:5000]) if p.stdout else p.stderr[:cap]
    except FileNotFoundError:
        return "ERR: binary not found"
    except subprocess.TimeoutExpired:
        return "ERR: timeout"
    except Exception as e:  # fail-soft
        return f"ERR: {e}"[:500]
