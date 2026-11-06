"""Content policy for model-generated HTML (open-ended mode).

The browser mounts generated HTML in <iframe sandbox="allow-scripts"> with a
restrictive CSP (see common/web/sandbox.js). On the server we also reject
the obvious problems before the HTML ever reaches the page. A sandbox
REDUCES capability; it does not make arbitrary output trustworthy.
"""
import re

MAX_BYTES = 40_000
BLOCKED = [
    (r"<script[^>]+src\s*=", "external scripts are not allowed"),
    (r"<link[^>]+href\s*=\s*['\"]?https?:", "external stylesheets are not allowed"),
    (r"\bfetch\s*\(|XMLHttpRequest|WebSocket", "network APIs are not allowed"),
    (r"\b(document\.cookie|localStorage|sessionStorage)\b", "storage access is not allowed"),
    (r"\b(window\.)?(top|parent)\.location", "navigating the host is not allowed"),
]


def check_html(html: str) -> list:
    errs = []
    if len(html.encode()) > MAX_BYTES:
        errs.append(f"html is larger than {MAX_BYTES} bytes")
    for pat, msg in BLOCKED:
        if re.search(pat, html, re.I):
            errs.append(msg)
    return errs
