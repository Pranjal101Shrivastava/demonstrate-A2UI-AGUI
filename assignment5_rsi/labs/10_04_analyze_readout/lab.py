"""Lab 10.04: analyse the scoring mechanism. Which coordinates matter, and does the readout rank?

The selection decision only ever compares *siblings* (children of one parent), so the
question that matters is within-sibling ranking, not overall R^2. We build a test bench:
12 parents taken from a real Budget RSI search tree, 8 children each, and ALL 96
children evaluated on steering (analysis cost only, the method never pays it). Then:

  * coefficient ranking, raw and scaled by each feature's spread
  * within-sibling Spearman and top-1 regret, against a random pick
  * the README's questions: 8 -> 4 features, 96 -> 48 -> 24 training edits
  * distribution shift: a readout trained on random-walk parents (the 'shifted' scaffold)
"""
import pathlib
import random
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.diff_features import FEATURE_NAMES, diff_features  # noqa: E402
from signalforge.evaluator import SearchEvaluator, final_report  # noqa: E402
from signalforge.labkit import banner, save, section, seeds, table  # noqa: E402
from signalforge.methods import budget_rsi as B  # noqa: E402
from signalforge.program import random_edit  # noqa: E402
from signalforge.stats import fmt_ms, mean, spearman, std  # noqa: E402

banner("LAB 10.04 · ANALYSE THE SCORING MECHANISM")

ev = SearchEvaluator()
rows = B.collect_scaffold_edits(ev, seed=0)
ro = B.train_readout(rows)

section("Feature importance (seed-0 readout)")
spread = {f: std([r[1][i] for r in rows]) for i, f in enumerate(FEATURE_NAMES)}
spread["parent_rate"] = std([r[0] for r in rows])
coef = {k: v for k, v in ro.coefficients().items() if k != "bias"}
ranked = sorted(coef.items(), key=lambda kv: abs(kv[1]) * spread[kv[0]], reverse=True)
table([[k, f"{v:+.3f}", f"{spread[k]:.3f}", f"{abs(v) * spread[k]:.3f}"] for k, v in ranked],
      ["coordinate", "weight", "feature std", "|weight| x std (importance)"])

section("Build the sibling test bench from real search trees (12 parents x 8 children)")
# Parents are nodes that HGM actually expanded in Budget RSI and random-selector searches, so
# the bench measures the readout where it is used. We take 12 spread across quality levels.
pool = {}
for s_ in (0, 1, 2):
    for mode, r_ in (("readout", ro), ("random", None)):
        t = B.search(SearchEvaluator(), r_, mode, seed=s_, max_expansions=30)
        for x in t.trace:
            pool[x["program"].key] = (x["real"], x["program"])
ordered = sorted(pool.values(), key=lambda v: v[0])
parents = [ordered[int(i * (len(ordered) - 1) / 11)][1] for i in range(12)]
rng = random.Random(42)
bench_ev = SearchEvaluator()
bench = []
for p in parents:
    prate = bench_ev.run(p).rate
    kids = []
    for _ in range(100):
        e = random_edit(p, rng)
        if all(e.child.key != k.child.key for k in kids) and e.child.key != p.key:
            kids.append(e)
        if len(kids) == 8:
            break
    bench.append((p, prate, [(e, bench_ev.run(e.child).rate) for e in kids]))
print(f"{len(bench)} parents (steering rates {min(b[1] for b in bench):.2f}-{max(b[1] for b in bench):.2f}), "
      f"{sum(len(k) for _, _, k in bench)} children, {bench_ev.ledger.units} instance-sims (analysis only)")


def validity(readout, featurize=diff_features, subset=None):
    sp, regret, rand_regret = [], [], []
    for p, prate, kids in (subset or bench):
        scores = [readout.score(prate, featurize(p.source, e.child.source)) for e, _ in kids]
        actual = [a for _, a in kids]
        if len(set(actual)) > 1:
            sp.append(spearman(scores, actual))
        pick = max(range(len(kids)), key=lambda i: scores[i])
        regret.append(max(actual) - actual[pick])
        rand_regret.append(max(actual) - mean(actual))
    return mean(sp), mean(regret) * 48, mean(rand_regret) * 48


section("Within-sibling validity of the paper-style readout")
sp, reg, rreg = validity(ro)
print(f"mean within-sibling Spearman : {sp:+.2f}")
print(f"top-1 regret (readout pick)  : {reg:.2f} steering instances below the best sibling")
print(f"top-1 regret (random pick)   : {rreg:.2f}")

section("README questions: fewer features, fewer training edits, shifted scaffold")
variants = []
four = ("lines_added", "lines_deleted", "funcs_added", "funcs_deleted")
variants.append(("8 features, 96 edits (paper)", ro))
variants.append(("4 features (lines/funcs only)", B.train_readout(rows, features=four)))
variants.append(("parent_rate only (ablation)", B.train_readout(rows, features=())))
for n in (48, 24):
    variants.append((f"8 features, {n} edits", B.train_readout(rows[:n])))
shifted_rows = B.collect_scaffold_edits(SearchEvaluator(), seed=0, regime="random")
shifted = B.train_readout(shifted_rows)
variants.append(("8 features, SHIFTED scaffold", shifted))
weak = [b for b in bench if b[1] < 0.7]       # parents a random walk tends to produce
strong = [b for b in bench if b[1] >= 0.7]    # parents HGM spends most of its expansions on
out = []
for name, r in variants:
    s_, g_, _ = validity(r)
    sw, gw, _ = validity(r, subset=weak)
    ss, gs, _ = validity(r, subset=strong)
    out.append({"variant": name, "spearman": round(s_, 3), "regret": round(g_, 2),
                "spearman_weak": round(sw, 3), "spearman_strong": round(ss, 3), "regret_strong": round(gs, 2)})
print(f"weak parents (<0.70 steering): {len(weak)}   strong parents (>=0.70): {len(strong)}")
table([[o["variant"], f"{o['spearman']:+.2f}", f"{o['spearman_weak']:+.2f}", f"{o['spearman_strong']:+.2f}",
        f"{o['regret']:.2f}", f"{o['regret_strong']:.2f}"] for o in out],
      ["readout variant", "Spearman all", "on weak parents", "on strong parents", "regret all", "regret strong"])

section("Does validity predict search outcome? shifted vs climb scaffold, 40 expansions")
search_rows = []
for name, regime in (("climb scaffold", "climb"), ("shifted scaffold", "random")):
    hos = []
    for s in seeds(6):
        rr = B.collect_scaffold_edits(SearchEvaluator(), s, regime=regime)
        o = B.search(SearchEvaluator(), B.train_readout(rr), "readout", seed=s, max_expansions=40)
        hos.append(final_report(o.best, who="lab10.04").solved)
    search_rows.append([name, fmt_ms(hos), " ".join(map(str, hos))])
table(search_rows, ["readout trained on", "held-out /100", "per seed"])
paper_sp = out[0]["spearman_strong"]
shift_sp = out[-1]["spearman_strong"]
print(f"\nOn STRONG parents: climb-trained Spearman {paper_sp:+.2f} vs shifted {shift_sp:+.2f}; "
      f"on weak parents: {out[0]['spearman_weak']:+.2f} vs {out[-1]['spearman_weak']:+.2f}.")
if shift_sp < paper_sp:
    print("The shifted readout learned from random-walk (mostly weak) parents. It ranks children of")
    print("weak parents well, but HGM's Thompson sampling spends its expansions on strong parents,")
    print("where that readout's preferences no longer hold. The readout is only as good as the match")
    print("between the edits it was trained on and the edits the search actually asks it about.")
else:
    print("Sibling ranking alone does not separate the two readouts here; the search gap comes from")
    print("which edit TYPES each readout systematically prefers (see the coefficient tables).")

save("10_04", {"importance": ranked, "variants": out, "search": search_rows,
               "validity": {"spearman": sp, "regret": reg, "random_regret": rreg}})
