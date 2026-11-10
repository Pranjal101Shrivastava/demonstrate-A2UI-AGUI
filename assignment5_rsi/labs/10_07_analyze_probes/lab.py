"""Lab 10.07: analyse the diagnostic probes. Which anomalies fire, what do the probes
recommend, and which part of SO-RSI produces the gain?

  1. anomaly / probe statistics over 8 seeds (README table: type, count, recommendation, why)
  2. ablations at the same budget:
       no mechanism map  the structure probe tries every mechanism (no domain knowledge)
       gate = always     probe after every failed edit (no anomaly detection)
       gate = never      never probe (inquiry layer off: Naive RSI with an unused memory)
  3. inquiry memory across RSI rounds: round 2 restarts from the seed program, with or
     without the memory round 1 accumulated
"""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.so_rsi import so_rsi  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

BUDGET = 2400
banner("LAB 10.07 · ANALYSE DIAGNOSTIC PROBES")

section("1. What fires, what it recommends, and whether it pays (8 seeds)")
runs = run_many(so_rsi, seeds(8), budget=BUDGET)
anom = collections.Counter()
concl = collections.defaultdict(collections.Counter)
src = {"explore": [0, 0, []], "probe": [0, 0, []]}
for r in runs:
    res = r["_result"]
    for t in res.trace:
        for a in t["anomalies"]:
            anom[a] += 1
        s = src[t["source"]]
        s[0] += 1
        s[1] += t["accepted"]
        if t["accepted"]:
            s[2].append(t["delta"])
    for f in res.extras["memory"].findings:
        concl[f["anomaly"]][f["probe"].split("(")[0] + ": " + f["conclusion"].split(" {")[0].split(";")[0]] += 1
WHY = {
    "recurrence": "the same nudge keeps failing: a sweep finds the value a 1-step walk never reaches",
    "opposing": "up-then-down means no single constant serves all families: look for a missing mechanism",
    "mismatch": "an 'obviously good' mechanism hurt: its default constant is wrong, so sweep it",
}
rows = []
for a in ("recurrence", "opposing", "mismatch"):
    top = concl[a].most_common(1)
    rows.append([a, anom[a], f"{top[0][0]} (x{top[0][1]})" if top else "-", WHY[a]])
table(rows, ["anomaly", "count", "most common probe -> conclusion", "why it helps"])
print()
table([[k, v[0], v[1], f"{v[1] / max(v[0], 1) * 100:.0f}%", f"{mean(v[2]):+.1f}" if v[2] else "-"] for k, v in src.items()],
      ["edit source", "proposed", "accepted", "acceptance", "mean gain when accepted"])
print("\nProbe-recommended (systematic) edits are accepted far more often than exploratory ones:")
print("the probe has already tested them on exactly the instances that were failing.")

section("2. Ablations at the same budget (8 seeds)")
abl = [("SO-RSI (full)", {}),
       ("no mechanism map", {"use_mechanism_map": False}),
       ("gate = always (probe every failure)", {"gate": "always"}),
       ("gate = never (no inquiry)", {"gate": "never"})]
abl_rows, abl_res = [], {}
for name, kw in abl:
    rs = runs if not kw else run_many(so_rsi, seeds(8), budget=BUDGET, **kw)
    probe_share = mean([x["ledger"].get("probe", 0) / x["units"] for x in rs]) * 100
    abl_res[name] = [x["heldout"] for x in rs]
    abl_rows.append([name, fmt_ms([x["heldout"] for x in rs]), f"{probe_share:.0f}%", " ".join(str(x["heldout"]) for x in rs)])
table(abl_rows, ["variant", "held-out /100", "probe share", "per seed"])

section("3. Inquiry memory across RSI rounds (round budget 1200, restart from seed program)")
mem_rows = {"round 2 WITHOUT memory": [], "round 2 WITH round-1 memory": []}
for s in seeds(6):
    r1 = so_rsi(SearchEvaluator(budget=1200), seed=s)
    memory = r1.extras["memory"]
    memory.bans.clear()                         # bans refer to round-1 incumbents; keep the knowledge
    fresh = so_rsi(SearchEvaluator(budget=1200), seed=100 + s)
    warm = so_rsi(SearchEvaluator(budget=1200), seed=100 + s, memory=memory)
    mem_rows["round 2 WITHOUT memory"].append(final_report(fresh.best, who="lab10.07").solved)
    mem_rows["round 2 WITH round-1 memory"].append(final_report(warm.best, who="lab10.07").solved)
table([[k, fmt_ms(v), " ".join(map(str, v))] for k, v in mem_rows.items()], ["condition", "held-out /100", "per seed"])
print("\nWhat carries over is causal knowledge, e.g. 'max_cap works once MAX_GREEN is ~60', not a")
print("program. Round 2 reuses it the first time it adds that mechanism.")

save("10_07", {"anomaly_counts": dict(anom), "conclusions": {k: dict(v) for k, v in concl.items()},
               "edit_sources": {k: v[:2] for k, v in src.items()}, "ablations": abl_res, "memory_rounds": mem_rows})
