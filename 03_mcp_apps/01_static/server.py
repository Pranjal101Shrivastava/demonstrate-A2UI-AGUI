"""MCP server for MCP Apps · STATIC: one tool + one hand-written ui:// view.

Run standalone for a desktop host (Claude Desktop, Goose, ...):  python server.py --stdio
"""
import pathlib, sys; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # repo root
from common.data import sales
from common.mcp import MCPServer, view_page

server = MCPServer("campus-cafe-static")
URI = "ui://cafe/dashboard.html"


def cafe_dashboard(days: int = 7):
    s = sales(days)
    s["_text"] = f"{s['total_cups']} cups, ${s['total_revenue']:.2f} over {s['days']} days; best day {s['best_day']}."
    return s  # -> structuredContent for the view, content[0].text for the model


server.tool("cafe_dashboard", "Show the Campus Cafe sales dashboard for the last N days (1-7).",
            {"type": "object", "properties": {"days": {"type": "integer", "minimum": 1, "maximum": 7}}},
            cafe_dashboard, resource_uri=URI)

# STATIC view: the developer wrote this layout. Data arrives via ui/notifications/tool-result.
VIEW_SCRIPT = r"""
function draw(d) {
  const node = { type: "Card", props: { title: `Campus Cafe - last ${d.days} days` }, children: [
    { type: "Stack", props: { direction: "row" }, children: [
      { type: "Metric", props: { label: "Cups", value: d.total_cups } },
      { type: "Metric", props: { label: "Revenue", value: "$" + d.total_revenue.toFixed(2) } },
      { type: "Metric", props: { label: "Best day", value: d.best_day } } ] },
    { type: "BarChart", props: { labels: d.labels, values: d.cups } } ] };
  document.getElementById("app").replaceChildren(renderNode(node));
}
mcp.on("ui/notifications/tool-result", (r) => draw(r.structuredContent));
// Interactive: the VIEW calls the server's tool through the host.
for (const b of document.querySelectorAll("[data-days]"))
  b.onclick = async () => draw((await mcp.callTool("cafe_dashboard", { days: +b.dataset.days })).structuredContent);
mcp.connect();
"""
server.resource(URI, "Cafe dashboard", lambda: view_page(
    '<div id="app">waiting for tool result…</div><p><button data-days="3">3 days</button> <button class="secondary" data-days="7">7 days</button></p>',
    VIEW_SCRIPT, extra_modules=("sandbox.js", "catalog.js")))

if __name__ == "__main__":
    server.serve_stdio()
