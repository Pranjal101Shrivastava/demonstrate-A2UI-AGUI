"""Lab 10.10: simulate AReaL-RSI's leader-follower team with conditional memory (arXiv:2610.18083).

1 leader + 2 researchers (R1 toggles mechanisms, R2 tunes constants) on SignalForge.
  1. one run narrated: campaign by campaign, with the leader's orientation and what was resolved
  2. the conditional memory at the end: resolved vs unresolved findings
  3. the paper's scaling claim at laptop scale: shared experience vs independent researchers,
     same budget, 8 seeds
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.areal_rsi import ORIENTATIONS, areal_rsi  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

BUDGET = 2400
banner("LAB 10.10 · LEADER-FOLLOWER COORDINATION WITH CONDITIONAL MEMORY (AReaL-RSI)")
print("orientations the leader can choose:", {k: sorted(v) for k, v in ORIENTATIONS.items()})

section("1. One run (seed 0): the campaigns that resolved something")
res = areal_rsi(SearchEvaluator(budget=BUDGET), seed=0, verbose=True)
print(f"  ({len(res.trace)} campaigns in total; the rest resolved nothing and are omitted)")
print("  leader orientation choices:", dict(collections.Counter(c['orientation'] for c in res.trace)))

section("2. Conditional memory at the end")
mem = res.extras["memory"]
by = collections.Counter((e["orientation"], e["status"]) for e in mem.entries)
table([[o, by[(o, "resolved")], by[(o, "unresolved")], f"{res.extras['priorities'][o]:.2f}"] for o in ORIENTATIONS],
      ["orientation", "resolved", "unresolved", "leader priority after review"])
print("\nresolved findings (adopted team-wide, retrieved by everyone):")
for e in [e for e in mem.entries if e["status"] == "resolved"][:8]:
    print(f"  [{e['orientation']:14s}] {e['desc']:36s} local {e['local_gain']:+d}, full split delta {e['global_delta']:+d}")
print("unresolved findings that helped LOCALLY but regressed the full split (kept so nobody retries them):")
for e in [e for e in mem.entries if e["status"] == "unresolved" and e["global_delta"] is not None][:6]:
    print(f"  [{e['orientation']:14s}] {e['desc']:36s} local {e['local_gain']:+d}, full split delta {e['global_delta']:+d}")
ho = final_report(res.best, who="lab10.10")
print(f"\nteam result: {res.best.summary()}  steering {res.best_report.solved}/48, held-out {ho.solved}/100")

section("3. Shared experience vs independent researchers (same budget, 8 seeds)")
shared = run_many(areal_rsi, seeds(8), budget=BUDGET)
indep = run_many(areal_rsi, seeds(8), budget=BUDGET, sharing=False)
table([[n, fmt_ms([r["heldout"] for r in rs]), " ".join(str(r["heldout"]) for r in rs)]
       for n, rs in (("leader + conditional memory (shared)", shared), ("independent researchers", indep))],
      ["condition", "held-out /100", "per seed"])
gain = mean([r["heldout"] for r in shared]) / mean([r["heldout"] for r in indep]) * 100 - 100
print(f"\nSharing beats independent exploration by {gain:.1f}% here (paper: 1.9-27.5%).")
print("Why: a structure specialist alone never tunes a constant, and a tuning specialist alone")
print("never adds a mechanism. Only the shared incumbent lets each build on the other's resolved work.")

save("10_10", {"shared": [r["heldout"] for r in shared], "independent": [r["heldout"] for r in indep],
               "memory_counts": {f"{o}:{s}": n for (o, s), n in by.items()}})
