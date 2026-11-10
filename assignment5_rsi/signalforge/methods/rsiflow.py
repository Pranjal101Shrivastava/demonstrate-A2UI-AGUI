"""RSIFlow: an evolving meta-agent that re-routes the improvement workflow (arXiv:2610.21791, lab 10.13).

The improvement workflow is a small graph. Every step runs one *route* through it:

    tune   -> full        nudge one constant, evaluate on the steering split (48 units)
    struct -> full        toggle a mechanism, evaluate on the steering split
    tune   -> screen -> full    the same, but first a cheap 16-instance fit-split screen;
    struct -> screen -> full    only survivors pay for the full evaluation
    diagnose -> targeted -> full    read the incumbent's failures (free) and propose an
                                    edit for the mechanism family that serves them

A *static* workflow samples routes uniformly forever. The *meta-agent* profiles each
route's execution feedback: improvement per budget unit, plus the screen's false-positive
rate. The statistics are *discounted* (old evidence fades), because the bottleneck moves:
early on new mechanisms pay, later their constants do. It then (a) routes traffic to the
current best yield with UCB, and (b) evolves its own screen rule. If too many screened
candidates fail the full evaluation, the screen tightens from "not worse" to "strictly
better".
"""
import math
import random

from ..program import SEED_PROGRAM, apply_op, all_ops
from .common import Tracker, until_exhausted

ROUTES = ("tune>full", "struct>full", "tune>screen>full", "struct>screen>full", "diagnose>targeted>full")
TARGETS = {
    "wait": {"starvation_guard", "max_cap", "starve_limit", "max_green"},
    "delay_light": {"actuated", "skip_empty", "gap_out", "min_green"},
    "delay_heavy": {"pressure", "pressure_ratio", "max_green", "fixed_green", "gap_out"},
}
LIGHT = {"balanced_light", "night_sparse", "platoon_pulses"}


class Flow:
    def __init__(self, ev, seed=0, adaptive=True, verbose=False):
        self.ev, self.adaptive, self.verbose = ev, adaptive, verbose
        self.rng = random.Random(seed)
        # lifetime totals (reported) and discounted totals (used for routing)
        self.stats = {r: {"gain": 0.0, "units": 1e-9, "n": 0, "dgain": 0.0, "dunits": 1e-9, "w": 0.0}
                      for r in ROUTES}
        self.screen_strict = False
        self.screen_pass, self.screen_false_pos = 0, 0
        self.history = []

    DISCOUNT = 0.9

    def choose_route(self, step):
        if not self.adaptive:
            return self.rng.choice(ROUTES)
        total = sum(s["w"] for s in self.stats.values()) + 1
        def ucb(r):
            s = self.stats[r]
            if s["n"] < 2:
                return float("inf")
            return s["dgain"] / s["dunits"] * 100 + 0.5 * math.sqrt(math.log(total) / max(s["w"], 1e-3))
        return max(ROUTES, key=ucb)

    def propose(self, route):
        p = self.cur
        if route.startswith("diagnose"):
            sig = {"wait": 0, "delay_light": 0, "delay_heavy": 0}
            for r in self.cur_rep.failures():
                if r["fail"] in ("wait", "both"):
                    sig["wait"] += 1
                if r["fail"] in ("delay", "both"):
                    sig["delay_light" if r["family"] in LIGHT else "delay_heavy"] += 1
            want = TARGETS[max(sig, key=sig.get)]
            ops = [o for o in all_ops(p) if o[1] in want] or all_ops(p)
        else:
            struct = route.startswith("struct")
            ops = [o for o in all_ops(p) if (o[0] in ("add", "remove")) == struct]
        return apply_op(p, self.rng.choice(ops), self.rng, steps=self.rng.randint(1, 3))

    def step(self, step):
        route = self.choose_route(step)
        u0 = self.ev.ledger.units
        e = self.propose(route)
        gain, reached_full = 0, True
        if ">screen>" in route:
            base = self.ev.run(self.cur, "fit", purpose="screen")
            scr = self.ev.run(e.child, "fit", purpose="screen")
            ok = scr.key() > base.key() if self.screen_strict else scr.solved >= base.solved
            reached_full = ok
        if reached_full:
            rep = self.ev.run(e.child, purpose="full")
            if ">screen>" in route:
                self.screen_pass += 1
                self.screen_false_pos += rep.key() <= self.cur_rep.key()
            if rep.key() > self.cur_rep.key():
                gain = rep.solved - self.cur_rep.solved + 0.5     # +0.5: delay-only wins still count
                self.cur, self.cur_rep = e.child, rep
        spent = self.ev.ledger.units - u0
        for r, st in self.stats.items():              # old evidence fades for every route
            st["dgain"] *= self.DISCOUNT
            st["dunits"] *= self.DISCOUNT
            st["w"] *= self.DISCOUNT
        s = self.stats[route]
        s["gain"] += gain
        s["units"] += spent
        s["n"] += 1
        s["dgain"] += gain
        s["dunits"] += max(spent, 8)                  # a re-proposal of a cached edit still costs a turn
        s["w"] += 1
        if self.adaptive and self.screen_pass >= 6 and not self.screen_strict:
            if self.screen_false_pos / self.screen_pass > 0.8:
                self.screen_strict = True                         # the meta-agent rewrites its own rule
        self.history.append({"step": step, "route": route, "desc": e.desc, "gain": gain,
                             "units": self.ev.ledger.units, "best": self.cur_rep.solved})

    def run(self):
        tr = Tracker(self.ev)
        self.cur, self.cur_rep = SEED_PROGRAM, self.ev.run(SEED_PROGRAM)
        tr.offer(self.cur, self.cur_rep)
        step = 0

        def loop():
            nonlocal step
            while True:
                step += 1
                self.step(step)
                tr.offer(self.cur, self.cur_rep)

        until_exhausted(loop)
        yields = {r: round(s["gain"] / s["units"] * 1000, 2) for r, s in self.stats.items()}
        usage = {r: s["n"] for r, s in self.stats.items()}
        return tr.result("rsiflow" + ("" if self.adaptive else "[static]"), trace=self.history,
                         route_yield_per_1000_units=yields, route_usage=usage, screen_strict=self.screen_strict)


def rsiflow(ev, seed=0, adaptive=True, verbose=False):
    return Flow(ev, seed, adaptive, verbose).run()
