"""The October 2026 RSI metrics (labs 10.15 and 10.17), computed on SignalForge results.

* ``rsi_index``               RSIGym (arXiv:2610.10310): mean fraction of the *remaining* gap
                              closed, (final - initial) / (ideal - initial), averaged over
                              benchmarks. Note: the course page for lab 10.15 prints the
                              numerator as (initial - final); its own worked example uses
                              (final - initial), which is what is implemented and tested here.
* ``steering_validity``       Budget RSI: how well the steering-split solve rate predicts
                              held-out solve rate across many programs (Spearman), and how
                              much the steering winner's score overstates its held-out score.
* ``recursive_learnability``  R2Orch (arXiv:2610.22740): prefer training tasks whose outcomes
                              vary across candidate policies, measured here as 4 p (1 - p).
                              1.0 means half the candidates solve it, 0 means all or none do.
* ``swarm_diversity``         SwarmRSI: mean pairwise distance between agents' programs.
"""
from .program import program_distance
from .stats import spearman


def gap_closed(initial, final, ideal=1.0):
    if ideal == initial:
        return None                       # no gap left: undefined, excluded from the mean
    return (final - initial) / (ideal - initial)


def rsi_index(initial, final, ideal=1.0):
    """initial/final: {benchmark: score in [0,1]}. Returns (index, per-benchmark dict)."""
    per = {b: gap_closed(initial[b], final[b], ideal) for b in initial}
    vals = [v for v in per.values() if v is not None]
    return (sum(vals) / len(vals) if vals else 0.0), per


def steering_validity(pairs):
    """pairs: [(steering_rate, heldout_rate)] for a population of programs."""
    s = [a for a, _ in pairs]
    h = [b for _, b in pairs]
    top = max(range(len(pairs)), key=lambda i: s[i])
    return {"spearman": spearman(s, h), "winner_steering": s[top], "winner_heldout": h[top],
            "winner_overstatement": s[top] - h[top]}


def recursive_learnability(outcomes):
    """outcomes: {task: [0/1 per candidate policy]} -> {task: 4 p (1-p)}."""
    out = {}
    for task, xs in outcomes.items():
        p = sum(xs) / len(xs)
        out[task] = 4 * p * (1 - p)
    return out


def swarm_diversity(programs):
    d = [program_distance(programs[i], programs[j]) for i in range(len(programs)) for j in range(i + 1, len(programs))]
    return sum(d) / len(d) if d else 0.0
