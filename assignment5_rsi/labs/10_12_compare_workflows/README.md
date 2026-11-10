# 10.12 · Compare workflow adaptation: RSIFlow vs Self-HPO

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/04_adaptive_workflows/step_01_compare/README.md) · Group 04 *Adaptive workflows* · run: `python labs/10_12_compare_workflows/lab.py` (~35 s)

**Goal.** Distinguish the two ways of adapting an improvement workflow, and say when each is preferable, backed by a same-budget measurement.

* **RSIFlow** adapts *how improvement steps are routed* (which proposal → screen → evaluate path to use next): [`rsiflow.py`](../../signalforge/methods/rsiflow.py).
* **Self-HPO** adapts *which object is being optimised*, alternating harness (mechanisms + failure curriculum) and policy (constants):
  [`self_hpo.py`](../../signalforge/methods/self_hpo.py).

## Execution
```text
workflow                    held-out /100  per seed
Naive RSI                   68.9 ± 7.2     81 61 61 73 72 73 68 62
RSIFlow (adaptive routing)  77.2 ± 9.9     72 73 79 83 74 62 79 96
Self-HPO (joint H/P)        78.2 ± 2.1     79 79 79 79 79 79 73 79
```
plus the completed comparison table (focus, adaptation, iteration, what it needs, when preferable, what we saw).

## What it shows
Similar means, very different character. Self-HPO is almost deterministic (sd 2.1): it alternates a fixed schedule over a curriculum of hard
instances, so it reliably reaches the same plateau. RSIFlow's spread is large (62–96): its route choice depends on early luck. Prefer **Self-HPO**
when new mechanisms need tuning before they pay off (true here, by construction). Prefer **RSIFlow** when routes differ a lot in cost and the
bottleneck drifts. 10.13 shows that its routing on its own does not beat random routing here.

**Next →** [10.13 RSIFlow meta-agent](../10_13_rsiflow_meta_agent/README.md)
