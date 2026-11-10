# 10.10 · Simulate leader-follower coordination (AReaL-RSI)

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/03_scaling_coordination/step_02_simulate/README.md) · Group 03 · AReaL-RSI (arXiv:2610.18083) ·
run: `python labs/10_10_leader_follower/lab.py` (~11 s)

**Goal.** Implement the course's 3-agent skeleton (`LeaderAgent`, `ResearcherAgent`, `ConditionalMemory`) on a real task, and test the paper's
claim that experience sharing beats independent exploration.

## Code walkthrough ([`signalforge/methods/areal_rsi.py`](../../signalforge/methods/areal_rsi.py))
* `ORIENTATIONS`: 4 research orientations = slices of the traffic families (light, heavy-balanced, asymmetric, surge).
* `Team.leader_select`: score = priority × (failures in the slice) / (1 + 0.5 × unresolved findings there).
* `Researcher.propose`: R1 has the *structure* skill (toggles mechanisms), R2 the *tuning* skill (moves constants 1–`max_steps`). Edits already
  recorded as unresolved are skipped.
* `Team.investigate`: evaluate on **the orientation's slice only** (cheap). If the slice improves, verify on the full steering split. The result is stored
  in `ConditionalMemory` as **resolved** (adopted by the whole team) or **unresolved** (helped locally, regressed globally: never retried).
* `Team.review` (evidence-based review after each campaign): orientation priority ×1.2 if something was resolved, ×0.6 if not. The tuning
  researcher widens its step size when small steps fail.
* `sharing=False`: each researcher has a private incumbent and memory, and orientations are chosen at random (the paper's control).
* Stops when 8 campaigns in a row find nothing new to test.

## Execution (excerpt)
```text
campaign  1 units 216 orientation=heavy_balanced resolved=['add pressure', 'increase min_green 8->10', 'increase min_green 10->12'] best=34/48
orientation     resolved  unresolved  leader priority after review ...
unresolved findings that helped LOCALLY but regressed the full split:
  [light_traffic ] add actuated              local +1, full split delta -6
  [light_traffic ] decrease fixed_green 40->25  local +1, full split delta -8
leader + conditional memory (shared)  73.6 ± 6.0
independent researchers               66.0 ± 0.0
Sharing beats independent exploration by 11.6% here (paper: 1.9-27.5%).
```

## What it shows
* **Conditional memory earns its keep.** "Add actuated helps light traffic (+1 locally) but costs 6 overall" is exactly the kind of finding that must be
  remembered as *unresolved*, so nobody adopts it, and also not lost.
* The independent condition is stuck at 66 for every seed: the structure specialist can add pressure but never tune it, and the tuning specialist can
  never add a mechanism. Only the shared incumbent lets each build on the other's resolved work.

**Next →** [10.11 Swarm evolution](../10_11_swarm_evolution/README.md)
