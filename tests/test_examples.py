"""Offline tests for all 24 examples (scripted model, no network, no API key).

    python -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import a2ui, agui  # noqa: E402
from common.catalog import validate_flat  # noqa: E402
from common.fixtures import dashboard_spec  # noqa: E402
from common.jsonpatch import apply_patch  # noqa: E402
from common.jsonrender import PatchStreamParser, spec_to_patches  # noqa: E402
from common.loader import example_dirs, load  # noqa: E402
from common.mcp import APP_MIME, MCPClient  # noqa: E402
from common.openui import HTML_SIGNATURES, SIGNATURES, Program, from_spec  # noqa: E402
from common.sandbox import check_html  # noqa: E402

ex = lambda rel: load(ROOT / rel)  # noqa: E731


def drain(gen):
    return list(gen)


class TestEveryExample(unittest.TestCase):
    def test_24_examples_with_4_modes_each(self):
        dirs = example_dirs()
        self.assertEqual(len(dirs), 24)
        modes = {}
        for d in dirs:
            m = load(d)
            for attr in ("TITLE", "MODE", "ROUTES", "cli"):
                self.assertTrue(hasattr(m, attr), f"{d} lacks {attr}")
            self.assertTrue((d / "index.html").is_file(), f"{d} lacks index.html")
            modes.setdefault(d.parent.name, []).append(m.MODE)
        for tech, ms in modes.items():
            self.assertEqual(ms, ["static", "declarative", "open-ended", "mixed"], tech)

    def test_every_cli_runs(self):
        for d in example_dirs():
            with self.subTest(example=d.relative_to(ROOT).as_posix()), contextlib.redirect_stdout(io.StringIO()) as out:
                load(d).cli()
                self.assertTrue(out.getvalue().strip())


class TestAGUI(unittest.TestCase):
    def run_events(self, rel, body):
        return drain(ex(rel).ROUTES["run"](body))

    def test_static_lifecycle_and_tool_args(self):
        ev = self.run_events("01_ag_ui/01_static", {"messages": [{"role": "user", "content": "sales for 3 days"}]})
        types = [e["type"] for e in ev]
        self.assertEqual(types[0], "RUN_STARTED")
        self.assertEqual(types[-1], "RUN_FINISHED")
        args = "".join(e["delta"] for e in ev if e["type"] == "TOOL_CALL_ARGS")
        self.assertEqual(json.loads(args), {"days": 3})
        self.assertLess(types.index("TOOL_CALL_START"), types.index("TOOL_CALL_END"))

    def test_declarative_state_rebuilds_valid_spec(self):
        state = {}
        for e in self.run_events("01_ag_ui/02_declarative", {"messages": [{"role": "user", "content": "dash 5 days"}]}):
            if e["type"] == "STATE_SNAPSHOT":
                state = e["snapshot"]
            elif e["type"] == "STATE_DELTA":
                state = apply_patch(state, e["delta"])
        self.assertEqual(validate_flat(state["ui"]), [])
        self.assertEqual(len(state["ui"]["elements"]), 14)

    def test_mixed_rejects_unknown_action_without_finishing(self):
        ev = self.run_events("01_ag_ui/04_mixed", {"forwardedProps": {"action": {"name": "evil"}}})
        self.assertEqual([e["type"] for e in ev], ["RUN_STARTED", "RUN_ERROR"])


class TestA2UI(unittest.TestCase):
    def test_static_structure_is_fixed(self):
        m = ex("02_a2ui/01_static")
        a, b = m.messages_for("3 days"), m.messages_for("7 days")
        self.assertEqual(a[1], b[1])          # identical components
        self.assertNotEqual(a[2], b[2])       # different data
        self.assertEqual(a2ui.validate(a), [])

    def test_declarative_corrects_itself(self):
        notes = []
        msgs = ex("02_a2ui/02_declarative").generate("overview 5 days", notes.append)
        self.assertTrue(notes[0].startswith("attempt 1") and "0 errors" not in notes[0])
        self.assertTrue(any(n.startswith("attempt 2") and "0 errors" in n for n in notes))
        self.assertEqual(a2ui.validate(msgs), [])

    def test_html_component_needs_opt_in_catalog(self):
        m = ex("02_a2ui/03_open_ended")
        self.assertEqual(a2ui.validate(m.messages_for("7 days")), [])
        self.assertTrue(a2ui.validate(m.messages_for("7 days", catalog=a2ui.CAFE_CATALOG)))

    def test_mixed_actions_send_data_only(self):
        out = drain(ex("02_a2ui/04_mixed").on_action({"action": {"name": "set_days", "context": {"days": 3}}}))
        self.assertTrue(all("updateDataModel" in o["a2ui"] for o in out))


class TestMCPApps(unittest.TestCase):
    def test_handshake_tools_and_ui_resource(self):
        for mode, tool, args in [("01_static", "cafe_dashboard", {"days": 2}), ("02_declarative", "cafe_ui", {"request": "x 3 days"}),
                                 ("03_open_ended", "generate_view", {"request": "7 days"}), ("04_mixed", "cafe_hybrid", {"request": "7 days"})]:
            with self.subTest(mode=mode):
                c = MCPClient(ROOT / "03_mcp_apps" / mode / "server.py")
                try:
                    init = c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}})
                    self.assertIn("io.modelcontextprotocol/ui", init["capabilities"]["extensions"])
                    t = {x["name"]: x for x in c.request("tools/list")["tools"]}[tool]
                    uri = t["_meta"]["ui"]["resourceUri"]
                    self.assertTrue(uri.startswith("ui://"))
                    self.assertIn("structuredContent", c.request("tools/call", {"name": tool, "arguments": args}))
                    res = c.request("resources/read", {"uri": uri})["contents"][0]
                    self.assertEqual(res["mimeType"], APP_MIME)
                    self.assertIn("Content-Security-Policy", res["text"])
                    self.assertEqual(res["text"].count("</script>"), 1)  # inlined modules never close the script early
                finally:
                    c.close()

    def test_app_only_tool_hidden_from_model(self):
        c = MCPClient(ROOT / "03_mcp_apps/04_mixed/server.py")
        try:
            tools = c.request("tools/list")["tools"]
        finally:
            c.close()
        picked = ex("03_mcp_apps/04_mixed").ROUTES["chat"]({"prompt": "7 days", "tools": tools})
        self.assertEqual(picked["tool"], "cafe_hybrid")
        self.assertEqual([t["_meta"]["ui"].get("visibility") for t in tools if t["name"] == "cafe_action"], [["app"]])


class TestJsonRender(unittest.TestCase):
    def test_stream_parser_drops_bad_element_keeps_rest(self):
        evs = drain(ex("04_json_render/02_declarative").stream({"prompt": "5 days"}, chunk=7))
        self.assertTrue(any("Gauge" in e.get("note", "") for e in evs))
        self.assertTrue(evs[-1]["note"].startswith("final spec valid: True"))

    def test_patch_roundtrip(self):
        spec = dashboard_spec(4)
        p = PatchStreamParser()
        text = "\n".join(json.dumps(o) for o in spec_to_patches(spec))
        for i in range(0, len(text), 11):
            p.feed(text[i:i + 11])
        p.close()
        self.assertEqual(p.spec, spec)

    def test_mixed_action_param_types_checked(self):
        with self.assertRaises(ValueError):
            ex("04_json_render/04_mixed").action_patches("restock", {"item": "beans_kg", "qty": "many"})


class TestOpenUI(unittest.TestCase):
    def test_forward_references_resolve(self):
        p = Program()
        p.feed('root = Stack([a, b], "row")\n')
        self.assertEqual(p.tree()["children"], [None, None])  # pending
        p.feed('a = Text("hi")\nb = Metric("x", 1)\n')
        self.assertEqual([c["type"] for c in p.tree()["children"]], ["Text", "Metric"])

    def test_spec_program_roundtrip_and_benchmark(self):
        sigs = dict(SIGNATURES, **HTML_SIGNATURES)
        p = Program(sigs)
        p.feed(from_spec(dashboard_spec(7, hybrid=True)))
        p.close()
        self.assertEqual(p.validate(), [])
        bench = ex("05_openui/02_declarative").benchmark()
        self.assertLess(bench["OpenUI Lang"][0], bench["json-render spec (JSON)"][0])

    def test_mixed_update_redefines(self):
        m = ex("05_openui/04_mixed")
        p = Program(m.SIGS)
        p.feed(m.generate("7 days"))
        n = len(p.defs)
        p.feed(m.update("set_days", {"days": 2}))
        self.assertEqual(len(p.defs), n)
        self.assertIn("last 2 days", p.tree("title")["props"]["text"])


class TestHarness(unittest.TestCase):
    def tool_results(self, rel, body):
        return [e for e in drain(ex(rel).ROUTES["run"](body)) if e["type"] == "TOOL_CALL_RESULT"]

    def test_declarative_error_then_success(self):
        r = self.tool_results("06_harness/02_declarative", {"prompt": "5 days"})
        self.assertTrue(r[1]["content"].startswith("ERROR"))
        self.assertEqual(json.loads(r[2]["content"]), {"rendered": 14})

    def test_open_ended_policy_blocks_cdn(self):
        r = self.tool_results("06_harness/03_open_ended", {"prompt": "7 days"})
        self.assertIn("external scripts", r[1]["content"])

    def test_mixed_action_reenters_loop(self):
        m = ex("06_harness/04_mixed")
        drain(m.run({"threadId": "t", "prompt": "7 days"}))
        before = len(m.SESSIONS["t"].messages)
        names = [e["toolCallName"] for e in drain(m.on_action({"threadId": "t", "action": "restock", "params": {"item": "milk_l", "qty": 1}})) if e["type"] == "TOOL_CALL_START"]
        self.assertEqual(names, ["restock", "render_ui"])
        self.assertGreater(len(m.SESSIONS["t"].messages), before)


class TestSandboxPolicy(unittest.TestCase):
    def test_blocks(self):
        self.assertTrue(check_html('<script src="https://x/y.js"></script>'))
        self.assertTrue(check_html("<script>fetch('/a')</script>"))
        self.assertTrue(check_html("<script>localStorage.x=1</script>"))
        self.assertEqual(check_html("<b>ok</b><script>genux.action('set_days',{days:3})</script>"), [])


class TestBrowserParity(unittest.TestCase):
    """The browser renderers must agree with the Python validators."""

    def test_node_parity(self):
        r = subprocess.run(["node", str(ROOT / "tests/parity.test.mjs")], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
