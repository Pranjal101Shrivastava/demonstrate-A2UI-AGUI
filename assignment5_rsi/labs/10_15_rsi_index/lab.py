"""Lab 10.15: calculate RSIGym's RSI-Index (arXiv:2610.10310).

RSI-Index = mean over benchmarks of (final - initial) / (ideal - initial): the fraction of
the *remaining* gap that the RSI system closed.

  1. the course's worked example (should give 0.5)
  2. a note on the formula as printed on the course page
  3. the lab task: a synthetic scenario with 5 benchmarks
  4. on SignalForge: the 8 traffic families are 8 benchmarks, and the three headline
     methods each get a run at the same budget
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import final_report  # noqa: E402
from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.budget_rsi import budget_rsi  # noqa: E402
from signalforge.methods.so_rsi import so_rsi  # noqa: E402
from signalforge.methods.swarm_rsi import swarm_rsi  # noqa: E402
from signalforge.metrics import rsi_index  # noqa: E402
from signalforge.program import SEED_PROGRAM  # noqa: E402
from signalforge.scenarios import FAMILIES  # noqa: E402
from signalforge.stats import mean  # noqa: E402

banner("LAB 10.15 · RSI-INDEX: FRACTION OF THE REMAINING GAP CLOSED")

section("1. Course worked example")
idx, per = rsi_index({"b1": 0.50, "b2": 0.20}, {"b1": 0.75, "b2": 0.60})
print(f"per benchmark {per} -> RSI-Index = {idx:.2f}   (expected 0.50)")

section("2. The formula as printed on the course page")
print("The lab page writes  mean( (initial - final) / (ideal - initial) ). Applied to the same")
wrong = mean([(0.50 - 0.75) / 0.50, (0.20 - 0.60) / 0.80])
print(f"example it gives {wrong:+.2f}: improvement would read as negative. The worked example on that page")
print("uses (final - initial), which is what signalforge/metrics.py implements (and tests).")

section("3. Lab task: synthetic scenario, 5 benchmarks")
init = {"swe": 0.18, "kernel": 0.40, "math": 0.62, "web": 0.30, "data": 0.85}
final = {"swe": 0.50, "kernel": 0.52, "math": 0.70, "web": 0.29, "data": 0.93}
idx, per = rsi_index(init, final)
table([[b, init[b], final[b], f"{final[b] - init[b]:+.2f}", f"{per[b]:+.3f}"] for b in init],
      ["benchmark", "initial", "final", "raw gain", "gap closed"])
print(f"RSI-Index = {idx:.3f}. 'data' gained +0.08 raw but closed {per['data']:.0%} of its gap; 'web' regressed and counts negative.")

section("4. SignalForge: 8 traffic families as benchmarks, budget 2400, 3 seeds per method")
seed_rep = final_report(SEED_PROGRAM, who="lab10.15-seed").by_family()
rows, out = [], {}
for name, fn in (("Budget RSI", budget_rsi), ("SO-RSI", so_rsi), ("SwarmRSI", swarm_rsi)):
    runs = run_many(fn, seeds(3), budget=2400)
    idxs = [rsi_index(seed_rep, r["heldout_by_family"])[0] for r in runs]
    fam = {f: mean([r["heldout_by_family"][f] for r in runs]) for f in FAMILIES}
    out[name] = {"rsi_index": idxs, "heldout": [r["heldout"] for r in runs], "by_family": fam}
    rows.append([name, f"{mean([r['heldout'] for r in runs]):.1f}", f"{mean(idxs):.3f}"] +
                [f"{fam[f]:.2f}" for f in FAMILIES])
rows.insert(0, ["seed program", "31.0", "0.000"] + [f"{seed_rep[f]:.2f}" for f in FAMILIES])
table(rows, ["method", "held-out", "RSI-Index"] + [f[:9] for f in FAMILIES])
print("\nnight_sparse and balanced_light start at 1.00 (no gap), so they are excluded from the mean,")
print("as RSIGym's definition implies. A method that regresses there is penalised only in the raw score.")

save("10_15", {"example": 0.5, "synthetic": idx, "signalforge": out, "seed_by_family": seed_rep})
