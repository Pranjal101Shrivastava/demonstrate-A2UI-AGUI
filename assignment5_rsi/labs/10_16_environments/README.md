# 10.16 · Compare environments, with SignalForge as Everything-as-a-Service

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/05_environments_metrics/step_02_environments/README.md) · Group 05 · run: `python labs/10_16_environments/lab.py` (< 1 s)

**Goal.** Identify when RSIGym (EaaS), Terminal-RSI (terminal infrastructure) and R2Orch (self-play) are appropriate. Then give our own
environment RSIGym's key property: capabilities behind services with **shared budget and permission controls**.

## Code walkthrough ([`signalforge/services.py`](../../signalforge/services.py))
`Services(budget, permissions)` wraps the evaluator:
* `simulate(program, instance_id)` / `evaluate(program, split)`: charged to the budget, restricted to the fit/steering boundary;
* `sandbox_exec(source)`: compiles untrusted controller code with **no builtins except max/min/abs**, then checks that `decide()` exists and returns a bool;
* `heldout(program)`: only with the `final` permission (given to a reviewer *after* search, never to the agent).
The lab plays an agent session with a 200-unit budget and no `final` permission, logging every call.

## Execution
```text
sandbox_exec(valid controller)     ok       {'ok': True, 'returns': False}
sandbox_exec('import os ...')      ok       {'ok': False, 'error': 'ImportError: __import__ not found'}
simulate(seed, held-out instance)  REFUSED  ServiceError: unknown or out-of-boundary instance night_sparse#9006
evaluate(good, 'heldout')          REFUSED  PermissionError: split 'heldout' is outside the search boundary
heldout(good)                      REFUSED  ServiceError: permission denied: 'final' is not granted to this agent
evaluate(seed, 'steering') x4      REFUSED  BudgetExhausted: needs 48 units, 39 left
after search, a reviewer with the 'final' permission: heldout(good) = 90/100
```
Then the comparison table: interface, what is improved, budget/permissions, metric, laptop feasibility, use it when.

## What it shows
The environment, not the agent's good manners, is what keeps a self-improving system honest. Every RSI comparison in this assignment relies on
these same boundaries. **Use RSIGym-style EaaS** to compare many RSI agents fairly, **Terminal-RSI** when agents act through shells (not
laptop-feasible: PPO/GAE/async), and **R2Orch** when task choice is the bottleneck (its metric appears in 10.17).

**Next →** [10.17 Analyse metrics](../10_17_metrics/README.md)
