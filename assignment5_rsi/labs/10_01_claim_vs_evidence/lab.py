"""Lab 10.01: distinguish a claim from its evidence, with two executable checks.

Check A re-runs the logic of the course's reference SO-RSI demo with its diagnostics
switched OFF. If the "improvement" survives, the demo's mechanism did not cause it.

Check B shows on our own benchmark how a single-run headline differs from a
multi-seed measurement, and how the steering score of a selected winner overstates its
held-out score (the selection effect).
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.labkit import banner, run_many, save, section, seeds, summarize, table  # noqa: E402
from signalforge.methods.baselines import naive_rsi  # noqa: E402
from signalforge.stats import mean, std  # noqa: E402

banner("LAB 10.01 · CLAIM vs EVIDENCE",
       "Problem area: SignalForge, a self-improving traffic-signal controller (see ../../README.md)")

section("Check A: does the reference SO-RSI demo measure its mechanism?")
print("The course demo (12_october_2026_papers/02_second_order_rsi/demo.py) draws outcomes as")
print("    NaiveRSI.attempt_fix:  outcome = success if random() < 0.3")
print("    SORSI.attempt_fix:     outcome = success if random() < 0.5   # diagnostics only print")
print("Below, the same two coin flips with the anomaly detector removed entirely:")


def reference_like(p_success, n=20, seed=0):
    rng = random.Random(seed)
    return sum(rng.random() < p_success for _ in range(n)) / n * 100


naive = [reference_like(0.3, seed=s) for s in range(200)]
sorsi_no_diag = [reference_like(0.5, seed=10_000 + s) for s in range(200)]
table([["Naive RSI (p=0.3)", f"{mean(naive):.1f} ± {std(naive):.1f}"],
       ["'SO-RSI' with diagnostics DELETED (p=0.5)", f"{mean(sorsi_no_diag):.1f} ± {std(sorsi_no_diag):.1f}"]],
      ["condition (200 repeats x 20 attempts)", "success rate %"])
gap = mean(sorsi_no_diag) - mean(naive)
print(f"\nThe ~{gap:.0f}-point gap survives with no diagnostics at all: the demo *assumes* the")
print("headline (+20 pp) instead of measuring it. Our SO-RSI (lab 10.06) instead runs both")
print("methods through the same simulator, so any gap has to come from the method.")

section("Check B: one lucky run vs the distribution (Naive RSI, budget 2400 units)")
runs = run_many(naive_rsi, seeds(10), budget=2400)
rows = [[r["seed"], f"{r['steering']}/48", f"{r['steering'] / 48 * 100:.1f}%", f"{r['heldout']}/100"] for r in runs]
table(rows, ["seed", "steering solved", "steering %", "held-out solved"])
s = summarize(runs)
best = max(runs, key=lambda r: r["heldout"])
print(f"\nHeadline a paper could print : 'reaches {best['heldout']}/100 held-out' (best seed {best['seed']})")
print(f"What the evidence supports   : {s['heldout_mean']} ± {s['heldout_std']} over {len(runs)} seeds")
over = mean([r["steering"] / 48 * 100 - r["heldout"] for r in runs])
print(f"Selection effect             : the chosen program's steering % exceeds its held-out % by {over:+.1f} points on average")

save("10_01", {"check_a": {"naive_mean": mean(naive), "no_diag_mean": mean(sorsi_no_diag)},
               "check_b": {k: v for k, v in s.items()}, "best_seed": best["heldout"], "selection_effect": over})
