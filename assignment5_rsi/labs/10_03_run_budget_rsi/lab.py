"""Lab 10.03: run Budget RSI (arXiv:2610.29121) on SignalForge.

Walkthrough of one run, step by step, followed by the paper's comparison protocol
(the same number of expansions for every selector, several seeds):

  1. collect 96 scaffold edits, labelled on the 16-instance fit split
  2. fit the linear readout   score = w . [1, parent_rate, 8 diff coordinates]
  3. one search step in slow motion: HGM picks a parent by Thompson sampling, the parent
     proposes 8 children, and the readout scores them WITHOUT running them. Only the top
     child is evaluated.
  4. 40 expansions x {readout, parent-rate ablation, random}
  5. cost: what the readout saved
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.diff_features import FEATURE_NAMES, diff_features, unified_diff  # noqa: E402
from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, save, section, seeds, table  # noqa: E402
from signalforge.methods import budget_rsi as B  # noqa: E402
from signalforge.program import SEED_PROGRAM, random_edit  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

banner("LAB 10.03 · RUN BUDGET RSI: SCORE EDITS BEFORE RUNNING THEM")

section("Step 0: the seed program the improver starts from")
print(SEED_PROGRAM.source)
ho0 = final_report(SEED_PROGRAM, who="lab10.03-seed")
print(f"seed program held-out: {ho0.solved}/100 solved, mean delay {ho0.mean_delay:.1f} s")

section("Step 1: 96 scaffold edits labelled on the fit split (16 instances each)")
ev = SearchEvaluator()
rows = B.collect_scaffold_edits(ev, seed=0)
print(f"collected {len(rows)} labelled edits for {ev.ledger.units} instance-simulations")
for prate, feats, crate, e in rows[:: 24]:
    print(f"  parent {prate:.2f} -> child {crate:.2f}   {e.desc:34s} features={feats}")

section("Step 2: fit the linear readout (ridge least squares, stdlib)")
ro = B.train_readout(rows)
table([[k, f"{v:+.3f}"] for k, v in ro.coefficients().items()], ["coordinate", "weight"])

section("Step 3: one HGM expansion in slow motion")
rng = random.Random(3)
parent = rows[40][3].parent
prate = SearchEvaluator().run(parent).rate
print(f"parent (steering rate {prate:.2f}): {parent.summary()}")
cands = []
while len(cands) < 8:
    e = random_edit(parent, rng)
    if all(e.child.key != c.child.key for c in cands):
        cands.append(e)
ev_all = SearchEvaluator()
scored = []
for e in cands:
    f = diff_features(parent.source, e.child.source)
    actual = ev_all.run(e.child).rate                 # for teaching only: the real method never does this
    scored.append((ro.score(prate, f), actual, e.desc))
scored.sort(reverse=True)
table([[f"{s:.3f}", f"{a:.3f}", d] for s, a, d in scored], ["readout score", "actual steering rate", "edit"])
top = scored[0]
print(f"Budget RSI expands only the top-scored child ({top[2]!r}); the other 7 are never run.")
print("Its diff, which is all the scorer saw:")
best_edit = [e for e in cands if e.desc == top[2]][0]
print(unified_diff(parent.source, best_edit.child.source))

section("Step 4: the paper's protocol: 40 expansions per selector, same seeds")
N = seeds(8)
res = {"readout": [], "parent_rate": [], "random": []}
for s in N:
    ev_s = SearchEvaluator()
    rows_s = B.collect_scaffold_edits(ev_s, s)
    ro_s, ro_p = B.train_readout(rows_s), B.train_readout(rows_s, features=())
    for mode, r in (("readout", ro_s), ("parent_rate", ro_p), ("random", None)):
        out = B.search(SearchEvaluator(), r, mode, seed=s, max_expansions=40)
        ho = final_report(out.best, who=f"lab10.03-{mode}")
        res[mode].append({"seed": s, "steering": out.best_report.solved, "heldout": ho.solved,
                          "spearman": out.extras.get("readout_spearman"), "units": out.ledger.units})
rows_t = []
for mode, rs in res.items():
    rows_t.append([mode, fmt_ms([r["steering"] for r in rs]), fmt_ms([r["heldout"] for r in rs]),
                   " ".join(str(r["heldout"]) for r in rs)])
table(rows_t, ["selector", "steering /48", "held-out /100", "per seed"])
gain = mean([r["heldout"] for r in res["readout"]]) - mean([r["heldout"] for r in res["parent_rate"]])
print(f"\nReadout vs parent-rate ablation: {gain:+.1f} held-out instances (paper: 87.0% vs 84.2% on HumanEval+).")

section("Step 5: cost of a decision")
k, exp = 8, 40
full = k * exp * 48
spent = mean([r["units"] for r in res["readout"]])
print(f"Evaluate every proposed child on steering : {k} x {exp} x 48 = {full:,} instance-sims")
print(f"Budget RSI (expand top-1 only)            : {exp} x 48 = {exp * 48:,} (+ root), measured {spent:,.0f} after cache hits")
print(f"Readout labels (one-off)                  : {ev.ledger.units:,} instance-sims on the 16-instance fit split")
print(f"Saving vs evaluating all children         : {(1 - (spent + ev.ledger.units) / full) * 100:.0f}% including the readout's own labels")

save("10_03", {"coefficients": ro.coefficients(), "results": res, "seed_heldout": ho0.solved,
               "readout_label_units": ev.ledger.units})
