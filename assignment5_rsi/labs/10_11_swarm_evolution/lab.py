"""Lab 10.11: simulate SwarmRSI's evolving agent swarm (arXiv:2610.20431).

Five agents (fairness, responsive, pressure, timing, explorer) improve controllers in parallel.
  1. one run narrated: per cycle best score, swarm diversity, the swarm's own procedure
     settings (recombination interval, mutation step size), and every recombination
  2. ablations at equal budget, 8 seeds: remove the shared board (feedback-guided
     mutation), remove recombination, freeze the procedure (no recursive evolution),
     or give every agent the same starting hypothesis (no diversity of directions)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.swarm_rsi import DIRECTIONS, swarm_rsi  # noqa: E402
from signalforge.stats import fmt_ms  # noqa: E402

BUDGET = 2400
banner("LAB 10.11 · SWARM EVOLUTION: MUTATION, RECOMBINATION, RECURSIVE PROCEDURE (SwarmRSI)")
for name, (start, prefs) in DIRECTIONS.items():
    print(f"  {name:10s} starts with {sorted(start) or ['fixed-time']}, prefers {prefs or 'nothing (uniform)'}")

section("1. One run (seed 0)")
res = swarm_rsi(SearchEvaluator(budget=BUDGET), seed=0, verbose=True)
print("\nfinal agents:")
for name, summ, solved in res.extras["agents"]:
    print(f"  {name:24s} {solved:2d}/48  {summ}")
ho = final_report(res.best, who="lab10.11")
print(f"swarm best: {res.best.summary()}  held-out {ho.solved}/100")
div = [(r["cycle"], r["diversity"]) for r in res.trace]

section("2. Which swarm mechanism carries the result? (8 seeds, same budget)")
variants = [("full SwarmRSI", {}), ("no shared board", {"use_board": False}),
            ("no recombination", {"use_recombination": False}), ("frozen procedure", {"evolve": False}),
            ("same start for all agents", {"diverse_starts": False})]
rows, out = [], {}
for name, kw in variants:
    rs = run_many(swarm_rsi, seeds(8), budget=BUDGET, **kw)
    out[name] = [r["heldout"] for r in rs]
    rows.append([name, fmt_ms(out[name]), " ".join(map(str, out[name]))])
table(rows, ["variant", "held-out /100", "per seed"])

full = sum(out["full SwarmRSI"]) / len(out["full SwarmRSI"])
print()
for name, v in out.items():
    print(f"  {name:28s} {sum(v) / len(v) - full:+5.1f} vs full")
print("\nRead it as an ablation: a mechanism matters only if removing it costs held-out instances.")

save("10_11", {"diversity_seed0": div, "ablations": out,
               "recombinations_seed0": [r["recombination"] for r in res.trace if r["recombination"]]})
