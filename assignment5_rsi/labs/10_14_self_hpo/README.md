# 10.14 · Simulate Self-HPO's harness/policy alternation

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/04_adaptive_workflows/step_03_selfhpo/README.md) · Group 04 · Self-HPO (arXiv:2610.22791) · run: `python labs/10_14_self_hpo/lab.py` (~21 s)

**Goal.** Implement alternating H-steps and P-steps on our task, and test the claim that harness and policy are mutually reinforcing.

## Code walkthrough ([`signalforge/methods/self_hpo.py`](../../signalforge/methods/self_hpo.py))
* **Harness** = the mechanisms wrapped around the controller + the curriculum. **Policy** = its constants.
* `curriculum()`: the policy's failures on steering become the **hard set**. The next training set = hard set + 8 passed instances (a regression check).
* `h_step()`: the policy proposes harness candidates (toggle each mechanism, keeping the constants) and scores them on the curriculum.
  The best is adopted only if it also improves the full steering split.
* `p_step()`: coordinate search over every active constant (±1, ±2 grid steps) on the curriculum, adopted if better on the full split.
* Modes: `policy_only` (harness frozen at fixed-time), `harness_only` (constants frozen), `joint` (H, P, H, P...).

## Execution (excerpt)
```text
H-step  hard set 32  adopted=True  best=32/48  add pressure
P-step  hard set 16  adopted=True  best=36/48  [pressure] min_green=6, fixed_green=35, pressure_ratio=4.5
...
policy_only   43.0 ± 0.0  +12.0
harness_only  66.0 ± 0.0  +35.0
joint         78.2 ± 2.1  +47.2
synergy test: joint gain +47.2 vs policy gain + harness gain = +47.0 -> joint ~= sum: the gains add up, but no synergy beyond that
```

## What it shows
* **Alternation is needed:** joint beats the better half by +12.2. The fixed-time harness gives the policy almost nothing to tune (+12), and new
  mechanisms with default constants stall at 66.
* The hard set shrinks as the loop works (32 → 8 failing instances), so the curriculum keeps targeting the policy's *current* failure modes.
* The paper reports synergy (joint gain > sum of the parts). **We measure additivity, not synergy**: the verdict uses a 2-instance noise margin
  rather than reading +0.2 as a finding.

**Next →** [Group 05 · 10.15 RSI-Index](../10_15_rsi_index/README.md)
