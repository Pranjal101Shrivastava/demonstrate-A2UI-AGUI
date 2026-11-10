"""Lab 10.18 (synthesis): the three headline RSI methods head to head on SignalForge.

Budget RSI, SO-RSI and SwarmRSI against two baselines (random search, Naive RSI), with
the protocol held fixed for every method:

  * same seed program, same edit operators, same simulator, same 48-instance steering split
  * same TOTAL budget of instance-simulations. Budget RSI's readout labels and SO-RSI's
    probes are charged to it.
  * the held-out split (100 instances) is read only after each search returns
  * 5 seeds x 2 budgets (2,400 and 4,800 units)

Outputs: results table, RSI-Index, cost breakdown, anytime curves, and two SVG charts in
docs/figures/ that the website (docs/index.html) embeds.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import final_report  # noqa: E402
from signalforge.labkit import ROOT, banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.baselines import naive_rsi, random_search  # noqa: E402
from signalforge.methods.budget_rsi import budget_rsi  # noqa: E402
from signalforge.methods.so_rsi import so_rsi  # noqa: E402
from signalforge.methods.swarm_rsi import swarm_rsi  # noqa: E402
from signalforge.metrics import rsi_index  # noqa: E402
from signalforge.program import SEED_PROGRAM  # noqa: E402
from signalforge.stats import fmt_ms, mean, std  # noqa: E402
from signalforge.svg import bar_chart, line_chart  # noqa: E402

METHODS = [("random search", random_search, False), ("Naive RSI", naive_rsi, False),
           ("Budget RSI", budget_rsi, True), ("SO-RSI", so_rsi, True), ("SwarmRSI", swarm_rsi, True)]
BUDGETS = (2400, 4800)
banner("LAB 10.18 · THREE RSI METHODS HEAD TO HEAD ON SignalForge",
       "same seed program, operators, simulator, splits and TOTAL budget for every method")

seed_rep = final_report(SEED_PROGRAM, who="lab10.18-seed")
print(f"seed program: {seed_rep.solved}/100 held-out, mean delay {seed_rep.mean_delay:.1f} s")
results = {}
for B in BUDGETS:
    section(f"Budget {B:,} instance-simulations, {len(seeds(5))} seeds")
    rows = []
    for name, fn, _ in METHODS:
        runs = run_many(fn, seeds(5), budget=B, label=name)
        idx = [rsi_index(seed_rep.by_family(), r["heldout_by_family"])[0] for r in runs]
        results[(name, B)] = {"runs": runs, "rsi_index": idx}
        rows.append([name, fmt_ms([r["steering"] for r in runs]), fmt_ms([r["heldout"] for r in runs]),
                     fmt_ms([r["heldout_delay"] for r in runs]), f"{mean(idx):.3f}",
                     " ".join(str(r["heldout"]) for r in runs), f"{mean([r['seconds'] for r in runs]):.1f}s"])
    table(rows, ["method", "steering /48", "held-out /100", "delay s", "RSI-Index", "per seed", "cpu/run"])

section("Where each method spent its budget (4,800 units, mean over seeds)")
purposes = ["search", "expansion", "readout-labels", "probe", "recombination"]
rows = []
for name, _, _ in METHODS:
    runs = results[(name, 4800)]["runs"]
    rows.append([name] + [f"{mean([r['ledger'].get(p, 0) for r in runs]):.0f}" for p in purposes]
                + [f"{mean([r['units'] for r in runs]):.0f}"])
table(rows, ["method"] + purposes + ["total used"])

section("How each improver revised ITSELF during the run (seed 0, 4,800 units)")
r_b = results[("Budget RSI", 4800)]["runs"][0]["_result"]
r_s = results[("SO-RSI", 4800)]["runs"][0]["_result"]
r_w = results[("SwarmRSI", 4800)]["runs"][0]["_result"]
coef = r_b.extras["coefficients"]
top = sorted(((k, v) for k, v in coef.items() if k not in ("bias", "parent_rate")), key=lambda kv: -abs(kv[1]))[:3]
print(f"Budget RSI: learned a selection rule from {96} labelled edits before searching; strongest diff")
print(f"            coordinates {', '.join(f'{k} {v:+.2f}' for k, v in top)}")
mem = r_s.extras["memory"]
print(f"SO-RSI    : {len(mem.findings)} findings in inquiry memory, tuned constants {mem.tuned},")
print(f"            {sum(len(v) for v in mem.bans.values())} operators banned as exhausted, {len(mem.refuted)} recommendations refuted")
last = r_w.trace[-1]
print(f"SwarmRSI  : procedure evolved to recombine every {last['recomb_every']} cycles with mutation step <= {last['max_steps']};")
print(f"            final agents {[a for a, _ in last['agents']]}")

section("Final controllers found (seed 0, 4,800 units)")
for name, _, _ in METHODS:
    r = results[(name, 4800)]["runs"][0]
    print(f"  {name:14s} held-out {r['heldout']:3d}/100  {r['program']}")

# ---------------------------------------------------------------- figures
fig = ROOT / "docs" / "figures"
fig.mkdir(parents=True, exist_ok=True)
items = []
for name, _, headline in METHODS:
    ho = [r["heldout"] for r in results[(name, 4800)]["runs"]]
    items.append((name, mean(ho), std(ho), headline))
items.insert(0, ("seed program", seed_rep.solved, 0, False))
(fig / "showdown_heldout.svg").write_text(bar_chart(items, "Held-out instances solved (of 100), 4,800-unit budget, mean ± sd over 5 seeds",
                                                     "held-out solved"))
series = []
for name, _, _ in METHODS:
    runs = results[(name, 4800)]["runs"]
    grid = list(range(0, 4801, 200))
    pts = []
    for g in grid:
        vals = []
        for r in runs:
            curve = r["_result"].curve
            best = max([b for u, b in curve if u <= g], default=curve[0][1])
            vals.append(best)
        pts.append((g, mean(vals)))
    series.append((name, pts))
(fig / "showdown_anytime.svg").write_text(line_chart(series, "Anytime curve: best steering score vs budget spent (mean of 5 seeds)",
                                                     "instance-simulations spent", "best steering solved (of 48)"))
print("\nwrote docs/figures/showdown_heldout.svg and docs/figures/showdown_anytime.svg")

save("10_18", {f"{n}@{b}": {"heldout": [r["heldout"] for r in v["runs"]], "steering": [r["steering"] for r in v["runs"]],
                            "delay": [r["heldout_delay"] for r in v["runs"]], "rsi_index": v["rsi_index"],
                            "units": [r["units"] for r in v["runs"]], "ledger": [r["ledger"] for r in v["runs"]],
                            "program_seed0": v["runs"][0]["program"]}
               for (n, b), v in results.items()} | {"seed_heldout": seed_rep.solved})
