"""Shared helpers for the lab scripts: headings, tables, multi-seed runs, result files."""
import json
import os
import time
from pathlib import Path

from .evaluator import SearchEvaluator, final_report
from .stats import mean, std

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "docs" / "results"
FAST = os.environ.get("RSI_FAST") == "1"     # RSI_FAST=1: fewer seeds, for quick checks


def seeds(n):
    return list(range(min(n, 2) if FAST else n))


def banner(title, sub=""):
    print("=" * 78)
    print(title)
    if sub:
        print(sub)
    print("=" * 78)


def section(title):
    print()
    print(f"--- {title} " + "-" * max(0, 72 - len(title)))


def table(rows, headers):
    cols = [[str(h)] + [str(r[i]) for r in rows] for i, h in enumerate(headers)]
    w = [max(len(c) for c in col) for col in cols]
    line = lambda xs: "  ".join(str(x).ljust(w[i]) for i, x in enumerate(xs))
    print(line(headers))
    print(line(["-" * x for x in w]))
    for r in rows:
        print(line(r))


def run_many(fn, seed_list, budget=None, label=None, **kw):
    """Run fn(ev, seed=s, **kw) for each seed. Held-out is read only after search returns."""
    out = []
    for s in seed_list:
        ev = SearchEvaluator(budget=budget)
        t0 = time.time()
        res = fn(ev, seed=s, **kw)
        ho = final_report(res.best, who=label or res.method)
        out.append({"seed": s, "method": label or res.method, "steering": res.best_report.solved,
                    "heldout": ho.solved, "heldout_delay": round(ho.mean_delay, 2),
                    "units": ev.ledger.units, "ledger": dict(ev.ledger.by_purpose),
                    "program": res.best.summary(), "seconds": round(time.time() - t0, 2),
                    "heldout_by_family": ho.by_family(), "_result": res})
    return out


def summarize(runs):
    ho = [r["heldout"] for r in runs]
    st = [r["steering"] for r in runs]
    return {"heldout_mean": round(mean(ho), 1), "heldout_std": round(std(ho), 1), "heldout_all": ho,
            "steering_mean": round(mean(st), 1), "units_mean": round(mean([r["units"] for r in runs]))}


def save(lab, data):
    RESULTS.mkdir(parents=True, exist_ok=True)
    clean = json.loads(json.dumps(data, default=lambda o: None))
    (RESULTS / f"{lab}.json").write_text(json.dumps(clean, indent=1))
    print(f"\n[saved docs/results/{lab}.json]")
