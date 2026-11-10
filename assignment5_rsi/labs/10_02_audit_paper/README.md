# 10.02 · Audit an October 2026 paper (SO-RSI)

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/00_reading_frontier_research/step_02_audit_paper/README.md) · Group 00 · run: `python labs/10_02_audit_paper/lab.py` (~12 s)
· deliverable: [`paper_audit_so_rsi.md`](paper_audit_so_rsi.md)

**Goal.** Fill the course audit template for one paper (SO-RSI, arXiv:2610.05701). Then pick one assumption it makes but does not report on,
and **measure it** in our adaptation instead of just listing it.

## Code walkthrough (`lab.py`)
1. `AUDIT` is the completed template, kept as data next to the code it describes: changed object, feedback, evaluation protocol, budget,
   baseline, untested assumptions. It is printed with `labkit.table`.
2. The assumption under test: *"diagnostic probes are lightweight."* `run_many(so_rsi, seeds(8), budget=2400)` runs our SO-RSI.
   Its evaluator's ledger tags every probe evaluation with `purpose="probe"` (see `SORSI._probe_score` in
   [`so_rsi.py`](../../signalforge/methods/so_rsi.py)), so the probe share of the budget can be read straight off the ledger.

## Execution (excerpt)
```text
seed  units  probe units  probe share  # probes  held-out
0     2361   739          31%  ...                96
...
Probes consume 35% of the budget on average ...
```
(Exact per-seed rows: [EXECUTION_LOG](../../docs/EXECUTION_LOG.md#10_02_audit_paper).)

## What it shows
Probes are **not** free: about a third of SO-RSI's compute goes on asking *why*. That makes the head-to-head in 10.06/10.18 meaningful. SO-RSI
pays for its diagnosis out of the same budget as Naive RSI, and still wins. Some runs stop early (e.g. 1,696 units) because inquiry memory
has banned or refuted every reachable edit: the method has converged.

## Quiz
**Q1. Why identify untested assumptions before implementing?** Implementation effort should go to the most uncertain parts. Here the cost of
probes was the obvious one, so the ledger was built to measure it from the start.
**Q2. Can a laptop adaptation prove a headline claim?** No. It can show the mechanism is sound under a fair protocol. Our +24.5 instances (10.06)
is in a different domain and at a different scale from the paper's +21.8 / +25.8 pp, so only the direction is comparable.

**Next →** [10.03 Run Budget RSI](../10_03_run_budget_rsi/README.md)
