"""Lab 10.05: extend the scorer to our task, and make the improver improve itself.

Three extensions, each against the paper-style readout from lab 10.03 (40 expansions,
same seeds):

  (a) task-specific features: per-constant signed change + per-mechanism add/remove.
      These are still static diff features. Does feature choice matter?
  (b) online refit, the recursive step: every expansion becomes a new labelled example,
      and the readout (part of the improver) is refitted, so the improver revises its
      own selection rule as it goes.
  (c) negative control (README quiz Q1): shuffle the training labels so the features no
      longer carry information. The scorer should fall to about random.
"""
import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.diff_features import RICH_FEATURE_NAMES, diff_features, rich_diff_features  # noqa: E402
from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, save, section, seeds, table  # noqa: E402
from signalforge.methods import budget_rsi as B  # noqa: E402
from signalforge.stats import fmt_ms, mean  # noqa: E402

banner("LAB 10.05 · EXTEND THE SCORER: TASK FEATURES, ONLINE REFIT, NEGATIVE CONTROL")

CONFIGS = [
    ("paper readout (8 generic, frozen)", dict(rich=False, refit=False, shuffle=False, mode="readout")),
    ("(b) + online refit (recursive)", dict(rich=False, refit=True, shuffle=False, mode="readout")),
    ("(a) task-specific features (19)", dict(rich=True, refit=False, shuffle=False, mode="readout")),
    ("(a)+(b) task features + refit", dict(rich=True, refit=True, shuffle=False, mode="readout")),
    ("(c) shuffled labels (control)", dict(rich=False, refit=False, shuffle=True, mode="readout")),
    ("random selector (reference)", dict(rich=False, refit=False, shuffle=False, mode="random")),
]

section("Task-specific readout coefficients (seed 0)")
rows_rich = B.collect_scaffold_edits(SearchEvaluator(), 0, featurize=rich_diff_features)
ro_rich = B.train_readout(rows_rich, features=RICH_FEATURE_NAMES, all_names=RICH_FEATURE_NAMES)
top = sorted(((k, v) for k, v in ro_rich.coefficients().items() if k not in ("bias",)), key=lambda kv: -abs(kv[1]))[:10]
table([[k, f"{v:+.3f}"] for k, v in top], ["coordinate", "weight"])
co = ro_rich.coefficients()
print(f"Reading it: dlog_GAP_OUT = {co['dlog_GAP_OUT']:+.3f}, dlog_MAX_GREEN = {co['dlog_MAX_GREEN']:+.3f} "
      f"(negative = shrinking that constant is predicted to help);")
print(f"toggle_gapped_out = {co['toggle_gapped_out']:+.3f}, toggle_outweighed = {co['toggle_outweighed']:+.3f} "
      "(which mechanisms the improver now believes in).")
print("The 8 generic coordinates cannot express this: 'decrease gap_out' and 'increase gap_out'")
print("produce identical line/function/branch counts.")

section("Search results, 40 expansions, same seeds")
results = {}
for name, c in CONFIGS:
    fz, names = (rich_diff_features, RICH_FEATURE_NAMES) if c["rich"] else (diff_features, None)
    hos, sps = [], []
    for s in seeds(6):
        ro = None
        if c["mode"] == "readout":
            rows = B.collect_scaffold_edits(SearchEvaluator(), s, featurize=fz)
            kw = dict(features=names, all_names=names) if names else {}
            ro = B.train_readout(rows, label_noise_seed=(s if c["shuffle"] else None), **kw)
        out = B.search(SearchEvaluator(), copy.deepcopy(ro), c["mode"], seed=s, max_expansions=40,
                       online_refit=c["refit"], featurize=fz)
        hos.append(final_report(out.best, who="lab10.05").solved)
        sps.append(out.extras.get("readout_spearman") or 0.0)
    results[name] = {"heldout": hos, "spearman": sps}
table([[n, fmt_ms(r["heldout"]), f"{mean(r['spearman']):+.2f}", " ".join(map(str, r["heldout"]))] for n, r in results.items()],
      ["configuration", "held-out /100", "pred-vs-real Spearman (expanded)", "per seed"])

base = mean(results[CONFIGS[0][0]]["heldout"])
print()
for n, r in results.items():
    print(f"  {n:36s} {mean(r['heldout']) - base:+5.1f} vs paper readout")
print("\n(The Spearman column is computed only over the children each search chose to expand, a")
print(" selected sample, so it understates ranking quality; lab 10.04 measures it properly.)")

save("10_05", {"results": results, "rich_top_coefficients": top})
