"""Lab 10.16: compare RSI environments, and expose SignalForge RSIGym-style (Everything as a Service).

  1. the same capabilities the labs use, behind service calls with budget and permission
     controls (signalforge/services.py), exercised the way an agent would, refusals included
  2. the comparison table: RSIGym vs Terminal-RSI vs R2Orch, and what SignalForge offers of each
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import BudgetExhausted  # noqa: E402
from signalforge.labkit import banner, save, section, table  # noqa: E402
from signalforge.program import SEED_PROGRAM, Program  # noqa: E402
from signalforge.services import ServiceError, Services  # noqa: E402

banner("LAB 10.16 · ENVIRONMENTS: SignalForge AS EVERYTHING-AS-A-SERVICE")
log = []


def call(label, fn):
    try:
        out = fn()
        log.append((label, "ok", str(out)[:70]))
    except (ServiceError, BudgetExhausted, PermissionError) as exc:
        log.append((label, "REFUSED", f"{type(exc).__name__}: {exc}"[:70]))


section("1. An agent session with a 200-unit budget and no 'final' permission")
svc = Services(budget=200)
good = Program(on=frozenset({"actuated", "max_cap"}), gap_out=3, max_green=50)
call("sandbox_exec(valid controller)", lambda: svc.sandbox_exec(good.source))
call("sandbox_exec('import os ...')", lambda: svc.sandbox_exec("import os\ndef decide(s):\n    return os.getcwd()"))
call("sandbox_exec(no decide())", lambda: svc.sandbox_exec("X = 1\n"))
call("simulate(seed, one instance)", lambda: svc.simulate(SEED_PROGRAM, svc.ev.split("steering")[5].iid))
call("simulate(seed, held-out instance)", lambda: svc.simulate(SEED_PROGRAM, "night_sparse#9006"))
call("evaluate(good, 'fit')", lambda: f"{svc.evaluate(good, 'fit').solved}/16 solved")
call("evaluate(good, 'heldout')", lambda: svc.evaluate(good, "heldout"))
call("heldout(good)", lambda: svc.heldout(good))
call("evaluate(seed, 'steering') x4", lambda: [svc.evaluate(Program(min_green=m), "steering").solved for m in (6, 10, 12, 14)])
table(log, ["service call", "status", "result"])
print(f"\nunits spent: {svc.spent} of 200; calls: {len(svc.calls)}")
svc2 = Services(budget=None, permissions=("evaluate", "final"))
print(f"after search, a reviewer with the 'final' permission: heldout(good) = {svc2.heldout(good).solved}/100")

section("2. Which environment for which RSI study?")
table([
    ["Interface", "services (train/infer/rollout/eval/sandbox)", "a real terminal + RL infrastructure", "self-play arena", "Python services (above)"],
    ["Improves", "data, harness, or both (3 tracks)", "actor policy (RSR) + critic (RPR)", "orchestrator + its own improver", "controller program"],
    ["Budget/permissions", "shared budget + permission controls", "not the focus", "not the focus", "unit budget + 'final' permission"],
    ["Metric", "RSI-Index", "task success over cycles", "Recursive Learnability", "solve rate, RSI-Index (10.15)"],
    ["Laptop-feasible", "metric + EaaS idea only", "no (PPO, GAE, async)", "toy version only", "yes, about 1 ms per instance"],
    ["Use it when", "comparing many RSI agents fairly", "agents act through shells", "task choice is the bottleneck", "teaching the mechanisms"],
], ["", "RSIGym", "Terminal-RSI", "R2Orch", "SignalForge (ours)"])

save("10_16", {"session": log})
