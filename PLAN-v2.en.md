# AUTO_RECON v2 — Build Spec (EN, token-saving) + Maintainability Guide

## 1. Goal (1 line)
1 domain in → 1 click → full enum map: arch, subdomains, ports, endpoints (UI + hidden), params, JS, tech, files. No exploit. OSCP-safe. Offline `python3 app.py`.

## 2. Stack (frozen)
- `app.py` stdlib only (`http.server`, `subprocess`, `urllib`) + `requests/bs4` (preinstalled). No Flask/pip.
- `index.html` vanilla JS+CSS, no framework. `words.txt`, `scans/*.json`.
- Allowed tools only: `nmap, katana, ffuf/gobuster, nikto-enum`. Banned: `sqlmap, nuclei, Burp Pro, LLM calls, auto-sqli/xss`.

## 3. APIs (frozen contract)
- `POST /api/scan {target, profile:fast|deep|exam, auth:{mode:off|cookie|bearer|login, cookie?, bearer?, login_url?, user?, pass?}, proxy:""|"127.0.0.1:8080"} → {job_id}`
- `GET /api/progress?job → {pct, modules:{ports|crawl|brute|params|js|tech:{state,pct,msg}}, counts}`
- `GET /api/result?job&cat=overview|subdomains|ports|endpoints|params|js|tech|auth|notes → {items}`
- `GET /api/fetch?url → {status, final, headers, body(50k)}`
- `POST /api/cancel {job_id}`, `GET /api/health`

## 4. Modules (1 func each, timeout+cap)
- `ports(target)`: `nmap -sV --top-ports 100 --open` (fallback `-F`) → `{port,svc,ver}`.
- `passive(target)`: crt.sh/wayback/gau/robots/sitemap → urls, tag `passive`. OFF in exam profile.
- `crawl(target, auth)`: `katana -d5 -jc -jsl -aff -fx -xhr -do -silent -ct60` + internal requests/bs4 (href/form/script/meta). Follow 1× `302 Location`. Record `via`. Run twice: anon + auth (`-H Cookie`, ffuf `-b`).
- `brute(target)`: `ffuf -w raft-medium+custom -mc 200,301,302,403 -e .bak,.old,.json,.js -t20`, recurse 1 level `/api /admin /post`, soft-404 calibrate by len.
- `params(endpoints)`: query + form inputs + JS `searchParams.get()` + openapi/swagger. Flag `redirect_candidate` in `{next,url,redirect,return,continue,postId}`.
- `js(endpoints)`: fetch ≤10 JS (50KB), extract `fetch("/api..")`, `window.location`, hrefs. Edge page→JS→API.
- `tech(endpoints)`: headers + regex (generator, wp-content, __next, X-AspNet), OPTIONS Allow, cookie flags, HSTS. Status-only.
- `secrets(js)`: regex keys/tokens → show `abc…xyz` masked + file. Never full value.
- `score(endpoint)`: `auth-only+10, location+10, redirect-param+8, /api|/admin+5, has-params+3`. Sort only.

## 5. Endpoint record (frozen schema)
`{url,path,status_anon,status_auth,len_anon,len_auth,via,tags[],params[{name,via,redirect_candidate}],js_files[],hrefs[],forms[{action,method,inputs[]}],headers{},has_location_js,score}`

## 6. UI (9 tabs, progressive render, poll 2s)
`Overview(graph) | Subdomains | Ports | Endpoints(tree+anon/auth cols+filter) | Params | JS | Tech&Files | Auth&Session | Notes&Export`. Header: target+profile+auth+proxy+Scan/Cancel/Export. Progress: total + per-module bars + log tail. Detail per endpoint: Info/JS/Hrefs/Forms+Params/Raw/Burp(copy).

## 7. Auth (memory-only)
Modes: off | cookie string | bearer | login_url+user+pass (single POST, fetch CSRF token once, no brute). `Check session` via `GET /my-account` (username/logout vs 302→login). Never store pass in JSON. Redact Cookie/Bearer on export. Multi-role: optional second session → `anon vs user vs admin` matrix.

## 8. Exceptions (must-handle)
Scope: keep rdn, drop exploit-server/w3.org + allowlist. Net: 504/timeout/cert-verify-off/429-backoff/403-WAF-tag-blocked. Auth: die mid-scan, CSRF-token, MFA/SSO→manual. SPA: headless optional; GraphQL status-only; ws:// list-only. Limits: 200 URLs/60s per tool/threads≤20, skip binary/>50KB, normalize `?a=1/2`. Cancel/kill per module, Resume via saved JSON.

## 9. Profiles
- fast(~2m): nmap -F, katana d2, ffuf small, no passive.
- deep(~8m): full + recurse + passive.
- exam: deep minus passive, low threads, tight timeouts.

## 10. Milestones
- MS1: JobEngine+progress+tabs+crawl/brute. MS2: ports/params/JS+Burp export+save/diff. MS3: passive/tech/secrets/graph/score. MS4: auth-matrix/report/polish+3-lab tests.

## 11. Maintainability (how to code so it stays easy)
1. **One module = one file + one `run(ctx)->dict`.** `modules/ports.py:crawl.py:brute.py:params.py:js.py:tech.py:auth.py`. `app.py` only routes + job queue. No logic in HTML (render only).
2. **Frozen I/O schemas.** Never rename §5/API fields without bumping `SCHEMA=2`. Frontend guards `?.` defaults.
3. **Stdlib-first, tiny deps.** New dep only if stdlib impossible; document fallback when binary missing.
4. **Pure parsers.** `parse_*` take `(url, body)` → dict, no network inside. Network only in `fetch_*`. Unit-test parsers with 3 saved fixtures (`tests/fixtures/*.html`).
5. **Limits in one place.** `LIMITS={urls:200, per_tool_s:60, js_kb:50, threads:20}` in `config.py`. No magic numbers elsewhere.
6. **Fail-soft.** Every module wraps try/except → `{state:fail, msg}`; scan continues. Missing binary → skip + message, never crash.
7. **No secrets on disk.** Session lives in job memory; JSON stores `auth_user` only. Redact function `mask(v)` used by secrets + export.
8. **Small diffs.** One PR per module/milestone; update `PLAN-v2.md` § + README example in same diff.
9. **Smoke test before push.** `python3 -m py_compile app.py modules/*.py` + `POST /api/scan example.com` returns count>0 + `GET /api/health` all true.
