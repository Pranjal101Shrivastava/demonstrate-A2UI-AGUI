"""Two baselines every RSI method must beat under the same budget.

* random_search     sample programs (1-8 random edits from the seed) and keep the best.
* naive_rsi         "first-order" RSI: propose one random edit to the incumbent, keep it if
                    the steering score improves. It patches symptoms and never asks why.
                    SO-RSI (arXiv:2610.05701) calls this the Naive RSI baseline.
"""
import random

from ..program import SEED_PROGRAM, random_edit, random_program
from .common import Tracker, until_exhausted


def random_search(ev, seed=0):
    rng = random.Random(seed)
    tr = Tracker(ev)
    tr.offer(SEED_PROGRAM, ev.run(SEED_PROGRAM))

    def loop():
        while True:
            p = random_program(rng, depth=rng.randint(1, 8))
            tr.offer(p, ev.run(p))

    until_exhausted(loop)
    return tr.result("random_search")


def naive_rsi(ev, seed=0, start=SEED_PROGRAM):
    rng = random.Random(seed)
    tr = Tracker(ev)
    cur, cur_rep = start, ev.run(start)
    tr.offer(cur, cur_rep)
    trace = []

    def loop():
        nonlocal cur, cur_rep
        while True:
            e = random_edit(cur, rng)
            rep = ev.run(e.child)
            accepted = rep.key() > cur_rep.key()
            trace.append({"op": e.op, "desc": e.desc, "delta": rep.solved - cur_rep.solved, "accepted": accepted})
            if accepted:
                cur, cur_rep = e.child, rep
            tr.offer(e.child, rep)

    until_exhausted(loop)
    return tr.result("naive_rsi", trace=trace)
