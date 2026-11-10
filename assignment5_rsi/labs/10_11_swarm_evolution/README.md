# 10.11 · Simulate swarm evolution (SwarmRSI)

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/03_scaling_coordination/step_03_swarm/README.md) · Group 03 · SwarmRSI (arXiv:2610.20431) · **headline method 3** ·
run: `python labs/10_11_swarm_evolution/lab.py` (~65 s)

**Goal.** Implement the course's 5-agent swarm skeleton (`SwarmAgent.mutate`, `recombine`) with all three SwarmRSI mechanisms, then find out by
ablation which one carries the result.

## Code walkthrough ([`signalforge/methods/swarm_rsi.py`](../../signalforge/methods/swarm_rsi.py))
| Mechanism | Code | Detail |
|---|---|---|
| research directions | `DIRECTIONS` | fairness (starvation guard + cap), responsive (actuated + skip-empty), pressure, timing, explorer. Each has a starting hypothesis and operator preferences. |
| feedback-guided mutation | `Swarm.mutate` | weight(op) = own preference × clip(exp(0.3 × mean Δ of op on the shared **board**), 0.5, 2). Accept → preference ×1.5; reject → ×0.85 (the hypothesis is refined). |
| complementary recombination | `Swarm.recombine` | choose the pair maximising Σ_f max(a_f, b_f) − max(Σa, Σb) over per-family solve vectors. The child takes each mechanism from the parent stronger on the families in `SERVES[c]`, and replaces the weakest agent if better. |
| recursive swarm evolution | `Swarm.evolve_procedure` | compare gain per unit of mutation vs recombination → move `recomb_every` (1–6). If no agent gained this cycle, widen `max_steps`. |
| diversity | `Swarm.diversity` | mean pairwise `program_distance` (logged per cycle, used in 10.17) |

## Execution (excerpt)
```text
cycle  6 units 1392 best 33/48 div 2.51 recomb_every 6 agents [31, 32, 33, 21, 22]  recomb {'parents': ('responsive', 'pressure'), ... 'child_solved': 31, 'replaced': 'fairness'}
cycle  9 units 1824 best 39/48 ...
variant                    held-out /100
full SwarmRSI              78.0 ± 7.2
no shared board            79.2 ± 5.9
no recombination           80.8 ± 4.1
frozen procedure           79.4 ± 6.3
same start for all agents  71.1 ± 8.4
```

## What it shows
* Recombination does produce real hybrids: the `responsive × pressure` child (actuated + pressure + skip-empty) became one of the top agents.
* **But the ablation is the honest answer to "what carries it?"** At 2,400 units, removing the board, recombination or procedure evolution
  changes the result by +1 to +3, within noise. **Removing the diversity of starting hypotheses costs −6.9.** The swarm's value here is parallel
  exploration of different mechanism families. The recombination/feedback machinery would need a larger budget, or more agents, to pay for itself.
* Diversity does not collapse during the run (2.36 → 2.81, lab 10.17).

**Next →** [Group 04 · 10.12 Compare workflow adaptation](../10_12_compare_workflows/README.md)
