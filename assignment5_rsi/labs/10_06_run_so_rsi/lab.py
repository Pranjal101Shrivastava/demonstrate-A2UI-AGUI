"""Lab 10.06: run SO-RSI (arXiv:2610.05701) against Naive RSI on SignalForge.

Both arms share the same proposal operators, the same acceptance rule ("keep it if the
steering score improves"), the same simulator and the same 2,400-unit budget. The ONLY
difference is SO-RSI's inquiry layer: anomaly detection, diagnostic probes (charged to
the budget), and inquiry memory.

1. one SO-RSI run, narrated: the trace rows where something happened, then the findings
2. the same detector run *passively* over Naive RSI's trace: how much does it thrash?
3. 8 seeds x {Naive RSI, SO-RSI}
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.baselines import naive_rsi  # noqa: E402
from signalforge.methods.so_rsi import detect, so_rsi  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

BUDGET = 2400
banner("LAB 10.06 · RUN SO-RSI: DIAGNOSE BEFORE PATCHING", f"budget = {BUDGET} instance-simulations per run")

section("1. One SO-RSI run (seed 0), narrated")
ev = SearchEvaluator(budget=BUDGET)
res = so_rsi(ev, seed=0)
shown = 0
for i, t in enumerate(res.trace, 1):
    if t["accepted"] or t["anomalies"] or t["source"] == "probe":
        tag = "ACCEPT" if t["accepted"] else "reject"
        an = f"  anomalies={t['anomalies']}" if t["anomalies"] else ""
        print(f"  step {i:3d} [{t['source']:7s}] {t['desc']:44s} delta={t['delta']:+3d} expected={t['expected']:+.1f} {tag}{an}")
        shown += 1
print(f"  ... {len(res.trace) - shown} quiet steps (rejected, no anomaly) not shown")
section("   inquiry memory: findings recorded by the probes")
for f in res.extras["memory"].findings[:12]:
    ev_s = ", ".join(f"{d} -> {sc}" for d, sc in f["evidence"][:3])
    print(f"  step {f['step']:3d} {f['anomaly']:10s} {f['probe']:30s} {f['conclusion']}")
    print(f"           incumbent solves {f['incumbent_probe_score']} of the probe set; best variants: {ev_s}")
print(f"  tuned constants remembered: {res.extras['memory'].tuned}")
print(f"\nfinal program: {res.best.summary()}")
print(res.best.source)
ho = final_report(res.best, who="lab10.06")
print(f"steering {res.best_report.solved}/48 -> held-out {ho.solved}/100 (seed program: 31/100)")
print(f"budget used: {dict(ev.ledger.by_purpose)}")

section("2. The same detector, run passively over Naive RSI's trace")
nv = naive_rsi(SearchEvaluator(budget=BUDGET), seed=0)
counts = {"recurrence": 0, "opposing": 0, "mismatch": 0}
trace = []
for t in nv.trace:
    trace.append({**t, "expected": 1.0 if t["op"][0] == "add" else 0.0})
    for a in detect(trace):
        counts[a] += 1
print(f"Naive RSI made {len(nv.trace)} proposals; anomalies it walked straight past: {counts}")
print("Each one is a moment where first-order patching repeats or reverses itself without asking why.")

section("3. Eight seeds, same budget")
N = seeds(8)
naive = run_many(naive_rsi, N, budget=BUDGET)
sor = run_many(so_rsi, N, budget=BUDGET)
rows = []
for name, rs in (("Naive RSI (first-order)", naive), ("SO-RSI (second-order)", sor)):
    rows.append([name, fmt_ms([r["steering"] for r in rs]), fmt_ms([r["heldout"] for r in rs]),
                 fmt_ms([r["heldout_delay"] for r in rs]), " ".join(str(r["heldout"]) for r in rs)])
table(rows, ["method", "steering /48", "held-out /100", "held-out delay s", "per seed"])
d = mean([r["heldout"] for r in sor]) - mean([r["heldout"] for r in naive])
print(f"\nSO-RSI - Naive RSI = {d:+.1f} held-out instances at equal budget (paper reports +21.8 / +25.8 pp")
print("on Lean 4 / Verus; ours is a different domain and scale, so only the direction is comparable).")

save("10_06", {"naive": [{k: v for k, v in r.items() if k != "_result"} for r in naive],
               "so_rsi": [{k: v for k, v in r.items() if k != "_result"} for r in sor],
               "naive_anomalies_seed0": counts, "findings_seed0": res.extras["memory"].findings})
