# 10.15 · Calculate the RSI-Index

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/05_environments_metrics/step_01_rsi_index/README.md) · Group 05 *Environments & metrics* · RSIGym (arXiv:2610.10310) ·
run: `python labs/10_15_rsi_index/lab.py` (~15 s)

**Goal.** RSI-Index = mean over benchmarks of (final − initial) / (ideal − initial), the fraction of the *remaining* gap closed.
Compute it for the course example, the required 5-benchmark scenario, and our three headline methods on 8 traffic-family benchmarks.

## Code walkthrough
* [`signalforge/metrics.py`](../../signalforge/metrics.py) `gap_closed` / `rsi_index`. A benchmark already at ideal has no gap: it returns `None` and is excluded from the mean.
* Part 4: `run_many(method, seeds(3), budget=2400)` per method. The `heldout_by_family` dictionaries are the per-benchmark scores; *initial* = the seed program's.

## Execution (excerpt)
```text
per benchmark {'b1': 0.5, 'b2': 0.5} -> RSI-Index = 0.50   (expected 0.50)
The lab page writes mean( (initial - final) / (ideal - initial) ) ... gives -0.50
RSI-Index = 0.264. 'data' gained +0.08 raw but closed 53% of its gap; 'web' regressed and counts negative.
method        held-out  RSI-Index
seed program  31.0      0.000
Budget RSI    74.3      0.660
SO-RSI        89.7      0.865
SwarmRSI      81.3      0.744
```

## What it shows
* **A note on the course page:** its formula has the numerator reversed (initial − final), which turns improvement negative. Its own worked example
  uses (final − initial). We implement and unit-test the correct sign (`tests/test_signalforge.py::test_rsi_index`).
* RSI-Index rewards closing *hard* gaps. +0.08 near the ceiling counts for more than +0.12 from a low base.
* Its blind spot is visible here: Budget RSI drops night_sparse from 1.00 to 0.94, but that family had no gap, so the index cannot see the regression.
  Report it next to the raw score.

**Quiz Q1. Why RSI-Index instead of raw scores?** It normalises across benchmarks of different difficulty. But it needs the raw score beside it, for the regression case above.

**Next →** [10.16 Compare environments](../10_16_environments/README.md)
