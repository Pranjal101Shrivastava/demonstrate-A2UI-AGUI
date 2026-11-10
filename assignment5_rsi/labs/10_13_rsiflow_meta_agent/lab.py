"""Lab 10.13: simulate RSIFlow's evolving meta-agent (arXiv:2610.21791).

The improvement workflow is a graph of five routes (see signalforge/methods/rsiflow.py).
  1. one run: which routes the meta-agent used in each third of the run, as the
     bottleneck moved, and whether it rewrote its own screening rule
  2. adaptive meta-agent vs a static workflow (uniform routing), 12 seeds, same budget
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.rsiflow import ROUTES, rsiflow  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

BUDGET = 2400
banner("LAB 10.13 · RSIFlow: A META-AGENT THAT RE-ROUTES THE IMPROVEMENT WORKFLOW")

section("1. One adaptive run (seed 0): route usage as the bottleneck moves")
res = rsiflow(SearchEvaluator(budget=BUDGET), seed=0)
h = [x for x in res.trace if x["units"] <= BUDGET]
thirds = [h[: len(h) // 3], h[len(h) // 3: 2 * len(h) // 3], h[2 * len(h) // 3:]]
rows = []
for r in ROUTES:
    rows.append([r] + [collections.Counter(x["route"] for x in t)[r] for t in thirds]
                + [f"{res.extras['route_yield_per_1000_units'][r]:.1f}"])
table(rows, ["route", "steps 1st third", "2nd third", "3rd third", "gain per 1000 units (lifetime)"])
print("\naccepted improvements, in order:")
for x in h:
    if x["gain"] > 0:
        print(f"  step {x['step']:3d} via {x['route']:24s} {x['desc']:32s} -> {x['best']}/48")
struct_share = [sum(1 for x in t if x["route"].startswith("struct")) / max(len(t), 1) for t in thirds]
print(f"\nshare of steps on structural routes by third: " + " -> ".join(f"{v:.0%}" for v in struct_share))
print(f"screen rule rewritten by the meta-agent: {'yes (now strict)' if res.extras['screen_strict'] else 'no'}")
print(f"held-out of the result: {final_report(res.best, who='lab10.13').solved}/100")

section("2. Adaptive meta-agent vs static workflow (12 seeds, same budget)")
ad = run_many(rsiflow, seeds(12), budget=BUDGET)
st = run_many(rsiflow, seeds(12), budget=BUDGET, adaptive=False)
table([[n, fmt_ms([r["heldout"] for r in rs]), " ".join(str(r["heldout"]) for r in rs)]
       for n, rs in (("adaptive meta-agent", ad), ("static uniform routing", st))], ["workflow", "held-out /100", "per seed"])
d = mean([r["heldout"] for r in ad]) - mean([r["heldout"] for r in st])
print(f"\ndifference: {d:+.1f} held-out instances.")
print("Honest reading: the meta-agent re-weights routes as their recent yield changes (part 1), but")
print("at this scale routing alone does not buy a better final controller than routing at random.")
print("Every route uses the same proposal operators, so re-routing changes WHEN an edit is tried")
print("more than WHICH edits are reachable.")

save("10_13", {"adaptive": [r["heldout"] for r in ad], "static": [r["heldout"] for r in st],
               "usage_by_third": rows, "screen_strict": res.extras["screen_strict"]})
