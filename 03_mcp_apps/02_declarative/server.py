"""MCP server for MCP Apps · DECLARATIVE: the tool returns a catalog spec;
the ui:// view is a GENERIC renderer for that catalog (it ships no layout of its own)."""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
import json

from common.catalog import catalog_prompt, validate_flat
from common.fixtures import dashboard_spec, days_from
from common.llm import complete, strip_fences
from common.mcp import MCPServer, view_page

server = MCPServer("campus-cafe-declarative")
URI = "ui://cafe/catalog-renderer.html"
SYSTEM = "Compose a Campus Cafe UI from ONLY these components:\n" + catalog_prompt() + '\nReturn JSON only: {"root", "elements"}.'


def cafe_ui(request: str = "dashboard"):
    """The SERVER calls the model to write the spec, validates it, and returns it as structuredContent."""
    spec = json.loads(strip_fences(complete(SYSTEM, request, lambda p: json.dumps(dashboard_spec(days_from(p))))))
    errors = validate_flat(spec)
    if errors:
        raise ValueError("invalid spec: " + "; ".join(errors[:5]))
    return {"spec": spec, "_text": f"Rendered a {len(spec['elements'])}-element UI for: {request}"}


server.tool("cafe_ui", "Build an interactive Campus Cafe UI for a free-text request.",
            {"type": "object", "properties": {"request": {"type": "string"}}, "required": ["request"]},
            cafe_ui, resource_uri=URI)

VIEW_SCRIPT = r"""
const app = document.getElementById("app");
const draw = (spec) => app.replaceChildren(renderNode(flatToTree(spec), onAction));
// Catalog buttons become tool calls back to the server, through the host.
async function onAction(action, params) {
  if (action === "set_days") draw((await mcp.callTool("cafe_ui", { request: `dashboard for ${params.days} days` })).structuredContent.spec);
  else app.prepend(Object.assign(document.createElement("div"), { className: "msg", textContent: `action ${action} is handled in 04_mixed` }));
}
mcp.on("ui/notifications/tool-result", (r) => draw(r.structuredContent.spec));
mcp.connect();
"""
server.resource(URI, "Catalog renderer", lambda: view_page('<div id="app">waiting for spec…</div>', VIEW_SCRIPT, ("sandbox.js", "catalog.js")))

if __name__ == "__main__":
    server.serve_stdio()
