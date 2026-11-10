"""Budgeted evaluation, a cost ledger, and the final evaluation boundary.

Cost unit: one *instance-simulation* (one program on one 10-minute instance). Results are
memoised per (program source, instance), and a repeat lookup is free. That is the
same rule for every method, so budgets are comparable.

Search code gets a :class:`SearchEvaluator`. It can only see the ``fit`` and
``steering`` splits. Held-out instances live in a module-private list. Only
:func:`final_report`, called by lab code *after* search returns, can read them. Every
final read is logged in ``FINAL_ACCESS_LOG``, so a test can check that no method ever
looked.
"""
from dataclasses import dataclass, field

from .program import compile_program
from .scenarios import FAMILIES, splits
from .sim import simulate


class BudgetExhausted(Exception):
    pass


@dataclass
class Report:
    split: str
    results: list

    @property
    def n(self):
        return len(self.results)

    @property
    def solved(self):
        return sum(r["solved"] for r in self.results)

    @property
    def rate(self):
        return self.solved / self.n if self.n else 0.0

    @property
    def mean_delay(self):
        return sum(r["avg_delay"] for r in self.results) / self.n if self.n else 0.0

    def by_family(self):
        out = {}
        for f in FAMILIES:
            rs = [r for r in self.results if r["family"] == f]
            if rs:
                out[f] = sum(r["solved"] for r in rs) / len(rs)
        return out

    def failures(self):
        return [r for r in self.results if not r["solved"]]

    def key(self):
        """Comparable score: more instances solved first, then lower mean delay."""
        return (self.solved, -self.mean_delay)


@dataclass
class Ledger:
    units: int = 0
    by_purpose: dict = field(default_factory=dict)

    def charge(self, n, purpose):
        self.units += n
        self.by_purpose[purpose] = self.by_purpose.get(purpose, 0) + n


class SearchEvaluator:
    """What an RSI method is allowed to call. Holds no reference to held-out data."""

    def __init__(self, budget=None):
        s = splits()
        self._splits = {"fit": s["fit"], "steering": s["steering"]}
        self.budget = budget
        self.ledger = Ledger()
        self._cache = {}
        self._stall = 0          # consecutive calls that cost nothing (all cached)
        self.max_stall = 400

    def split(self, name):
        if name not in self._splits:
            raise PermissionError(f"split {name!r} is outside the search boundary")
        return self._splits[name]

    def remaining(self):
        return float("inf") if self.budget is None else self.budget - self.ledger.units

    def cost_of(self, program, instances):
        src = program.source
        return sum((src, x.iid) not in self._cache for x in instances)

    def run(self, program, split="steering", instances=None, purpose="search"):
        """Evaluate program on a split (or on an explicit subset of that split)."""
        insts = instances if instances is not None else self.split(split)
        allowed = {x.iid for x in self._splits["fit"]} | {x.iid for x in self._splits["steering"]}
        if any(x.iid not in allowed for x in insts):
            raise PermissionError("instance outside the search boundary")
        new = self.cost_of(program, insts)
        if self.budget is not None and self.ledger.units + new > self.budget:
            raise BudgetExhausted(f"needs {new} units, {self.remaining()} left")
        # A search that only revisits cached programs spends nothing and would loop
        # forever. After max_stall free calls in a row we call it converged and stop.
        self._stall = self._stall + 1 if new == 0 else 0
        if self._stall > self.max_stall:
            raise BudgetExhausted("stalled: no new program evaluated in a long time")
        self.ledger.charge(new, purpose)
        decide = compile_program(program)
        src = program.source
        results = []
        for x in insts:
            k = (src, x.iid)
            r = self._cache.get(k)
            if r is None:
                r = self._cache[k] = simulate(decide, x)
            results.append(r)
        return Report(split, results)


FINAL_ACCESS_LOG = []


def final_report(program, who="lab"):
    """The final boundary: evaluate on the 100 held-out instances. Logged on every call."""
    FINAL_ACCESS_LOG.append(who)
    decide = compile_program(program)
    return Report("heldout", [simulate(decide, x) for x in splits()["heldout"]])
