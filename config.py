"""Central limits + profiles. Single source of truth (no magic numbers elsewhere)."""
from __future__ import annotations

SCHEMA = 2

LIMITS = {
    "urls": 200,          # max endpoints stored per job
    "passive_urls": 60,   # passive share of the cap (active enum goes first)
    "per_tool_s": 60,     # timeout per external tool
    "fetch_s": 12,        # timeout per HTTP fetch
    "js_kb": 50,          # max JS body to analyse (KB)
    "body_kb": 200,       # max HTML body to store (KB)
    "js_files": 10,       # max JS files to fetch per job
    "crawl_pages": 30,    # max pages for internal crawl enrichment
    "threads": 20,        # max worker threads
    "brute_hits": 100,
    "custom_wl_lines": 5000,  # custom upload cap
    "custom_wl_kb": 256,
}

PROFILES = {
    "fast": {  # ~2 min
        "label_vi": "Nhanh (~2’)",
        "label_en": "Fast (~2m)",
        "nmap_args": ["-F", "--open"],
        "katana_depth": 2,
        "ffuf_wordlist": "small",
        "passive": False,
        "recurse": False,
        "threads": 10,
    },
    "deep": {  # ~8 min
        "label_vi": "Sâu (~8’)",
        "label_en": "Deep (~8m)",
        "nmap_args": ["-sV", "--top-ports", "100", "--open", "-T4"],
        "katana_depth": 5,
        "ffuf_wordlist": "medium",
        "passive": True,
        "recurse": True,
        "threads": 20,
    },
    "exam": {  # OSCP exam: like deep minus passive, low threads
        "label_vi": "OSCP-thi",
        "label_en": "OSCP-exam",
        "nmap_args": ["-sV", "--top-ports", "100", "--open", "-T3"],
        "katana_depth": 5,
        "ffuf_wordlist": "medium",
        "passive": False,
        "recurse": True,
        "threads": 10,
    },
}

# 8 pipeline modules shown in UI (order matters)
MODULES = [
    ("ports", "M1", "PORTS"),
    ("passive", "M2", "PASSIVE"),
    ("crawl_anon", "M3", "CRAWL_ANON"),
    ("crawl_auth", "M4", "CRAWL_AUTH"),
    ("brute", "M5", "FFUF_DIR"),
    ("params", "M6", "PARAMS"),
    ("js", "M7", "JS_MINER"),
    ("tech", "M8", "TECH_STACK"),
]

REDIRECT_HINTS = frozenset({
    "next", "url", "redirect", "redirect_to", "redirectto",
    "return", "returnurl", "return_url", "returnpath", "return_path",
    "continue", "dest", "destination", "postid", "r", "u",
})

INTEREST_HINTS = (
    "admin", "api", "redirect", "confirm", "comment", "change-email",
    "my-account", "login", "logout", "dashboard", "console", "config",
    ".env", ".git", "backup", "upload", "graphql", "swagger", "openapi",
)

OUT_OF_SCOPE_HOSTS = ("exploit-server", "portswigger.net", "w3.org", "w3c.org")

SECRET_RES = (
    ("aws_key", r"AKIA[0-9A-Z]{16}"),
    ("google_api", r"AIza[0-9A-Za-z\-_]{35}"),
    ("slack", r"xox[baprs]-[0-9A-Za-z\-]{10,60}"),
    ("bearer", r"[Bb]earer\s+[A-Za-z0-9\-._~+/=]{10,}"),
    ("secret_assign", r"(?i)(secret|api[_-]?key|token)\s*=\s*['\"][^'\"]{4,}['\"]"),
)

NEXT_STEP_HINTS = {
    "redirect_candidate": ("thử returnPath=//attacker.com, javascript:alert(domain)", "try returnPath=//attacker.com, javascript:alert(domain)"),
    "auth-only": ("so sánh anon 302 vs auth 200, thử IDOR decrement id", "compare anon 302 vs auth 200, try IDOR id decrement"),
    "has-params": ("fuzz param thủ công từng giá trị, xem phản xạ", "manually test each param value for reflection"),
    "client-redirect": ("tìm window.location sink trong JS, kiểm tra postId/returnPath", "find window.location sink in JS, check postId/returnPath"),
    "api": ("xem JSON response, thử verb tampering/OPTIONS", "inspect JSON, try OPTIONS / verb tampering"),
}
