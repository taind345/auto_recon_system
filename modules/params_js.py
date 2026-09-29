"""M6 params + M7 js-miner + secrets + score. Pure analysis over fetched bodies."""
from __future__ import annotations
from urllib.parse import urljoin
from core.http import fetch
from core.parse import mine_params, extract_js_api, find_secrets


def run_params(endpoints: dict) -> dict:
    n_inputs = 0
    n_redir = 0
    for ep in endpoints.values():
        inline = ep.get("_inline", [])
        jsb = [ep.get("_jsbody", {}).get(j, "") for j in ep.get("js_files", [])]
        ep["params"] = mine_params(ep["url"], ep.get("forms", []), inline, jsb)
        n_inputs += len(ep["params"])
        n_redir += sum(1 for p in ep["params"] if p.get("redirect_candidate"))
    return {"msg": f"params: {n_inputs} inputs, {n_redir} redirect-candidates",
            "inputs": n_inputs, "redir": n_redir}


def run_js(ctx: dict, endpoints: dict) -> dict:
    timeout = ctx["limits"]["fetch_s"]
    cap_kb = ctx["limits"]["js_kb"]
    proxy = ctx.get("proxy", "")
    auth = ctx.get("auth_session")
    wanted: list[str] = []
    for ep in endpoints.values():
        for j in ep.get("js_files", []):
            if j not in wanted:
                wanted.append(j)
            if len(wanted) >= ctx["limits"]["js_files"] * 2:
                break
    bodies: dict[str, str] = {}
    sinks = 0
    apis: set[str] = set()
    ws_all: list[str] = []
    secrets: list[dict] = []
    for ju in wanted[: ctx["limits"]["js_files"]]:
        if ctx["cancel"]():
            break
        d = fetch(ju, timeout=timeout, auth=None, proxy=proxy, max_body=cap_kb * 1024)
        body = d.get("body", "") or ""
        bodies[ju] = body[:8000]
        info = extract_js_api(body)
        if info["has_location"]:
            sinks += 1
        for a in info["apis"]:
            apis.add(urljoin(ctx["target"] + "/", a) if a.startswith("/") else a[:200])
        ws_all += info["ws"]
        secrets += find_secrets(body, ju)
    # also scan inline bodies for secrets (masked)
    for ep in endpoints.values():
        for blob in (ep.get("_inline", []) or [])[:3]:
            secrets += find_secrets(blob, ep["url"])
        ep["_jsbody"] = {k: v for k, v in bodies.items() if k in ep.get("js_files", [])}
        # tag client-redirect when sink found in its JS
        for j in ep.get("js_files", []):
            if j in bodies and extract_js_api(bodies[j])["has_location"]:
                if "client-redirect" not in ep["tags"]:
                    ep["tags"].append("client-redirect")
                ep["has_location_js"] = True
    return {"msg": f"js: {len(bodies)} files, {sinks} sinks, {len(apis)} apis",
            "files": len(bodies), "sinks": sinks, "apis": sorted(apis)[:100],
            "ws": ws_all[:10], "secrets": secrets[:50]}
