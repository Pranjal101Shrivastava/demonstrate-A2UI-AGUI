"""MCP Apps · MIXED mode - the HOST side.

server.py is the MCP server (spawned over stdio). This file gives the local
host its routes: "mcp" forwards JSON-RPC from the browser host page to the
server, "chat" lets the host's model choose a tool. The browser
(../host_page.js + common/web/mcp_host.js) mounts the ui:// resource in a
sandboxed iframe and runs the postMessage bridge.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.fixtures import days_from
from common.mcp_host import make_routes, trace

TITLE = "Catalog + nested generated region + an app-only action tool"
MODE = "mixed"
SERVER = pathlib.Path(__file__).with_name("server.py")


def scripted_pick(prompt):
    return json.dumps({"tool": "cafe_hybrid", "arguments": {"request": prompt}})


ROUTES = make_routes(SERVER, scripted_pick)


def cli():
    tools, result, html = trace(SERVER, "cafe_hybrid", {"request": "hybrid dashboard for 7 days"})
    print("\ntool result content[0].text (what the MODEL sees):", result["content"][0]["text"])
    print("structuredContent keys (what the VIEW gets):", list(result["structuredContent"]))
    print("view HTML has CSP:", "Content-Security-Policy" in html, "| inlines bridge:", "ui/initialize" in html)


if __name__ == "__main__":
    cli()
