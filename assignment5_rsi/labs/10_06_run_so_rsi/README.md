# 10.06 · Run SO-RSI: diagnose before patching

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/02_second_order_diagnostics/step_01_run_demo/README.md) · Group 02 *Second-order RSI* (arXiv:2610.05701) · **headline method 2** ·
run: `python labs/10_06_run_so_rsi/lab.py` (~25 s)

**Goal.** Run SO-RSI against Naive RSI where **the only difference is the inquiry layer**: the same operators, acceptance rule, simulator and
2,400-unit budget. Probes are charged to that budget.

## Code walkthrough ([`signalforge/methods/so_rsi.py`](../../signalforge/methods/so_rsi.py))
`SORSI.run` loop, one iteration:
1. `propose()`: take a pending *systematic* edit recommended by a probe if there is one. Otherwise a random edit, excluding operators the
   memory has banned for this incumbent; if it adds a mechanism whose constant the memory has already tuned, use that constant.
2. evaluate on steering; `delta` = solved(child) − solved(incumbent); accept if strictly better (the same rule as `baselines.naive_rsi`).
3. log a trace row with the operator, delta and `expected` = running mean of that operator's past deltas (prior +1 for "add a mechanism").
4. `detect(trace)`: **recurrence** (the same operator already failed in the last 8), **opposing** (the inverse operator on the same target failed in the last 5),
   **mismatch** (expected ≥ +0.5 but delta ≤ −2, or the reverse).
5. dispatch a probe. Each runs on `_probe_set()` = the instances the incumbent *fails* + 6 it passes (a regression check), charged as `probe`:
   * `probe_mechanism(c)`: mismatch/recurrence on "add c": sweep c's constant. If one value works → tuned constant + pending edit; else ban.
   * `probe_direction(p)`: recurrence on a nudge: sweep p across its range. A jump target, or "exhausted" (ban both directions).
   * `probe_structure()`: opposing / other mismatches: attribute failures (wait vs delay, light vs heavy families) and test the mechanisms
     `MECHANISMS` lists for the dominant signature.
6. a probe recommendation that later loses on the full split is recorded as **refuted** and never re-proposed.

## Execution (excerpt; full narrated trace in [EXECUTION_LOG](../../docs/EXECUTION_LOG.md#10_06_run_so_rsi))
```text
step   5 [explore] decrease min_green 8->6        delta= -1  reject  anomalies=['recurrence']
step   6 [probe  ] set min_green=4                delta= +0  ACCEPT
step   7 [explore] increase min_green 4->6        delta= -1  reject  anomalies=['opposing']
step   8 [probe  ] add max_cap (max_green=60)     delta= +9  ACCEPT     <- structure probe: 'wait' failures dominate
step   9 [explore] add pressure                   delta= -6  reject  anomalies=['mismatch']
...
step   7 opposing   structure_probe(wait)  dominant failure signature = wait {'wait': 23, 'delay_light': 0, 'delay_heavy': 8}
          best variants: add max_cap (max_green=60) -> 15, ...
Naive RSI made 475 proposals; anomalies it walked straight past: {'recurrence': 269, 'opposing': 40, 'mismatch': 51}
Naive RSI (first-order)  35.6 ± 2.5   68.9 ± 7.2   81 61 61 73 72 73 68 62
SO-RSI (second-order)    45.1 ± 2.5   93.4 ± 7.0   96 97 76 96 96 96 95 95
```

## What it shows
* The decisive moment comes at step 7. An *opposing* pair on MIN_GREEN triggers failure attribution: 23 of the failures are "someone waited > 70 s".
  The structure probe then finds that a **max-green cap with MAX_GREEN = 60** fixes 9 of them. A first-order loop would need to add `max_cap`
  (worthless at its default of 90) *and then* walk the constant down 3 steps, with no reward along the way.
* Run passively over Naive RSI, the same detector flags 360 anomalies that Naive RSI simply walks past.
* **+24.5 held-out instances at equal budget** (≈ the paper's +21.8 / +25.8 pp, in a different domain). Held-out delay also falls, 13.6 → 11.3 s.

## Quiz
**Q1. Key difference?** Naive RSI patches symptoms. SO-RSI notices *patterns in its own failures* and runs experiments about why before editing.
**Q2. Why synthetic traces in the course demo?** Ours are not synthetic: the trace is the real edit history of a real search, and every outcome
comes from the simulator. (See 10.01 for why that matters.)

**Next →** [10.07 Analyse diagnostic probes](../10_07_analyze_probes/README.md)
