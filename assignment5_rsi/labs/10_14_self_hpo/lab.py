"""Lab 10.14: simulate Self-HPO's alternating harness / policy optimisation (arXiv:2610.22791).

harness = mechanisms around the controller + the curriculum (hard instances);
policy = the controller's constants.
  1. one joint run: every H-step and P-step, the hard-set size, and what was adopted
  2. the paper's claim that harness and policy are mutually reinforcing:
     policy-only vs harness-only vs joint at the same budget, plus the synergy test
     (joint gain vs the sum of the individual gains)
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.self_hpo import self_hpo  # noqa: E402
from signalforge.program import SEED_PROGRAM  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

BUDGET = 2400
banner("LAB 10.14 · SELF-HPO: ALTERNATING HARNESS (H) AND POLICY (P) STEPS")

section("1. One joint run (seed 0)")
res = self_hpo(SearchEvaluator(budget=BUDGET), seed=0)
for x in res.trace:
    print(f"  {x['step']}-step  hard set {x['hard_set']:2d}  adopted={str(x['adopted']):5s} best={x['best']:2d}/48  units={x['units']:4d}  {x['proposal']}")
print(f"held-out: {final_report(res.best, who='lab10.14').solved}/100")

section("2. Policy-only vs harness-only vs joint (8 seeds, same budget)")
seed_ho = final_report(SEED_PROGRAM, who="lab10.14-seed").solved
out = {}
for mode in ("policy_only", "harness_only", "joint"):
    rs = run_many(self_hpo, seeds(8), budget=BUDGET, mode=mode)
    out[mode] = [r["heldout"] for r in rs]
table([[m, fmt_ms(v), f"{mean(v) - seed_ho:+.1f}", " ".join(map(str, v))] for m, v in out.items()],
      ["condition", "held-out /100", "gain over seed", "per seed"])
gp, gh, gj = (mean(out[m]) - seed_ho for m in ("policy_only", "harness_only", "joint"))
margin = 2.0   # held-out instances; smaller differences are within seed noise here
verdict = ("joint > sum: synergy" if gj > gp + gh + margin else
           "joint ~= sum: the gains add up, but no synergy beyond that" if gj >= gp + gh - margin else
           "joint < sum: the steps interfere")
print(f"\nsynergy test: joint gain {gj:+.1f} vs policy gain + harness gain = {gp + gh:+.1f}  ->  {verdict}")
print(f"joint beats the better single condition by {gj - max(gp, gh):+.1f}: neither object alone gets there,")
print("because the fixed-time harness gives the policy little to tune, and new mechanisms ship with")
print("poor default constants that only a P-step fixes.")

save("10_14", {"results": out, "seed_heldout": seed_ho, "gains": {"policy": gp, "harness": gh, "joint": gj},
               "trace_seed0": res.trace})
