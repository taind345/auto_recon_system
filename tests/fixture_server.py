"""Lab fixture target: login (csrf) + auth-only pages + DOM sink + secret-shaped JS.

Routes:
  /                     home (links, form q/returnPath, /s.js)
  /login                GET csrf form / POST wiener:peter -> session cookie
  /my-account, /my-account/change-email   302 anon / 200 auth
  /public               inline window.location sink (returnPath)
  /s.js                 fetch("/api/data") + AKIA-shaped key + location sink
  /api/data, /robots.txt, /sitemap.xml
  *                     404
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

USER, PASS = "wiener", "peter"
SESS = "session=abc123wiener"
CSRF = "tok123"

HOME = """<html><head><title>lab</title><script src="/s.js"></script></head><body>
<h1>lab home</h1>
<a href="/login">login</a> <a href="/public?postId=3">post</a> <a href="/my-account">account</a>
<form action="/public" method="GET"><input name="q"><input name="returnPath"></form>
</body></html>"""
LOGIN = f"""<html><body><form action="/login" method="POST">
<input type="hidden" name="csrf" value="{CSRF}">
<input name="username"><input name="password" type="password">
</form></body></html>"""
PUBLIC = """<html><body><div id="c">hello</div>
<script>const u=new URLSearchParams(window.location.search);
const r=u.get('returnPath'); if(r){window.location=r;}</script>
</body></html>"""
SJS = """const k="AKIAIOSFODNN7EXAMPLE";
fetch("/api/data").then(r=>r.json());
function go(){const p=new URLSearchParams(window.location.search).get('returnPath');
if(p){window.location=p;}}"""
ACCT = """<html><body>Welcome wiener <a href="/logout">logout</a>
<div id="comment-status">ok</div></body></html>"""


class FixtureHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def authed(self) -> bool:
        return SESS in (self.headers.get("Cookie") or "")

    def send(self, body, code=200, ctype="text/html", extra=None) -> None:
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: C901
        p = urlparse(self.path).path
        if p == "/":
            self.send(HOME)
        elif p == "/login":
            self.send(LOGIN)
        elif p == "/public":
            self.send(PUBLIC)
        elif p == "/s.js":
            self.send(SJS, ctype="application/javascript")
        elif p == "/api/data":
            self.send('{"user":"wiener"}', ctype="application/json")
        elif p == "/my-account":
            if self.authed():
                self.send(ACCT)
            else:
                self.send("Redirecting to /login...", code=302, extra={"Location": "/login"})
        elif p == "/my-account/change-email":
            if self.authed():
                self.send("<html><body>change email wiener <a href='/logout'>logout</a></body></html>")
            else:
                self.send("Redirecting...", code=302, extra={"Location": "/login"})
        elif p == "/robots.txt":
            self.send("User-agent: *\nDisallow: /admin\n", ctype="text/plain")
        elif p == "/sitemap.xml":
            self.send("<urlset><url><loc>/public</loc></url></urlset>", ctype="application/xml")
        else:
            self.send("not found", code=404)

    def do_POST(self):
        p = urlparse(self.path).path
        if p != "/login":
            self.send("nf", code=404)
            return
        n = int(self.headers.get("Content-Length") or 0)
        q = parse_qs(self.rfile.read(n).decode())
        u = (q.get("username") or q.get("user") or [""])[0]
        pw = (q.get("password") or q.get("pass") or [""])[0]
        if u == USER and pw == PASS:
            self.send("ok", code=302,
                      extra={"Set-Cookie": SESS + "; Path=/", "Location": "/my-account"})
        else:
            self.send("bad login", code=401)
