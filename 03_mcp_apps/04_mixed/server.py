"""MCP server for MCP Apps · MIXED: catalog spec + one GeneratedView region + an app-only tool.

`cafe_action` has _meta.ui.visibility=["app"]: the VIEW may call it through the
host, but the host never offers it to the model. Server-side state (stock) lives
here, not in the iframe.
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.catalog import catalog_prompt, validate_flat
from common.data import sales
from common.fixtures import dashboard_spec, days_from
from common.llm import complete, strip_fences
from common.mcp import MCPServer, view_page
from common.sandbox import check_html

server = MCPServer("campus-cafe-mixed")
URI = "ui://cafe/hybrid.html"
STOCK = dict(sales()["stock"])
SYSTEM = ("Compose a Campus Cafe UI from these components; use GeneratedView once for a custom visual:\n"
          + catalog_prompt(extra=True) + '\nReturn JSON only: {"root", "elements"}.')


def build(request, days=None):
    spec = json.loads(strip_fences(complete(SYSTEM, request, lambda p: json.dumps(dashboard_spec(days or days_from(p), hybrid=True)))))
    errors = validate_flat(spec, extra=True)
    for eid, el in spec["elements"].items():
        if el["type"] == "GeneratedView":
            errors += check_html(el["props"]["html"])
        if eid == "stock":
            el["props"]["rows"] = [[k, v] for k, v in STOCK.items()]
    if errors:
        raise ValueError("; ".join(errors[:5]))
    return spec


def cafe_hybrid(request: str):
    return {"spec": build(request), "_text": "Rendered the hybrid cafe dashboard."}


def cafe_action(name: str, params: dict = None):
    params = params or {}
    if name == "restock":
        STOCK[params.get("item", "beans_kg")] = STOCK.get(params.get("item", "beans_kg"), 0) + int(params.get("qty", 1))
        return {"spec": build("dashboard", days=7), "notice": f"Ordered {params.get('qty', 1)} {params.get('item')}", "_text": "restocked"}
    if name == "set_days":
        return {"spec": build("dashboard", days=int(params.get("days", 7))), "notice": f"Showing {params.get('days')} days", "_text": "ok"}
    raise ValueError(f"action {name!r} not allowed")


server.tool("cafe_hybrid", "Show the hybrid Campus Cafe dashboard for a free-text request.",
            {"type": "object", "properties": {"request": {"type": "string"}}, "required": ["request"]},
            cafe_hybrid, resource_uri=URI)
server.tool("cafe_action", "UI-only: apply a dashboard action.",
            {"type": "object", "properties": {"name": {"type": "string"}, "params": {"type": "object"}}, "required": ["name"]},
            cafe_action, resource_uri=URI, visibility=["app"])

VIEW_SCRIPT = r"""
const app = document.getElementById("app"), note = document.getElementById("note");
const draw = (sc) => { app.replaceChildren(renderNode(flatToTree(sc.spec), onAction)); note.textContent = sc.notice || ""; };
// Both catalog Buttons and genux.action() from the nested GeneratedView arrive here.
async function onAction(name, params) {
  try { draw((await mcp.callTool("cafe_action", { name, params })).structuredContent); }
  catch (e) { note.textContent = "error: " + e.message; }
}
mcp.on("ui/notifications/tool-result", (r) => draw(r.structuredContent));
mcp.connect();
"""
server.resource(URI, "Hybrid dashboard", lambda: view_page('<div class="msg" id="note"></div><div id="app">waiting…</div>', VIEW_SCRIPT, ("sandbox.js", "catalog.js")))

if __name__ == "__main__":
    server.serve_stdio()
