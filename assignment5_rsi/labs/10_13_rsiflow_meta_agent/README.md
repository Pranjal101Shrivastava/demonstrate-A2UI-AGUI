# 10.13 · Simulate the RSIFlow meta-agent

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/04_adaptive_workflows/step_02_rsiflow/README.md) · Group 04 · RSIFlow (arXiv:2610.21791) · run: `python labs/10_13_rsiflow_meta_agent/lab.py` (~38 s)

**Goal.** Implement "a simple workflow graph with adaptive routing", with a meta-agent that finds the bottleneck and evolves itself, and test whether it helps.

## Code walkthrough ([`signalforge/methods/rsiflow.py`](../../signalforge/methods/rsiflow.py))
* **Workflow graph** (`ROUTES`): `tune>full`, `struct>full`, `tune>screen>full`, `struct>screen>full`, `diagnose>targeted>full`. *screen* = a 16-instance
  fit-split filter before paying for 48 steering instances; *diagnose* = read the incumbent's failures (free) and target the mechanism family that serves them.
* **Meta-agent** (`Flow.choose_route`): UCB on **discounted** gain per unit (γ = 0.9 per step). Old evidence fades because the bottleneck moves:
  early on, new mechanisms pay; later, their constants do. A re-proposed cached edit still costs a turn (8 units), so stale routes look stale.
* **Capability evolution:** if more than 80% of screened candidates then fail the full evaluation, the meta-agent rewrites its own screen rule from
  "not worse" to "strictly better" (`screen_strict`).
* `adaptive=False`: uniform random routing (the static workflow).

## Execution (excerpt)
```text
route                   steps 1st third  2nd third  3rd third  gain per 1000 units (lifetime)
tune>full               9                10         8          20.8
struct>full             14               10         8          18.5 ...
share of steps on structural routes by third: 41% -> 41% -> 30%
screen rule rewritten by the meta-agent: yes (now strict)
adaptive meta-agent     76.4 ± 8.4
static uniform routing  76.4 ± 10.7
difference: +0.0 held-out instances.
```

## What it shows (a negative result, reported as measured)
The meta-agent does what it is designed to do. It shifts away from structural routes as mechanisms saturate (41% → 30%), and it tightens its own
screening rule. But over 12 seeds the final controller is **exactly as good as with random routing**. Every route draws on the same edit operators,
so routing changes *when* an edit is tried more than *which* edits are reachable. A first version that used lifetime (undiscounted) yields was
*worse* than static: one early lucky structural win locked it onto that route. This is a concrete instance of the "evolving bottleneck" problem
RSIFlow is about.

**Next →** [10.14 Self-HPO alternation](../10_14_self_hpo/README.md)
