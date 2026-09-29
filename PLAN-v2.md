# AUTO_RECON v2 — Kế hoạch chi tiết All-in-One Recon (1-click, enum-only, OSCP-safe)

> Mục tiêu: 1 domain vào → 1 click → có tất cả: kiến trúc hệ thống, subdomain, ports, endpoints (UI được + ẩn), params, JS/secrets, tech, files. UI progress + kết quả phân danh mục, dễ nhìn nhất.

## 1. Luồng 1-click (user story)
1. Dán `https://target/` → chọn profile `Nhanh / Sâu / OSCP-thi` → bấm **Scan**.
1b. **Nếu có credentials (optional):** bật `Authenticated scan`, nhập 1 trong 3 cách: (a) user/pass + login-url để tool tự login lấy session, (b) dán Cookie header, (c) dán Authorization Bearer. Bấm `Check session` thấy `logged-in as X` mới Scan.
2. Thấy progress bar tổng + từng module chạy song song (ports, crawl-unauth, crawl-auth, brute...), log streaming, nút Cancel/Retry từng module.
3. Kết quả đổ dần vào 9 danh mục (không đợi xong hết mới thấy), có cột so sánh `anon vs auth`.
4. Click endpoint trong cây → phải thấy ngay JS tương ứng, href, form/params, raw, mẫu Burp (kèm session nếu có).

## 2. Kiến trúc hệ thống
```
index.html (dashboard)
  │ POST /api/scan {target, profile} → job_id
  │ GET  /api/progress?job=… (SSE/poll 1s): {pct, module_states, counts}
  │ GET  /api/result?job=…&cat=subdomains|ports|endpoints|params|js|tech|files
  ▼
app.py (JobEngine, stdlib, không Flask/pip)
  ├─ queue + subprocess runner (kill được, timeout từng tool)
  ├─ normalizer + scope guard (chỉ rdn, bỏ ngoài-scope)
  └─ store scans/<host>/<ts>.json (để diff + mở lại)
modules/ ports.py tech.py passive.py crawl.py brute.py params.py js.py
```
- Offline-first, `python3 app.py 8000` chạy trên Kali không pip.
- Mỗi tool chạy có timeout + giới hạn (200 URL, 60s/tool, threads ≤20) để không DoS lab.

## 3. Danh mục kết quả (9 tab cố định)
1. **Overview / System map:** sơ đồ target → IP → ports → tech → N endpoints/params/js; SVG mini page→JS→API; thêm dòng `auth: off/on (user X)` + số endpoint chỉ hiện khi login.
2. **Subdomains:** crt.sh + wayback + gau (passive, tắt mặc định ở profile OSCP-thi); cột alive/status.
3. **Network/Ports:** `nmap -sV --top-ports 100 --open` (+fallback `-F`); banner Server/X-Powered-By.
4. **Endpoints:** cây thư mục collapsible group theo segment (`/post`, `/api`, `/resources`); badge `interesting/has-params/client-redirect/js/api/gadget/auth-only`; filter text; phân biệt `via: click-UI-được (katana/href/form)` vs `ẩn (ffuf/302/JS)`; cột `anon: 200/302/403` vs `auth: 200/403` để thấy khác biệt khi login.
5. **Params & Inputs:** bảng toàn site {param, via: query/form/js/swagger, ở endpoint nào, redirect_candidate?}; filter theo tên.
6. **JS & Links:** mỗi page → script src + inline; nút Xem tải source (50KB, beautify); trích `fetch("/api..")`, `searchParams.get()`, `window.location`, href.
7. **Tech & Files:** header fingerprint (Generator, wp-content, __next, X-AspNet…), robots/sitemap/security.txt, backup/`/.git/HEAD`/`.env` (chỉ check status, không dump sâu).
8. **Auth & Session (mới):** trạng thái session, login-url, cách attach (cookie/header), nút Check/Re-login, bảng endpoint `auth-only` (anon 302→login nhưng auth 200, vd `/my-account?id=wiener`, `/my-account/change-email`), cảnh báo nếu session hết hạn giữa scan.
9. **Notes & Export:** note từng endpoint, Diff 2 scan (kể cả diff anon-vs-auth), export JSON/CSV, copy Burp Repeater 1-click (kèm Cookie/Bearer nếu có).

## 4. Module chi tiết (tool + lệnh + output)
- **M1 ports:** `nmap -sV -sC --top-ports 100 --open -T4 {host}` → {port,svc,ver}. Fallback `-F`.
- **M2 passive:** `waybackurls`, `gau`, `crt.sh?q=%.host` → subdomains+urls cũ, tag passive. Profile thi tắt.
- **M3 crawl (xương sống):** `katana -d 5 -jc -jsl -aff -fx -xhr -do -silent -ct 60` + crawler nội bộ requests/bs4 (href/form/script/meta-refresh). Ghi `via`. Tự theo `302 Location` 1 lần để lòi confirmation/gadget.
- **M4 brute:** `ffuf -u {t}/FUZZ -w raft-medium+custom -mc 200,301,302,403 -e .bak,.old,.json,.js -t 20` (+gobuster dự phòng); recurse 1 level `/api /admin /post`; calibrate soft-404 theo độ dài.
- **M5 params:** query + form inputs + JS regex + `/openapi.json|/swagger*.json`. Đánh dấu redirect_candidate {next,url,redirect,return,continue,postId}.
- **M6 js:** fetch 10 JS đầu, trích endpoint/fetch/XHR, hiển thị cạnh page→JS→API.
- **M7 tech/files:** headers + regex + robots/sitemap/security.txt + known-sensitive status-only.
- **M8 jobs:** progress {queued/running/done/fail}, log tail, cancel/kill, retry.
- **M9 auth-session (mới, vì có login scan khác hẳn):**
  - Input: `login_url + user/pass` (tool tự POST 1 lần lấy Set-Cookie, không brute-force), hoặc `Cookie: session=...`, hoặc `Authorization: Bearer ...`. Lưu trong memory job, không ghi disk mặc định, có nút xóa.
  - Attach: mọi fetch/katana/ffuf đều chạy 2 lượt `anon` và `auth` (katana `-H "Cookie: ..."`, ffuf `-b`, requests headers). So sánh status/len để gắn tag `auth-only` (vd anon 302→/login nhưng auth 200 ở `/my-account?id=wiener`).
  - Validate: nút `Check session` gọi `GET /my-account` xem có chứa username/logout không; nếu 302 về login thì báo session die, dừng nhánh auth.
  - An toàn: không tự đổi password/email, không lưu pass plaintext vào scan JSON (chỉ lưu `auth_user`, không lưu pass), Burp export kèm session tách riêng để bạn tự xóa trước khi nộp report.

## 5. Data model (mỗi endpoint)
`{url, path, status_anon, status_auth, len_anon, len_auth, via, tags[] (+auth-only khi anon≠auth), params[{name,via,redirect_candidate}], js_files[], hrefs[], forms[{action,method,inputs[]}], headers{}, has_location_js, final_url}`

## 6. UI progress + dễ nhìn
- Header: input + profile + Scan/Cancel + Export + cụm **Auth (off/user-pass/cookie/bearer) + Check session** + cụm **Proxy qua Burp (off/127.0.0.1:8080)**.
- Progress tổng + 8 thanh module (thêm `crawl-auth`) + log box (tail 50 dòng).
- Kết quả đổ dần (poll 2s), skeleton khi chưa có; toggle `Ẩn/Hiện: chỉ auth-only`.
- Cây thư mục: `details/summary` collapsible, badge màu, click → detail 6 sub-tab Info/JS/Hrefs/Forms+Params/Raw/Burp.
- Search toàn cục + nút "chỉ hiện redirect-candidate / có params".

## 7. Profile 1-click
- **Nhanh (~2’):** ports `-F`, katana d2, ffuf small, không passive.
- **Sâu (~8’):** ports full 100, katana d5 + jsluice, ffuf medium + recurse, passive on.
- **OSCP-thi:** như Sâu nhưng passive OFF, threads thấp, timeout chặt.

## 8. Ranh giới OSCP (hard rule)
KHÔNG: sqlmap/nuclei/auto-SQLi-XSS-test/browser_autopwn/Burp Pro/LLM API trong tool/mass vuln report. CHỈ hiện bằng chứng enum + gắn tag candidate. Ghi `enum-only` trong UI+README.

## 9. Cấu trúc code khi coding
`app.py, index.html, words.txt, modules/{ports,passive,crawl,brute,params,js,tech}.py, scans/, README.md, PLAN-v2.md`

## 10. Milestone + test
- MS1: JobEngine + progress + 8 tab rỗng + M3/M4 cơ bản.
- MS2: M1/M5/M6 + Burp export + lưu/diff scan.
- MS3: M2/M7 + recurse/soft-404 + polish UI.
- MS4: test 3 lab (blog/api/spa) + docs thi.
- Đạt: lab SameSite phải ra `/post/comment → confirmation?postId (client-redirect) → commentConfirmationRedirect.js (window.location) → change-email (ffuf)`; `example.com` không crash khi 504.

## 11. Ngoại lệ thực tế (bổ sung để tool không gãy)
- **Target/scope:** http/https lẫn lộn, www vs root, port lạ, IP thay domain, redirect chain `http→https→www`; ngoài-scope (`exploit-server`, `portswigger.net`, w3.org) tự loại, chỉ giữ rdn + nút allowlist.
- **Mạng/lab:** 504 lab hết hạn, timeout, cert self-signed (verify=False + cảnh báo), 429 rate-limit (giảm threads, backoff), 403 WAF/Cloudflare/captcha (gắn tag `blocked`, không retry vô hạn), kill/cancel từng module.
- **Auth:** session die giữa scan (re-check, dừng nhánh auth), login cần CSRF token động (fetch token trước POST 1 lần), MFA/OTP/captcha/SSO (không tự bypass — chuyển manual, tool chỉ lưu cookie dán tay), nhiều role (chạy thêm lượt `user2/admin` để diff phân quyền), không lưu pass plaintext, không tự đổi email/pass.
- **SPA/API:** trang render bằng JS (katana headless optional, không bắt buộc), GraphQL (`/graphql` introspect status-only), WebSocket (chỉ liệt kê `ws://` thấy trong JS, không fuzz), upload/pagination (ghi chú manual).
- **Tool/data:** thiếu binary (fallback crawl nội bộ + báo msg), site khổng lồ (cap 200 URL/60s/tool), file nhị phân/JS >50KB (skip body, chỉ ghi meta), soft-404 (calibrate theo len), trùng query-param (normalize).
- **An toàn/báo cáo:** che Cookie/Bearer khi export/screenshot (evidence hygiene), nút xóa session, mọi candidate chỉ gắn tag không kết luận vuln.

## 12. Bổ sung đợt 2 (soi thêm để xịn thật)
- **Proxy qua Burp (quan trọng nhất):** toggle `Proxy: off / 127.0.0.1:8080`, mọi requests/katana/ffuf đi qua Burp để lọt hết vào `Proxy > HTTP history + Site map`; nút `Copy as Repeater` đã có, thêm `Open in Burp` hướng dẫn + export list URL để paste vào Burp.
- **Secrets mining (hiển thị che mờ):** regex `aws_key, google-api, slack, bearer, secret=` trong JS/body, chỉ hiện `đầu...cuối` + file chứa, không hiện full — phục vụ hunting nhưng giữ hygiene.
- **Methods + headers audit (enum-only):** `OPTIONS` mỗi endpoint chính (Allow: GET/POST?), check thiếu `HSTS`, cookie thiếu `Secure/HttpOnly/SameSite` — chỉ liệt kê, không exploit.
- **Scope/project:** multi-target queue, allowlist/blocklist regex trên UI, dedup `?a=1 vs ?a=2` gộp 1 node, lưu project `scans/<host>/<ts>.json` + nút Resume.
- **Wordlist:** 3 mức built-in (small/medium) + upload custom + extensions `.bak,.old,.json,.js` cấu hình được.
- **Next-step gợi ý (không auto-test):** mỗi endpoint có checklist tay ví dụ `có postId + location → thử foo/../ ; có form → thử 302` — giúp bạn biết nhìn vào endpoint thì thử gì.
- **API contract trước khi code:** `POST /api/scan → {job_id}`, `GET /api/progress?job → {pct, modules{state,pct,msg}}`, `GET /api/result?job&cat → {items}`, `GET /api/fetch?url`, `POST /api/cancel`.

## 13. Chốt xịn nhất (khóa scope tại đây)
- **Site graph:** tab Overview vẽ `page → JS → API` force-graph nhẹ (SVG, không lib nặng), click node nhảy sang detail.
- **Heuristic score (không AI, không kết luận vuln):** `auth-only +10, window.location +10, param redirect +8, /api|/admin +5, has-params +3`; sort đáng-nhìn-nhất lên đầu.
- **Ma trận role 3 cột:** `anon vs user vs admin` (thêm ô nhập session thứ 2), tag `role-only` khi user≠admin.
- **So sánh song song:** detail endpoint hiện diff `anon vs auth` (status/len/headers) cạnh nhau.
- **Report 1-click:** xuất Markdown `endpoint → checkbox đã xem → gợi ý thử tay`, dùng nộp lab/thi.
- **Không làm thêm:** auto-verify SQLi/XSS, nuclei, LLM, screenshot headless nặng, DB — để giữ offline + OSCP-safe + chạy nổi trên Kali.

