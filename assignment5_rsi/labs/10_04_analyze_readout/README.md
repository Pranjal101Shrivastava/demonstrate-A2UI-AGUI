# 10.04 · Analyse the scoring mechanism

[Course lab](https://github.com/dlmastery/simple-coding-harness/blob/main/10_research_studio/01_budget_rsi_scoring/step_02_analyze_mechanism/README.md) · Group 01 · run: `python labs/10_04_analyze_readout/lab.py` (~40 s)

**Goal.** Which diff coordinates drive the score? Does the readout rank the children it is actually asked about? What do 8→4 features
and 96→24 training edits do (the course's check-your-understanding questions)?

## Code walkthrough
1. **Importance.** Raw weights are not comparable across features with different spreads, so we rank by |weight| × feature std.
2. **A sibling test bench built from real search trees.** Budget RSI's search log keeps every expanded program (`trace[i]["program"]`).
   We pool the nodes of 6 searches, pick 12 parents spread across quality (steering 0.25–0.92), give each 8 distinct children, and
   evaluate **all 96** on steering (analysis-only cost, which the method never pays).
3. **`validity(readout, subset)`** = mean within-sibling Spearman(score, actual) + top-1 regret (best sibling minus the picked one, in instances),
   reported for *weak* (< 0.70) and *strong* (≥ 0.70) parents separately. Ranking only ever happens among siblings, so overall R² would be misleading.
4. **Variants:** 4 features (lines/functions only), parent-rate only, 48 and 24 training edits, and a readout trained on a **shifted
   scaffold** (`regime="random"`: random-walk parents instead of hill-climb snapshots).
5. **Does validity predict search outcome?** 6 seeds of 40-expansion search with climb-trained vs shift-trained readouts.

## Execution (excerpt)
```text
coordinate   weight  feature std  |weight| x std
lines_deleted -0.111 2.480        0.275
branch_delta  -0.358 0.571        0.204
parent_rate   +0.648 0.215        0.139 ...
readout variant               Spearman all  on weak parents  on strong parents  regret all  regret strong
8 features, 96 edits (paper)  +0.12         +0.03            +0.31              7.00        3.50
4 features (lines/funcs only) -0.07         -0.27            +0.31              9.00        2.00
8 features, SHIFTED scaffold  +0.31         +0.36            +0.22              5.50        4.75
climb scaffold    76.2 ± 12.4   97 63 74 83 74 66
shifted scaffold  64.3 ± 2.3    62 66 67 63 62 66
```

## What it shows
* The readout learned **"edits that delete code or add branches tend to hurt"**, plus parent quality. These are generic, plausible regularities.
* Within-sibling ranking is weak overall (+0.12) but better on **strong** parents (+0.31), which is where HGM spends its expansions.
* **Distribution shift is the failure mode.** The shifted readout ranks weak parents' children better (+0.36), because those are what it was
  trained on, but strong parents' children worse (+0.22). Its searches lose ~12 held-out instances. The readout is only as good as the match
  between its training edits and the edits the search asks about. (Caveat: only 4 strong parents on the bench, so treat the split as indicative.)
* 4 features: no better on strong parents and much worse on weak ones. Fewer edits (24): validity drops towards zero.

## Quiz
**Q1. Why linear?** Fast to fit (96 × 9), microseconds to score, and interpretable: the table above *is* the model.
**Q2. Correlated features?** `lines_added` / `lines_deleted` / `funcs_added` move together when a mechanism is toggled. Ridge (`lam=1e-2`)
splits the weight between them, so read importance per group, not per coordinate.

**Next →** [10.05 Extend to your own edits](../10_05_extend_readout/README.md)
