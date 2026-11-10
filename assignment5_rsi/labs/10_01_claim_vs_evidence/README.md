# 10.01 · Distinguish claim from evidence

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/00_reading_frontier_research/step_01_claim_vs_evidence/README.md) · Group 00 *Read a frontier claim* · run: `python labs/10_01_claim_vs_evidence/lab.py` (~12 s)

**Goal.** A headline score does not prove a mechanism. Before rebuilding any October 2026 method, we practise separating
*what is claimed*, *what was measured*, and *what remains untested*. We do it twice: on paper text
([`claim_evidence_analysis.md`](claim_evidence_analysis.md), the lab's required deliverable for Budget RSI), and with code.

## Code walkthrough (`lab.py`)
1. **Check A: audit the course's own SO-RSI demo.** In `12_october_2026_papers/02_second_order_rsi/demo.py`, `NaiveRSI.attempt_fix`
   draws `success if random() < 0.3` and `SORSI.attempt_fix` draws `success if random() < 0.5`. Its diagnostics only *print*.
   `reference_like(p)` reproduces those coin flips **with the anomaly detector deleted**, 200 repeats × 20 attempts.
   If the ~20-point "improvement" survives, the mechanism did not cause it.
2. **Check B: one run vs the distribution.** `run_many(naive_rsi, seeds(10), budget=2400)` (from `signalforge/labkit.py`) runs Naive RSI on
   SignalForge with 10 seeds. Each run's best program is evaluated on the 100 held-out instances only *after* the search returns.
   We print the best seed (what a headline would quote) next to mean ± sd (what the evidence supports), and the
   **selection effect**: the steering score of the program a search *selected* exceeds its held-out score.

## Execution (excerpt; full output in [EXECUTION_LOG](../../docs/EXECUTION_LOG.md#10_01_claim_vs_evidence))
```text
Naive RSI (p=0.3)                          30.0 ± 9.5
'SO-RSI' with diagnostics DELETED (p=0.5)  48.8 ± 11.5
The ~19-point gap survives with no diagnostics at all ...
Headline a paper could print : 'reaches 81/100 held-out' (best seed 0)
What the evidence supports   : 69.2 ± 7.5 over 10 seeds
Selection effect             : the chosen program's steering % exceeds its held-out % by +5.8 points on average
```

## What it shows
* The reference demo *assumes* its result. So every comparison in this assignment runs both arms through the **same simulator,
  operators, budget and splits**, and any gap has to come from the method.
* A single seed can overstate a method by 12 points. Every result from here on is reported as mean ± sd over seeds.
* Selecting on the steering split makes its score optimistic (+5.8). That is why the held-out split is a hard boundary
  (`signalforge/evaluator.py`, enforced by `tests/test_signalforge.py::test_no_method_reads_heldout`).

## Quiz
**Q1. Can Budget RSI claim linear readout scoring works for all code-editing tasks?** No. The paper tested HumanEval+/Polyglot with GPT-4o.
On our controller task the readout's advantage over its ablation is +2.9 ± noise (lab 10.03), and it *reverses* under distribution shift (lab 10.04).
**Q2. Why do laptop demos use synthetic data?** To make the mechanism executable without GPT-4o or the benchmarks. SignalForge goes one step further:
its "edits" are real source diffs, scored by a real simulator, so a mechanism can visibly fail.

**Next →** [10.02 Audit an October 2026 paper](../10_02_audit_paper/README.md)
