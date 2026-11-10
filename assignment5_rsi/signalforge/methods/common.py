"""What every method returns, plus the shared "keep the best so far" bookkeeping."""
from dataclasses import dataclass, field

from ..evaluator import BudgetExhausted


@dataclass
class RunResult:
    method: str
    best: object            # Program
    best_report: object     # steering Report of best
    curve: list             # [(units_spent, best_steering_solved)]: the anytime curve
    ledger: object
    trace: list = field(default_factory=list)     # per-step records (method-specific)
    extras: dict = field(default_factory=dict)    # method-specific evidence (memory, coefficients...)


class Tracker:
    """Keeps the incumbent and the anytime curve. ``offer`` returns True if it improved."""

    def __init__(self, ev):
        self.ev = ev
        self.best = None
        self.best_report = None
        self.curve = []

    def offer(self, program, report):
        improved = self.best_report is None or report.key() > self.best_report.key()
        if improved:
            self.best, self.best_report = program, report
        self.curve.append((self.ev.ledger.units, self.best_report.solved))
        return improved

    def result(self, method, trace=None, **extras):
        return RunResult(method, self.best, self.best_report, self.curve, self.ledger_copy(), trace or [], extras)

    def ledger_copy(self):
        from copy import deepcopy
        return deepcopy(self.ev.ledger)


def until_exhausted(fn):
    """Run ``fn`` and swallow the BudgetExhausted that ends every search loop."""
    try:
        fn()
    except BudgetExhausted:
        pass
