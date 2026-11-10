# 10.17 · Analyse the October 2026 metrics

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/05_environments_metrics/step_03_metrics/README.md) · Group 05 · run: `python labs/10_17_metrics/lab.py` (~7 s)

**Goal.** For each new metric, state the problem it solves, when it is useful and its limitations, **with a measurement on our task**.

## Code walkthrough ([`signalforge/metrics.py`](../../signalforge/metrics.py))
* **Steering solve rate (Budget RSI):** `steering_validity` takes 60 random distinct programs and computes Spearman(steering rate, held-out rate) and the
  steering winner's over/under-statement. This is analysis only: these programs are not chosen by any search.
* **Recursive Learnability (R2Orch):** `recursive_learnability` scores each family by 4p(1−p) of its outcomes across the 60-policy population.
  1 means policies split 50/50 (informative to train on); 0 means all or none solve it.
* **Swarm diversity (SwarmRSI):** the per-cycle `diversity` from a swarm run.
* **RSI-Index (RSIGym):** see 10.15.

## Execution (excerpt)
```text
Spearman(steering, held-out) = +0.97
Across 60 *unselected* programs the 48-instance proxy ranks well ... in lab 10.01 the program a search selected scored +5.8 points higher on steering than on held-out.
am_rush_ramp    0.53   1.00
platoon_pulses  0.74   0.77 ...
night_sparse    0.96   0.14
diversity by cycle: 2.36 2.61 ... 2.81
```
plus the summary table (metric, problem, useful when, limitation, measured here).

## What it shows
* The steering proxy is **valid on average (ρ = 0.97) yet optimistic for the programs a search picks with it** (+5.8 points, 10.01). Both facts matter.
* Learnability gives a training curriculum for free: the morning ramp and platoon traffic separate good controllers from bad; night traffic teaches nothing.
* **Q1. Why so many metrics?** Each RSI system changes a different object (scorer, workflow, swarm, harness), and each metric answers a different
  failure mode: incomparable gains, expensive evaluation, uninformative tasks, premature convergence.

**Next →** [10.18 Three methods head to head](../10_18_three_method_showdown/README.md)
