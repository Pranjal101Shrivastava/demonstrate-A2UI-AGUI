# 10.05 · Extend the scorer to our task, and make it recursive

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/01_budget_rsi_scoring/step_03_extend/README.md) · Group 01 · run: `python labs/10_05_extend_readout/lab.py` (~80 s)

**Goal.** The course asks us to adapt the scorer to our own editing task. We test three extensions against the paper-style readout,
on the same seeds and with 40 expansions each:

| Extension | Code | Idea |
|---|---|---|
| (a) task-specific features | `diff_features.rich_diff_features` (19 coordinates) | + signed log change **per named constant** (`dlog_GAP_OUT`...) + **±1 per mechanism helper** added/removed. Still static: read from the two source files. |
| (b) online refit, the *recursive* step | `budget_rsi.search(..., online_refit=True)` | after every expansion: `readout.add(parent_rate, features, realised_rate)`; `readout.fit()`. The improver's selection rule is rewritten by its own results during the run. |
| (c) negative control | `train_readout(..., label_noise_seed=s)` | labels shuffled, so features carry no information. The course quiz predicts "no better than random". |

## Execution (excerpt; full: [EXECUTION_LOG](../../docs/EXECUTION_LOG.md#10_05_extend_readout))
```text
configuration                      held-out /100  per seed
paper readout (8 generic, frozen)  76.2 ± 12.4    97 63 74 83 74 66
(b) + online refit (recursive)     76.3 ± 6.4     83 79 72 83 74 67
(a) task-specific features (19)    73.8 ± 11.8    97 66 74 68 72 66
(a)+(b) task features + refit      81.8 ± 10.5    97 78 74 77 72 93
(c) shuffled labels (control)      65.8 ± 13.3    43 74 74 63 80 61
random selector (reference)        69.3 ± 3.8     66 66 69 74 74 67
```

## What it shows
* **Feature choice matters, but richer features need on-distribution data.** 19 features fitted on 96 scaffold edits overfit (-2.3).
  The same features with online refitting, which keeps feeding them labels from the search's own regime, give the **best Budget RSI result (+5.7)**.
* **The recursive step halves the variance** with the generic features (sd 12.4 → 6.4) at the same mean: a self-correcting selection rule
  avoids the bad seeds where the frozen readout's bias leads search astray.
* **The negative control behaves as predicted.** With no signal in the labels, the scorer is no better than random (65.8 vs 69.3), and has the
  worst single seed (43). So the readout's gains in 10.03 come from what the features carry.

## Quiz
**Q1. If success is not correlated with the diff features?** Shown directly by (c): random-level performance.
**Q2. Can Budget RSI work for non-code tasks?** Yes, given a steering split, static features of a proposed change, and correlation. Our
"code" is a traffic controller, and the features are about traffic mechanisms (gap-out, max-green), which is what makes (a) work.

**Next →** [Group 02 · 10.06 Run SO-RSI](../10_06_run_so_rsi/README.md)
