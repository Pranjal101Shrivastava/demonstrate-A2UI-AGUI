# 10.08 · Apply SO-RSI to a debugging task (from this project)

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/02_second_order_diagnostics/step_03_apply/README.md) · Group 02 · run: `python labs/10_08_apply_debugging/lab.py` (< 1 s)

**Goal.** Follow the course's steps on a real failing test: record each fix attempt (what changed, what happened, what was expected),
analyse the trace for recurrence/opposing/mismatch, and find the root cause.

## The task
A teammate adds **T1: "a 60 s green with a long queue releases 30 vehicles" (0.5 veh/s × 60 s)** next to three existing physics tests:
T2 first departure at 2 s (start-up loss), T3 departures exactly 2 s apart, T4 nobody departs after the green ends. T1 fails: the
discharge rule (the same rule as `sim.py` step 4) releases **29**.

## Code walkthrough
1. `build(lost, headway, extra)` compiles a patched version of the discharge rule from a source template; `run_tests` executes T1–T4. Every attempt is real.
2. `ATTEMPTS`: six first-order fixes a developer typically tries, each with the expected outcome (a car count).
3. The trace goes through SO-RSI's own `detect()` for recurrence/opposing. Mismatch compares the *expected car count* with the actual one,
   because that is the quantity the developer had expectations about.
4. **Second-order probe:** search the whole space of code variants (start-up loss 0–4 × headway 1–3 × with/without off-by-one) for one that passes
   all four tests, then repeat with each test dropped in turn.

## Execution
```text
1  lost 2 -> 1 (cars start sooner)        T1 passes, nothing else changes  3/4 (fails T2; 30 cars)     -
2  lost 1 -> 2 (T2 broke, revert)         back to 3/4                      3/4 (fails T1; 29 cars)     opposing
3  range(green) -> range(green + 1)       classic off-by-one, all pass     3/4 (fails T4; 30 cars)     -
4  headway 2 -> 1 (more throughput)       one more car -> 30               2/4 (fails T1,T3; 58 cars)  mismatch
5  lost 2 -> 1 again (maybe T2 is wrong)  T1 passes                        3/4 (fails T2; 30 cars)     recurrence, opposing
6  headway 1 -> 2 (revert)                back to 3/4                      3/4 (fails T1; 29 cars)     opposing
searched 30 code variants ...: 0 pass all four
  without 'T1 60 s green -> 30 departures': 1 variant(s) pass, e.g. [(2, 2, '')]   <- the shipped code
Root cause: ... T1's author forgot the startup lost time: floor((60 - 2 - 1) / 2) + 1 = 29 vehicles. Fix the TEST.
```

## What it shows
Every first-order patch "fixed" T1 by breaking the physics that T2–T4 protect. The anomalies are the signal to stop patching. The probe
turns "which line is wrong?" into "**are my constraints satisfiable at all?**", and the answer is no. The test, not the code, holds the wrong assumption.
This is the course's toy example (the test setup is wrong), reproduced on code that actually runs in this project; `tests/test_signalforge.py` keeps the correct
29-vehicle expectation (`test_saturation_flow_matches_lab_10_08`).

## Quiz
**Q1. How does SO-RSI differ from standard debugging?** It treats the *history of fix attempts* as data. **Q2. Can it be automated?** Partly: the
anomaly detection and the satisfiability probe above are fully automatic; choosing the variant space to search takes domain knowledge.

**Next →** [Group 03 · 10.09 Compare scaling approaches](../10_09_compare_scaling/README.md)
