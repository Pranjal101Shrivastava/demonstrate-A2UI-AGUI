#!/usr/bin/env python3
"""One local server for all 24 examples.  Usage:  python serve.py [port]

  GET  /                          index of every example
  GET  /<tech>/<mode>/            that example's index.html
  POST /<tech>/<mode>/api/<name>  that example's ROUTES[name](body)
                                  -> JSON, or an SSE stream if the handler yields
  GET  /common/web/<file>         shared renderer, sandbox, styles
"""
import inspect
import json
import mimetypes
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from common.loader import ROOT, example_dirs, load

DELAY = float(os.environ.get("GENUX_DELAY", "0.04"))  # seconds between streamed events, to make streaming visible


def index_html():
    rows, last = [], None
    for d in example_dirs():
        m = load(d)
        rel = d.relative_to(ROOT).as_posix()
        tech = rel.split("/")[0]
        if tech != last:
            rows.append(f"<tr><th colspan=3 style='padding-top:16px;text-align:left'>{tech}</th></tr>")
            last = tech
        rows.append(f"<tr><td><a href='/{rel}/'>{rel}</a></td><td><span class=tag>{m.MODE}</span></td><td>{m.TITLE}</td></tr>")
    return f"""<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>
<title>GenUX Examples</title><link rel=stylesheet href='/common/web/style.css'>
<header class=top><h1>GenUX: A2UI · AG-UI · MCP Apps · json-render · OpenUI · Harness</h1></header>
<div style='padding:16px 20px'><div class=panel><table class=g-table>{''.join(rows)}</table></div></div>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("  " + (fmt % args) + "\n")

    def _send(self, code, body, ctype):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            return self._send(200, index_html(), "text/html; charset=utf-8")
        if path.endswith("/"):
            path += "index.html"
        f = (ROOT / path.lstrip("/")).resolve()
        if ROOT not in f.parents or not f.is_file() or f.suffix == ".py":
            return self._send(404, "not found", "text/plain")
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        if f.suffix in (".js", ".mjs"):
            ctype = "text/javascript"
        self._send(200, f.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text") else ""))

    def do_POST(self):
        path = self.path.split("?")[0].strip("/")
        if "/api/" not in path:
            return self._send(404, "not found", "text/plain")
        ex_rel, route = path.split("/api/", 1)
        ex_dir = ROOT / ex_rel
        if not (ex_dir / "example.py").is_file():
            return self._send(404, "no such example", "text/plain")
        mod = load(ex_dir)
        handler = getattr(mod, "ROUTES", {}).get(route)
        if not handler:
            return self._send(404, "no such route", "text/plain")
        n = int(self.headers.get("content-length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        try:
            result = handler(body)
        except Exception as e:  # report errors as data, not a crash
            return self._send(400, json.dumps({"error": str(e)}), "application/json")
        if inspect.isgenerator(result):
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("cache-control", "no-store")
            self.end_headers()
            for event in result:
                self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                self.wfile.flush()
                time.sleep(DELAY)
            return
        self._send(200, json.dumps(result), "application/json")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"GenUX examples on http://127.0.0.1:{port}/  ({len(example_dirs())} examples)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
