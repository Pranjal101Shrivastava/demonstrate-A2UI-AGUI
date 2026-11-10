"""Lab 10.09: compare the two scaling designs, AReaL-RSI (leader-follower) vs SwarmRSI (peer swarm).

The comparison table is filled with numbers measured on SignalForge, at the same
budget and on the same seeds as a single-agent baseline (Naive RSI). Labs 10.10 and 10.11
then take each design apart.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.areal_rsi import areal_rsi  # noqa: E402
from signalforge.methods.baselines import naive_rsi  # noqa: E402
from signalforge.methods.swarm_rsi import swarm_rsi  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

BUDGET = 2400
banner("LAB 10.09 · COMPARE SCALING APPROACHES: AReaL-RSI vs SwarmRSI")

section("Measured at equal budget (2,400 instance-sims, 8 seeds)")
runs = {"single agent (Naive RSI)": run_many(naive_rsi, seeds(8), budget=BUDGET),
        "AReaL-RSI (leader + 2 specialists)": run_many(areal_rsi, seeds(8), budget=BUDGET),
        "SwarmRSI (5 peers)": run_many(swarm_rsi, seeds(8), budget=BUDGET)}
table([[n, fmt_ms([r["heldout"] for r in rs]), fmt_ms([r["units"] for r in rs], 0), " ".join(str(r["heldout"]) for r in rs)]
       for n, rs in runs.items()], ["design", "held-out /100", "units actually used", "per seed"])

section("Comparison table (course template, completed)")
a = mean([r["units"] for r in runs["AReaL-RSI (leader + 2 specialists)"]])
table([
    ["Coordination", "leader picks orientation; specialists execute", "peers in parallel, no leader"],
    ["Memory", "conditional: resolved vs unresolved findings", "shared experience board of op outcomes"],
    ["Evolution", "evidence-based review between campaigns", "mutation + complementary recombination"],
    ["Selection", "leader-guided, verified on full split", "competitive: child replaces the weakest"],
    ["Key advantage (seen here)", "cheap: probes slices first, stops when memory is exhausted",
     "diverse starting hypotheses avoid a single basin"],
    ["Key limitation (seen here)", f"converges early (used {a:.0f} of {BUDGET} units); specialists are narrow",
     "5 agents split the budget, so each gets few evaluations"],
    ["Choose it when", "a clear objective and decomposable failure slices", "the right mechanism is unknown, so search wide"],
], ["aspect", "AReaL-RSI", "SwarmRSI"])

save("10_09", {n: [r["heldout"] for r in rs] for n, rs in runs.items()})
