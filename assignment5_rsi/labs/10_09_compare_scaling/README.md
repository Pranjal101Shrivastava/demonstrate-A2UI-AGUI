# 10.09 · Compare scaling approaches: AReaL-RSI vs SwarmRSI

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/03_scaling_coordination/step_01_compare/README.md) · Group 03 *Scaling RSI* · run: `python labs/10_09_compare_scaling/lab.py` (~30 s)

**Goal.** Complete the course comparison table (advantage, limitation, when to choose) with **measured** evidence instead of opinion.
Both multi-agent designs and a single-agent baseline run at 2,400 units on the same 8 seeds.

## Code walkthrough
`run_many(fn, seeds(8), budget=2400)` for `naive_rsi`, `areal_rsi` ([`areal_rsi.py`](../../signalforge/methods/areal_rsi.py)) and `swarm_rsi`
([`swarm_rsi.py`](../../signalforge/methods/swarm_rsi.py)). Besides held-out, we print **units actually used**, because AReaL-RSI stops when its
conditional memory says every reachable edit has been tried.

## Execution
```text
design                              held-out /100  units actually used
single agent (Naive RSI)            68.9 ± 7.2     1890 ± 457
AReaL-RSI (leader + 2 specialists)  73.6 ± 6.0     922 ± 133
SwarmRSI (5 peers)                  78.0 ± 7.2     2400 ± 0
```
followed by the completed table (coordination, memory, evolution, selection, advantage, limitation, when to choose).

## What it shows
* Both multi-agent designs beat the single agent. **AReaL-RSI does it with < 40% of the budget.** Its leader concentrates work on failure slices,
  and conditional memory stops repeats. But it converges early because each specialist is narrow.
* SwarmRSI uses the whole budget and gets further, because diverse starting hypotheses avoid a single basin (10.11 proves it by ablation).
* **Choose AReaL-RSI** when failures decompose into slices and compute is tight. **Choose SwarmRSI** when the right mechanism is unknown.

## Quiz
**Q1. When is leader-follower better?** With a clear objective and decomposable failures, and when the budget matters: it reached 73.6 with ~900 units.

**Next →** [10.10 Leader-follower coordination](../10_10_leader_follower/README.md)
