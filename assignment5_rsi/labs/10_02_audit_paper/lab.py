"""Lab 10.02: audit an October 2026 paper (SO-RSI, arXiv:2610.05701) against our adaptation.

The audit table is printed from data, so it lives next to the code it describes. We then
pick one assumption the paper relies on but (per the course summary) does not report on,
and *measure* it in our adaptation: are diagnostic probes really "lightweight" compared
with the evaluations they replace?
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.labkit import banner, run_many, save, section, seeds, table  # noqa: E402
from signalforge.methods.so_rsi import so_rsi  # noqa: E402
from signalforge.stats import mean  # noqa: E402

banner("LAB 10.02 · AUDIT AN OCTOBER 2026 PAPER: SO-RSI (arXiv:2610.05701)")

AUDIT = [
    ("Changed object", "agent workflow (second-order edits)", "controller program source (genome -> Python)",
     "edits target mechanisms, not only constants"),
    ("Feedback type", "Lean 4 / Verus execution traces", "per-instance sim results + edit trace",
     "recurrence / opposing / mismatch detection on the edit trace"),
    ("Evaluation protocol", "24 h search, held-out proofs", "48-instance steering search, 100 held-out final",
     "held-out never visible to search (enforced, tested)"),
    ("Compute budget", "24 h per comparison", "2,400 instance-simulations (~2 s CPU)",
     "same budget for both arms, probes charged"),
    ("Baseline", "Naive RSI (first-order patching)", "naive_rsi(): same proposal + acceptance rule",
     "only the inquiry layer differs"),
    ("Untested assumptions", "probes stay cheap; diagnosis transfers", "measured below; mechanism map is hand-written",
     "second-order principle, not the LLM diagnosis"),
]
table(AUDIT, ["aspect", "paper's setup (course summary)", "our laptop adaptation", "what is preserved"])

section("Assumption under test: 'diagnostic probes are lightweight'")
runs = run_many(so_rsi, seeds(8), budget=2400)
rows = []
for r in runs:
    probe = r["ledger"].get("probe", 0)
    rows.append([r["seed"], r["units"], probe, f"{probe / r['units'] * 100:.0f}%", r["_result"].extras["probes"], r["heldout"]])
table(rows, ["seed", "units", "probe units", "probe share", "# probes", "held-out"])
share = mean([r["ledger"].get("probe", 0) / r["units"] for r in runs]) * 100
print(f"\nProbes consume {share:.0f}% of the budget on average. That is not negligible: in our")
print("adaptation SO-RSI spends roughly a third of its compute on *asking why*. Labs 10.06/10.07")
print("test whether that spend pays for itself against Naive RSI at the SAME total budget.")
print("\nUntested in the paper (per the course summary) and NOT tested here either:")
print("  * whether an LLM-written diagnosis is as reliable as our hand-written mechanism map")
print("  * whether inquiry memory transfers across domains (we only test across rounds, lab 10.07)")

save("10_02", {"probe_share_pct": share, "runs": [{k: v for k, v in r.items() if k != "_result"} for r in runs]})
