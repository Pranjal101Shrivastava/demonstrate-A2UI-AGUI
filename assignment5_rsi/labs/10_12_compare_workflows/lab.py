"""Lab 10.12: compare workflow adaptation, RSIFlow (re-route the workflow) vs Self-HPO
(alternate what is optimised).

Both are measured at the same budget on the same seeds, next to Naive RSI. The table
records what each one adapts, and when each is preferable on the evidence here.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.baselines import naive_rsi  # noqa: E402
from signalforge.methods.rsiflow import rsiflow  # noqa: E402
from signalforge.methods.self_hpo import self_hpo  # noqa: E402
from signalforge.stats import fmt_ms  # noqa: E402

BUDGET = 2400
banner("LAB 10.12 · COMPARE WORKFLOW ADAPTATION: RSIFlow vs Self-HPO")

section("Measured at equal budget (8 seeds)")
runs = {"Naive RSI": run_many(naive_rsi, seeds(8), budget=BUDGET),
        "RSIFlow (adaptive routing)": run_many(rsiflow, seeds(8), budget=BUDGET),
        "Self-HPO (joint H/P)": run_many(self_hpo, seeds(8), budget=BUDGET)}
table([[n, fmt_ms([r["heldout"] for r in rs]), " ".join(str(r["heldout"]) for r in rs)] for n, rs in runs.items()],
      ["workflow", "held-out /100", "per seed"])

section("Comparison (course template, completed)")
table([
    ["Focus", "how improvement steps are routed", "which object is optimised (harness vs policy)"],
    ["Adaptation", "meta-agent re-weights routes by recent yield", "failures define the next curriculum + harness"],
    ["Iteration", "every step; discounted statistics", "strict H-step / P-step alternation"],
    ["What it needs", "several routes with different cost/yield", "a clean split between scaffold and parameters"],
    ["Preferable when", "route costs differ a lot and the bottleneck drifts", "new mechanisms need tuning before they pay"],
    ["Seen here", "tracks the bottleneck, no final-score gain (10.13)", "joint >> either half alone; gains add up (10.14)"],
], ["aspect", "RSIFlow", "Self-HPO"])

save("10_12", {n: [r["heldout"] for r in rs] for n, rs in runs.items()})
