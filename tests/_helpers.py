"""Shared fixtures for AUTO_RECON tests (stdlib only)."""
from __future__ import annotations
import json
import threading
import urllib.request
from http.server import HTTPServer


def start_server(handler, host="127.0.0.1", port=0):
    srv = HTTPServer((host, port), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, t, srv.server_address[1]


def stop_server(srv) -> None:
    try:
        srv.shutdown()
    except Exception:
        pass
    try:
        srv.server_close()
    except Exception:
        pass


def api(base: str, path: str, data=None, timeout: int = 30) -> dict:
    import urllib.error
    url = base + path
    try:
        if data is None:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return json.loads(r.read().decode())
        body = json.dumps(data).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode())
        except Exception:
            return {"error": f"http {e.code}"}


def wait_done(base: str, job: str, timeout: int = 240, interval: int = 2) -> dict:
    import time
    t0 = time.time()
    last: dict = {}
    while time.time() - t0 < timeout:
        try:
            last = api(base, f"/api/progress?job={job}")
        except Exception:
            time.sleep(interval)
            continue
        if last.get("status") in ("done", "cancelled"):
            return last
        time.sleep(interval)
    raise TimeoutError(f"job {job} not done: {last}")
