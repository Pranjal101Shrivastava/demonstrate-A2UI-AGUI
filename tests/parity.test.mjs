// Node checks that the browser-side modules agree with the Python ones.
// Python prints reference outputs; we compute the same in JS and compare.
import { execFileSync } from "node:child_process";
import assert from "node:assert/strict";
import { Program, SIGNATURES, HTML_SIGNATURES } from "../common/web/openui.js";
import { applyPatch } from "../common/web/jsonpatch.js";

const py = (code) => JSON.parse(execFileSync("python3", ["-c", "import sys,json; sys.path.insert(0,'.');" + code], { encoding: "utf8" }));

// 1) OpenUI: the JS parser resolves the same tree as Python, even when fed in odd chunks.
const ref = py("from common.openui import *; from common.fixtures import dashboard_spec; s=from_spec(dashboard_spec(5,True)); p=Program(dict(SIGNATURES,**HTML_SIGNATURES)); p.feed(s); p.close(); t=p.tree(); print(json.dumps({'src':s,'tree':t}))");
const p = new Program({ ...SIGNATURES, ...HTML_SIGNATURES });
for (let i = 0; i < ref.src.length; i += 13) p.feed(ref.src.slice(i, i + 13));
p.close();
const norm = (n) => n && typeof n === "object" && !Array.isArray(n) && n.type ? { type: n.type === "GeneratedView" ? "HtmlArtifact" : n.type, props: n.props, children: (n.children || []).map(norm) } : n;
assert.deepEqual(norm(p.tree()), norm(ref.tree));
assert.equal(p.errors.length, 0);

// 2) JSON Patch: same result as Python.
const ops = [{ op: "add", path: "/a", value: { b: [1, 2] } }, { op: "add", path: "/a/b/-", value: 3 }, { op: "replace", path: "/a/b/0", value: 9 }, { op: "remove", path: "/a/b/1" }, { op: "add", path: "/c~1d", value: true }];
const pyRes = py(`from common.jsonpatch import apply_patch; print(json.dumps(apply_patch({}, json.loads(${JSON.stringify(JSON.stringify(ops))}))))`);
assert.deepEqual(applyPatch({}, ops), pyRes);
console.log("parity OK: OpenUI parser and JSON Patch match Python");
