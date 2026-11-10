#!/usr/bin/env python3
"""Build docs/index.html (the assignment's website) from docs/results/*.json and docs/figures/*.svg.

Static, self-contained, no JavaScript and no external assets. Serve with GitHub Pages (folder
/assignment5_rsi/docs) or open the file directly.
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RES = ROOT / "docs" / "results"
FIG = ROOT / "docs" / "figures"


def load(name):
    try:
        return json.loads((RES / f"{name}.json").read_text())
    except (OSError, ValueError):
        return {}


def m(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def svg(name):
    p = FIG / name
    return p.read_text() if p.exists() else "<p>(run labs/10_18 to generate this figure)</p>"


def key_results():
    r = {k: load(k) for k in [f"10_{i:02d}" for i in range(1, 19)]}
    out = {}
    try:
        out["10_01"] = (f"Reference demo's +{r['10_01']['check_a']['no_diag_mean'] - r['10_01']['check_a']['naive_mean']:.0f} pp "
                        f"gap survives with diagnostics deleted; best seed {r['10_01']['best_seed']} vs mean "
                        f"{r['10_01']['check_b']['heldout_mean']}")
    except KeyError:
        pass
    try:
        out["10_02"] = f"Probes cost {r['10_02']['probe_share_pct']:.0f}% of SO-RSI's budget (the 'lightweight' assumption, measured)"
    except KeyError:
        pass
    try:
        res = r["10_03"]["results"]
        out["10_03"] = ("Held-out after 40 expansions: readout " + f"{m([x['heldout'] for x in res['readout']]):.1f}, parent-rate "
                        f"{m([x['heldout'] for x in res['parent_rate']]):.1f}, random {m([x['heldout'] for x in res['random']]):.1f}")
    except KeyError:
        pass
    try:
        v = r["10_04"]["variants"]
        out["10_04"] = (f"Within-sibling Spearman on strong parents: climb-trained {v[0]['spearman_strong']:+.2f} vs shifted "
                        f"{v[-1]['spearman_strong']:+.2f}; shifted readout loses ~12 held-out instances")
    except (KeyError, IndexError):
        pass
    try:
        res = r["10_05"]["results"]
        k = list(res)
        out["10_05"] = (f"Task features + online refit {m(res[k[3]]['heldout']):.1f} vs paper readout {m(res[k[0]]['heldout']):.1f}; "
                        f"shuffled-label control {m(res[k[4]]['heldout']):.1f}")
    except (KeyError, IndexError):
        pass
    try:
        out["10_06"] = (f"SO-RSI {m([x['heldout'] for x in r['10_06']['so_rsi']]):.1f} vs Naive RSI "
                        f"{m([x['heldout'] for x in r['10_06']['naive']]):.1f} held-out at equal budget")
    except KeyError:
        pass
    try:
        a = r["10_07"]["ablations"]
        out["10_07"] = (f"Full {m(a['SO-RSI (full)']):.1f}; no mechanism map {m(a['no mechanism map']):.1f}; probe every failure "
                        f"{m(a['gate = always (probe every failure)']):.1f}; no inquiry {m(a['gate = never (no inquiry)']):.1f}")
    except KeyError:
        pass
    try:
        out["10_08"] = f"Anomalies {', '.join(r['10_08']['anomalies'])}; probe shows 0 code variants pass all tests, so the test is wrong"
    except KeyError:
        pass
    try:
        d = r["10_09"]
        out["10_09"] = " · ".join(f"{k.split(' (')[0]} {m(v):.1f}" for k, v in d.items())
    except (KeyError, AttributeError):
        pass
    try:
        out["10_10"] = f"Shared conditional memory {m(r['10_10']['shared']):.1f} vs independent researchers {m(r['10_10']['independent']):.1f}"
    except KeyError:
        pass
    try:
        a = r["10_11"]["ablations"]
        out["10_11"] = (f"Full swarm {m(a['full SwarmRSI']):.1f}; same start for all agents {m(a['same start for all agents']):.1f} "
                        "(diversity of directions carries the result)")
    except KeyError:
        pass
    try:
        out["10_12"] = " · ".join(f"{k.split(' (')[0]} {m(v):.1f}" for k, v in r["10_12"].items())
    except (KeyError, AttributeError):
        pass
    try:
        out["10_13"] = f"Adaptive meta-agent {m(r['10_13']['adaptive']):.1f} vs static workflow {m(r['10_13']['static']):.1f} (a tie)"
    except KeyError:
        pass
    try:
        g = r["10_14"]["gains"]
        out["10_14"] = f"Gain over seed: policy-only {g['policy']:+.1f}, harness-only {g['harness']:+.1f}, joint {g['joint']:+.1f}"
    except KeyError:
        pass
    try:
        s = r["10_15"]["signalforge"]
        out["10_15"] = "RSI-Index (budget 2400): " + ", ".join(f"{k} {m(v['rsi_index']):.2f}" for k, v in s.items())
    except KeyError:
        pass
    out["10_16"] = "Services with budget + 'final' permission; sandbox refuses imports; held-out refused during search"
    try:
        out["10_17"] = (f"Steering proxy Spearman {r['10_17']['steering_validity']['spearman']:+.2f}; most learnable family "
                        f"{max(r['10_17']['learnability'], key=r['10_17']['learnability'].get)}")
    except KeyError:
        pass
    try:
        d = r["10_18"]
        out["10_18"] = " · ".join(f"{k.split('@')[0]} {m(d[k]['heldout']):.1f}" for k in d if k.endswith("@4800"))
    except KeyError:
        pass
    return out


LABS = [
    ("10_01", "10_01_claim_vs_evidence", "Distinguish claim from evidence", "Read a frontier claim"),
    ("10_02", "10_02_audit_paper", "Audit an October 2026 paper (SO-RSI)", "Read a frontier claim"),
    ("10_03", "10_03_run_budget_rsi", "Run Budget RSI", "Budget RSI"),
    ("10_04", "10_04_analyze_readout", "Analyse the scoring mechanism", "Budget RSI"),
    ("10_05", "10_05_extend_readout", "Extend the scorer to our task", "Budget RSI"),
    ("10_06", "10_06_run_so_rsi", "Run SO-RSI", "Second-order RSI"),
    ("10_07", "10_07_analyze_probes", "Analyse diagnostic probes", "Second-order RSI"),
    ("10_08", "10_08_apply_debugging", "Apply SO-RSI to a debugging task", "Second-order RSI"),
    ("10_09", "10_09_compare_scaling", "Compare scaling approaches", "Scaling & swarms"),
    ("10_10", "10_10_leader_follower", "Leader-follower coordination (AReaL-RSI)", "Scaling & swarms"),
    ("10_11", "10_11_swarm_evolution", "Swarm evolution (SwarmRSI)", "Scaling & swarms"),
    ("10_12", "10_12_compare_workflows", "Compare workflow adaptation", "Adaptive workflows"),
    ("10_13", "10_13_rsiflow_meta_agent", "RSIFlow meta-agent", "Adaptive workflows"),
    ("10_14", "10_14_self_hpo", "Self-HPO alternation", "Adaptive workflows"),
    ("10_15", "10_15_rsi_index", "Calculate RSI-Index", "Environments & metrics"),
    ("10_16", "10_16_environments", "Compare environments (EaaS)", "Environments & metrics"),
    ("10_17", "10_17_metrics", "Analyse the new metrics", "Environments & metrics"),
    ("10_18", "10_18_three_method_showdown", "Synthesis: three methods head to head", "Synthesis"),
]

CSS = """
:root{--bg:#f7f7f5;--card:#ffffff;--ink:#1d2025;--mut:#5f6672;--line:#e3e4e8;--acc:#3a63e0;--good:#15885f;--warn:#b0581b;--code:#f0f1f4}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111316;--card:#181b20;--ink:#e7e9ee;--mut:#9aa2ae;--line:#2a2f37;--acc:#7f9cff;--good:#4cc79a;--warn:#f0a066;--code:#20242b}}
:root[data-theme="dark"]{--bg:#111316;--card:#181b20;--ink:#e7e9ee;--mut:#9aa2ae;--line:#2a2f37;--acc:#7f9cff;--good:#4cc79a;--warn:#f0a066;--code:#20242b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}h1{font-size:30px;line-height:1.2;margin:0 0 8px}
h2{font-size:21px;margin:40px 0 12px}h3{font-size:16px;margin:0 0 6px}.lede{color:var(--mut);max-width:760px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.card p{margin:6px 0;color:var(--mut);font-size:14.5px}.big{font-size:26px;font-weight:650}.good{color:var(--good)}.warn{color:var(--warn)}
table{border-collapse:collapse;width:100%;font-size:14px;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mut);font-weight:600}
.scroll{overflow-x:auto}code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:13.5px}
pre{background:var(--code);padding:12px;border-radius:8px;overflow-x:auto;font-size:13px}a{color:var(--acc)}
.fig svg{width:100%;height:auto;display:block}.tag{display:inline-block;font-size:12px;color:var(--mut);border:1px solid var(--line);border-radius:99px;padding:1px 8px}
ul{padding-left:20px}li{margin:4px 0}
"""


def build():
    kr = key_results()
    d18 = load("10_18")
    head = {k.split("@")[0]: (m(v["heldout"]), m(v["rsi_index"])) for k, v in d18.items() if k.endswith("@4800")} if d18 else {}

    def hv(name):
        return f"{head[name][0]:.1f}" if name in head else "?"

    rows = "\n".join(
        f"<tr><td><b>{n.replace('_', '.')}</b><br><span class='tag'>{escape(g)}</span></td><td>{escape(t)}</td>"
        f"<td>{escape(kr.get(n, '-'))}</td><td><a href='../labs/{d}/README.md'>walkthrough</a> · "
        f"<a href='../labs/{d}/lab.py'>code</a></td></tr>" for n, d, t, g in LABS)
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SignalForge RSI Studio</title><meta name="description" content="Assignment 5: three October 2026 RSI methods rebuilt on a self-improving traffic-signal controller.">
<style>{CSS}</style></head><body><main>
<span class="tag">Assignment 5 · Section 10 Research Studio · RSI Masterclass (October 2026 edition)</span>
<h1>SignalForge: recursive self-improvement of a traffic-signal controller</h1>
<p class="lede">All 17 codelabs of Section 10, plus a synthesis lab, implemented progressively on one problem. The thing being
improved is a <b>Python program</b>: the controller that decides, second by second, when a four-way intersection switches its lights.
Three state-of-the-art RSI methods (<b>Budget RSI</b>, <b>SO-RSI</b> and <b>SwarmRSI</b>) are rebuilt from the course's paper
summaries and compared under one fair protocol. Everything runs on a laptop CPU with the Python standard library.</p>

<h2>The problem</h2>
<div class="grid">
<div class="card"><h3>Environment</h3><p>A queueing simulator: 4 approaches, 2 phases, 2 s saturation headway, 2 s start-up loss, 4 s clearance.
8 traffic families: light, heavy, N/S- or E/W-dominant, morning ramp, stadium surge, night, platoons.</p></div>
<div class="card"><h3>Benchmark</h3><p>An instance is <i>solved</i> if average delay ≤ 18 s and no car waits &gt; 70 s.
Splits: 16 <b>fit</b> · 48 <b>steering</b> · 100 <b>held-out</b>. Search code physically cannot read held-out (enforced and unit-tested).</p></div>
<div class="card"><h3>Improved object</h3><p>A genome rendered to real Python source with up to five mechanisms (actuated gap-out, max-green cap,
pressure switching, starvation guard, skip-empty) and their constants. The seed fixed-time plan solves <b>31/100</b>.</p></div>
<div class="card"><h3>Fair comparison</h3><p>One cost unit = one instance simulation. Every method gets the same total budget.
Readout labels and diagnostic probes are charged. Results are reported as mean ± sd over seeds.</p></div>
</div>

<h2>Three RSI methods, head to head</h2>
<div class="grid">
<div class="card"><h3>Budget RSI <span class="tag">arXiv:2610.29121</span></h3><div class="big">{hv('Budget RSI')}<span class="tag">/100 held-out</span></div>
<p>A linear readout on 8 diff coordinates scores edits <i>before running them</i>, and HGM/Thompson selection expands only the top child.
Recursive variant: the readout refits itself on every expansion (lab 10.05).</p></div>
<div class="card"><h3>SO-RSI <span class="tag">arXiv:2610.05701</span></h3><div class="big good">{hv('SO-RSI')}<span class="tag">/100 held-out</span></div>
<p>Watches its own edit trace for recurrence, opposing edits and expectation mismatch, then runs cost-charged diagnostic probes on the failing
instances and keeps causal findings in inquiry memory.</p></div>
<div class="card"><h3>SwarmRSI <span class="tag">arXiv:2610.20431</span></h3><div class="big">{hv('SwarmRSI')}<span class="tag">/100 held-out</span></div>
<p>Five agents with different research directions, feedback-guided mutation, complementary recombination, and a swarm procedure
that evolves its own recombination rate and step size.</p></div>
</div>
<p class="lede">Baselines at the same 4,800-unit budget: random search {hv('random search')}, Naive (first-order) RSI {hv('Naive RSI')}.</p>
<div class="card fig">{svg('showdown_heldout.svg')}</div>
<div class="card fig" style="margin-top:14px">{svg('showdown_anytime.svg')}</div>

<h2>All Section 10 codelabs</h2>
<div class="scroll"><table><thead><tr><th>Lab</th><th>Codelab</th><th>Measured result (from docs/results)</th><th>Files</th></tr></thead>
<tbody>{rows}</tbody></table></div>

<h2>What the evidence supports, and what it does not</h2>
<ul>
<li><b>SO-RSI's gain survives every control we tried.</b> Removing the hand-written mechanism map barely matters, so the gain comes from
anomaly-gated <i>sweeps on the failing instances</i>. Probing after every failure (no anomaly gate) loses about 10 instances (lab 10.07).</li>
<li><b>Budget RSI depends on where its labels come from.</b> A readout trained on random-walk parents ranks the strong parents HGM actually expands
worse, and loses about 12 held-out instances (lab 10.04). Its gain over the parent-rate ablation is small and noisy, as in the paper.</li>
<li><b>SwarmRSI's result comes from diverse starting hypotheses.</b> Ablating the shared board, recombination or procedure evolution is within noise
at this budget (lab 10.11).</li>
<li><b>Negative result:</b> the RSIFlow meta-agent re-routes work but ties a static workflow (lab 10.13). <b>Course demo audit:</b> the reference
SO-RSI demo hard-codes its success rates (lab 10.01).</li>
<li>These are laptop adaptations. They preserve each paper's <i>mechanism</i>, not its scale or headline numbers.</li>
</ul>

<h2>Reproduce</h2>
<pre>cd assignment5_rsi
python run_all.py          # all labs + tests, rewrites docs/EXECUTION_LOG.md and this page
python labs/10_06_run_so_rsi/lab.py   # any single lab
python -m unittest discover -s tests -v</pre>
<p class="lede">Unedited output of every lab: <a href="EXECUTION_LOG.md">docs/EXECUTION_LOG.md</a> · Course map:
<a href="https://github.com/dlmastery/simple-coding-harness/blob/main/COURSE-MAP.md#theme-10">Theme 10</a></p>
</main></body></html>
"""
    (ROOT / "docs" / "index.html").write_text(html, encoding="utf-8")
    print("wrote docs/index.html")


if __name__ == "__main__":
    build()
