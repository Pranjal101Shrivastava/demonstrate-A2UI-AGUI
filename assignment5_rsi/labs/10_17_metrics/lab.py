"""Lab 10.17: analyse the new metrics from the October 2026 papers, measured on SignalForge.

    RSI-Index (RSIGym)                     fraction of the remaining gap closed (lab 10.15)
    steering-split solve rate (Budget RSI) a cheap proxy for held-out: is it valid?
    Recursive Learnability (R2Orch)        which tasks are worth training on?
    swarm diversity (SwarmRSI)             is the swarm still exploring?
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, save, section, table  # noqa: E402
from signalforge.methods.swarm_rsi import swarm_rsi  # noqa: E402
from signalforge.metrics import recursive_learnability, steering_validity  # noqa: E402
from signalforge.program import random_program  # noqa: E402
from signalforge.scenarios import FAMILIES  # noqa: E402
from signalforge.stats import mean  # noqa: E402

banner("LAB 10.17 · ANALYSE THE OCTOBER 2026 RSI METRICS")

rng = random.Random(17)
population = []
keys = set()
while len(population) < 60:
    p = random_program(rng, depth=rng.randint(1, 10))
    if p.key not in keys:
        keys.add(p.key)
        population.append(p)
ev = SearchEvaluator()

section("Steering-split solve rate: validity as a proxy (60 random programs)")
pairs = []
steer_reports = []
for p in population:
    r = ev.run(p)
    steer_reports.append(r)
    pairs.append((r.rate, final_report(p, who="lab10.17-analysis").rate))
v = steering_validity(pairs)
print(f"Spearman(steering, held-out) = {v['spearman']:+.2f}")
print(f"steering winner: {v['winner_steering']:.2f} on steering vs {v['winner_heldout']:.2f} held-out "
      f"(difference {v['winner_overstatement'] * 100:+.1f} points)")
import json  # noqa: E402
from signalforge.labkit import RESULTS  # noqa: E402
try:
    sel = json.loads((RESULTS / "10_01.json").read_text())["selection_effect"]
except (OSError, KeyError, ValueError):
    sel = float("nan")
print(f"Across 60 *unselected* programs the 48-instance proxy ranks well (rho={v['spearman']:+.2f}). The optimism")
print(f"appears under search pressure: in lab 10.01 the program a search selected scored {sel:+.1f} points")
print("higher on steering than on held-out. A proxy can be valid on average and still biased for")
print("the programs you pick with it.")

section("Recursive Learnability: which families separate good from bad policies?")
outcomes = {f: [] for f in FAMILIES}
for r in steer_reports:
    for x in r.results:
        outcomes[x["family"]].append(int(x["solved"]))
rl = recursive_learnability(outcomes)
table([[f, f"{mean(outcomes[f]):.2f}", f"{rl[f]:.2f}"] for f in sorted(FAMILIES, key=lambda f: -rl[f])],
      ["family", "mean solve rate across policies", "learnability 4p(1-p)"])
print("Families at the top are where candidate policies disagree, so they are the most informative to")
print("train on. night_sparse (almost everyone solves it) teaches nothing; R2Orch would drop it.")

section("Swarm diversity over a SwarmRSI run (budget 2400, seed 0)")
sw = swarm_rsi(SearchEvaluator(budget=2400), seed=0)
d = [r["diversity"] for r in sw.trace]
print("diversity by cycle: " + " ".join(f"{x:.2f}" for x in d))
print(f"start {d[0]:.2f} -> end {d[-1]:.2f}. In this run diversity does not collapse: the agents keep")
print("different research directions, which is what lab 10.11 found carries the swarm's result.")

section("Summary")
table([
    ["RSI-Index", "raw gains are not comparable across benchmarks", "comparing systems on mixed benchmarks",
     "undefined at ceiling; hides regressions on solved tasks", "see 10.15"],
    ["Steering solve rate", "full evaluation is too expensive", "cheap selection during search",
     "optimistic for the programs a search selects", f"rho={v['spearman']:+.2f} (10.01: {sel:+.1f} pts optimism)"],
    ["Recursive Learnability", "which tasks to self-train on", "curriculum / task proposal",
     "needs a population of policies; myopic", f"top: {max(rl, key=rl.get)}"],
    ["Swarm diversity", "premature convergence of a swarm", "tuning swarm size / recombination",
     "distance metric is a design choice", f"{d[0]:.2f} -> {d[-1]:.2f}"],
], ["metric", "problem it solves", "useful when", "limitation", "measured here"])

save("10_17", {"steering_validity": v, "learnability": rl, "swarm_diversity": d})
