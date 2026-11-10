# 10.07 · Analyse the diagnostic probes

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/02_second_order_diagnostics/step_02_analyze_probes/README.md) · Group 02 · run: `python labs/10_07_analyze_probes/lab.py` (~60 s)

**Goal.** Count how often each anomaly fires, what the probes recommend and why (the course's required table), and then find out
**which part of SO-RSI produces the gain**.

## Code walkthrough
1. Aggregate 8 runs' traces and `memory.findings` (anomaly → probe → conclusion). Split edits by source: `explore` vs `probe`-recommended.
2. Ablations, via `SORSI(use_mechanism_map=..., gate=...)`:
   * `use_mechanism_map=False`: `probe_structure` tests **every** mechanism instead of the 2–3 that `MECHANISMS` lists for the failure signature;
   * `gate="always"`: probe after every failed edit (no anomaly detection);
   * `gate="never"`: never probe (the inquiry layer off).
3. Memory across RSI rounds: round 1 (1,200 units) builds a memory. Round 2 restarts **from the seed program** with that memory (bans cleared,
   because they refer to round-1 incumbents) or without it.

## Execution (excerpt)
```text
anomaly     count  most common probe -> conclusion                        why it helps
recurrence  385    structure_probe: dominant failure signature = ...      the same nudge keeps failing: a sweep finds the value a 1-step walk never reaches
opposing    13     (structure_probe)                                      no single constant serves all families: look for a missing mechanism
mismatch    13     mechanism_probe: constant was wrong                     an 'obviously good' mechanism hurt: its default constant is wrong
edit source  proposed  accepted  acceptance  mean gain when accepted
explore      622       55        9%          ~+2
probe        56        23        41%         ~+5.5
SO-RSI (full)                        93.4 ± 7.0
no mechanism map                     93.2 ± 7.0
gate = always (probe every failure)  83.8 ± 11.9
gate = never (no inquiry)            68.9 ± 7.2
round 2 WITHOUT memory   82.7 ± 12.8
round 2 WITH round-1 memory  87.0 ± 11.3
```
(Exact counts: [EXECUTION_LOG](../../docs/EXECUTION_LOG.md#10_07_analyze_probes).)

## What it shows
* Probe-recommended edits are accepted **~4× more often** and gain **~3× more** when accepted. They were already tested on exactly the failing instances.
* **The domain-knowledge map is not what matters** (−0.2 without it). The gain comes from *anomaly-gated sweeps on the failing subset*.
  That is good news for the paper's claim: the second-order principle works without hand-written expertise.
* **Gating matters:** probing every failure spends 48% of the budget on probes and loses ~10 instances. Anomalies tell SO-RSI *when* asking "why" is worth paying for.
* Inquiry memory carries causal knowledge (e.g. "max_cap works at MAX_GREEN≈60") into the next round: +4.3 instances on average.

## Quiz
**Q1. Can several anomalies fire at once?** Yes. The trace in 10.06 shows rows with `['recurrence', 'opposing']`, and each triggers its probe.
**Q2. A probe finds no clear root cause?** It is recorded as "no mechanism helped" or "parameter exhausted", and the operator is banned for this
incumbent, so the search stops re-trying it. A recommendation that later fails full verification is stored as *refuted*.

**Next →** [10.08 Apply to a debugging task](../10_08_apply_debugging/README.md)
