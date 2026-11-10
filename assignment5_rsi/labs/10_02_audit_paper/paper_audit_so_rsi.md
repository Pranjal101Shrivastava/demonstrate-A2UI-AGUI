# Paper audit: SO-RSI, Second-Order Problem Solving for RSI (arXiv:2610.05701)

| Aspect | Paper's setup (course summary) | Our laptop adaptation | What's preserved |
|---|---|---|---|
| Changed object | agent workflow, edited at the level of mechanisms ("second-order") | controller program source: mechanisms + constants ([`program.py`](../../signalforge/program.py)) | edits that target *mechanisms*, not only surface parameters |
| Feedback type | Lean 4 / Verus execution traces | per-instance simulator results (family, failing constraint) + the improver's own edit trace | recurrence / opposing / mismatch detection on the trace |
| Evaluation protocol | 24 h search; held-out proofs | search on 48 steering instances; 100 held-out instances read once, after search | held-out boundary (enforced in `evaluator.py` and unit-tested) |
| Compute budget | 24 h per comparison | 2,400 instance-simulations (~2 s CPU) per run; probes charged | identical budget for both arms |
| Baseline | Naive RSI (first-order patching) | `naive_rsi()`: same proposal operators and acceptance rule | only the inquiry layer differs |
| Diagnosis | LLM-driven diagnostic probes | anomaly-gated sweeps on failing instances + a 3-entry mechanism map | probe → evidence → finding → systematic edit |

**Untested assumptions**
1. *Probes are lightweight.* **Measured in lab 10.02:** about 35% of the budget. Not negligible, yet still net-positive (10.06).
2. *The diagnosis needs domain knowledge (the LLM's).* **Tested in lab 10.07:** removing our mechanism map changes held-out by -0.2, so the gain
   comes from anomaly-gated sweeps. Whether an LLM's diagnosis adds more than that is untested here.
3. *Inquiry memory transfers.* **Tested across rounds only (10.07 §3):** +4.3 held-out instances in round 2. Transfer across *domains* is untested.
4. *Anomaly gating matters.* **Tested (10.07):** probing after every failure is ~10 instances worse at the same budget.

**Laptop constraints.** Synthetic but physically meaningful traffic; operators instead of an LLM; a hand-written 3-entry mechanism map.
**What would test the remaining assumptions:** swap the mechanism map for an LLM-written diagnosis at equal cost, and run round 2 of inquiry
on a different intersection geometry.
