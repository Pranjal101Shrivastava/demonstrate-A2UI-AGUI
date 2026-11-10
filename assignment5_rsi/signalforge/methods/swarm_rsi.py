"""Method 3: SwarmRSI, an evolving swarm of scientific agents (arXiv:2610.20431, lab 10.11).

Five agents, each with a *research direction* and an *implementation* (its current
controller program). A direction is a hypothesis about which mechanisms matter: the
components the agent starts with switched on, plus its operator preferences.

1. **Feedback-guided swarm mutation.** Each agent proposes an edit. It samples
   operators by its own preferences, multiplied by what the *shared experience board*
   says those operators did for other agents. An accepted edit reinforces the
   agent's preference and a failed one weakens it, so the hypothesis itself is refined.
2. **Complementary swarm recombination.** The swarm pairs agents whose per-family solve
   vectors complement each other (A solves what B fails). A child takes each component from
   the parent stronger on the families that component serves. The child replaces the
   weakest agent if it is better, and inherits both parents' preferences.
3. **Recursive swarm evolution.** The swarm also improves its own procedure. It tracks
   improvement per budget unit for mutation and for recombination, and moves the
   recombination interval and mutation step size towards whichever pays.

Swarm diversity (mean pairwise program distance) is logged every cycle (lab 10.17).
"""
import math
import random
from dataclasses import dataclass, field, replace

from ..program import COMPONENTS, PARAMS, SEED_PROGRAM, apply_op, all_ops, program_distance, recombine
from ..scenarios import FAMILIES
from .common import Tracker, until_exhausted

# Each research direction = a starting hypothesis (components switched on) + operator preferences.
DIRECTIONS = {
    "fairness":   ({"starvation_guard", "max_cap"}, {"starve_limit": 4, "max_green": 4, "starvation_guard": 2, "max_cap": 2}),
    "responsive": ({"actuated", "skip_empty"}, {"gap_out": 4, "min_green": 3, "actuated": 2, "skip_empty": 2}),
    "pressure":   ({"pressure"}, {"pressure_ratio": 5, "pressure": 2, "min_green": 2}),
    "timing":     (set(), {"min_green": 4, "fixed_green": 4}),
    "explorer":   (set(), {}),
}
# which families each component is meant to serve (used to make recombination complementary)
SERVES = {
    "starvation_guard": {"stadium_surge", "ns_dominant", "ew_dominant"},
    "max_cap": {"ns_dominant", "ew_dominant", "balanced_heavy", "am_rush_ramp"},
    "skip_empty": {"night_sparse", "balanced_light"},
    "pressure": {"ns_dominant", "ew_dominant", "stadium_surge", "platoon_pulses"},
    "actuated": {"night_sparse", "balanced_light", "platoon_pulses", "am_rush_ramp"},
}


@dataclass
class Agent:
    name: str
    program: object
    report: object
    prefs: dict = field(default_factory=dict)
    gains: int = 0

    def weight(self, op):
        return self.prefs.get(op, self.prefs.get(op[1], 1.0))


class Swarm:
    def __init__(self, ev, seed=0, n_agents=5, verbose=False, use_board=True, use_recombination=True,
                 evolve=True, diverse_starts=True):
        self.ev = ev
        self.use_board, self.use_recombination, self.evolve = use_board, use_recombination, evolve
        self.rng = random.Random(seed)
        self.verbose = verbose
        self.agents = []
        for n in list(DIRECTIONS)[:n_agents]:
            start, prefs = DIRECTIONS[n]
            prog = replace(SEED_PROGRAM, on=frozenset(start if diverse_starts else ()))
            self.agents.append(Agent(n, prog, ev.run(prog), dict(prefs)))
        self.board = {}                 # op -> [sum_delta, n]: shared experience
        self.recomb_every = 3           # swarm-level procedure parameters (evolve, step 3)
        self.max_steps = 2
        self.yield_mut = [0.0, 1e-9]    # [solved gained, units spent]
        self.yield_rec = [0.0, 1e-9]
        self.log = []

    # ------------------------------------------------------------ 1. mutation
    def mutate(self, a):
        ops = all_ops(a.program)
        w = []
        for op in ops:
            s, n = self.board.get(op, [0.0, 0])
            social = math.exp(0.3 * s / n) if (n and self.use_board) else 1.0          # feedback from other agents
            w.append(a.weight(op) * min(max(social, 0.5), 2.0))
        op = self.rng.choices(ops, weights=w)[0]
        e = apply_op(a.program, op, self.rng, steps=self.rng.randint(1, self.max_steps))
        u0 = self.ev.ledger.units
        rep = self.ev.run(e.child)
        delta = rep.solved - a.report.solved
        b = self.board.setdefault(op, [0.0, 0])
        b[0] += delta
        b[1] += 1
        key = op if op in a.prefs else op[1]
        if rep.key() > a.report.key():
            a.program, a.report = e.child, rep
            a.prefs[key] = a.weight(op) * 1.5
            a.gains += delta
            self.yield_mut[0] += max(delta, 0)
        else:
            a.prefs[key] = max(0.2, a.weight(op) * 0.85)
        self.yield_mut[1] += self.ev.ledger.units - u0
        return e.desc, delta

    # ------------------------------------------------------------ 2. recombination
    def recombine(self):
        fam = {a.name: a.report.by_family() for a in self.agents}

        def complement(x, y):
            fx, fy = fam[x.name], fam[y.name]
            union = sum(max(fx[f], fy[f]) for f in FAMILIES)
            return union - max(sum(fx.values()), sum(fy.values()))

        pairs = [(complement(x, y), i, j) for i, x in enumerate(self.agents) for j, y in enumerate(self.agents) if i < j]
        gain, i, j = max(pairs)
        x, y = self.agents[i], self.agents[j]
        fx, fy = fam[x.name], fam[y.name]
        prefer = {}
        for c in COMPONENTS:
            sx = sum(fx[f] for f in SERVES[c])
            sy = sum(fy[f] for f in SERVES[c])
            prefer[c] = "a" if sx >= sy else "b"
        prefer["timing"] = "a" if x.report.key() >= y.report.key() else "b"
        child = recombine(x.program, y.program, self.rng, prefer)
        u0 = self.ev.ledger.units
        rep = self.ev.run(child, purpose="recombination")
        self.yield_rec[1] += self.ev.ledger.units - u0
        worst = min(self.agents, key=lambda a: a.report.key())
        replaced = None
        if rep.key() > worst.report.key() and child.key not in {a.program.key for a in self.agents}:
            best_parent = max(x.report.solved, y.report.solved)
            self.yield_rec[0] += max(0, rep.solved - best_parent)
            prefs = {k: (x.prefs.get(k, 1) + y.prefs.get(k, 1)) / 2 for k in set(x.prefs) | set(y.prefs)}
            replaced = worst.name
            worst.program, worst.report, worst.prefs = child, rep, prefs
            worst.name = f"{x.name}x{y.name}"[:24]
        return {"parents": (x.name, y.name), "complementarity": round(gain, 2), "child_solved": rep.solved,
                "replaced": replaced}

    # ------------------------------------------------------------ 3. recursive evolution
    def evolve_procedure(self):
        ym = self.yield_mut[0] / self.yield_mut[1]
        yr = self.yield_rec[0] / self.yield_rec[1]
        if yr > ym:
            self.recomb_every = max(1, self.recomb_every - 1)
        else:
            self.recomb_every = min(6, self.recomb_every + 1)
        stuck = sum(a.gains for a in self.agents) == 0
        self.max_steps = min(4, self.max_steps + 1) if stuck else max(1, self.max_steps - 1)

    def diversity(self):
        ps = [a.program for a in self.agents]
        d = [program_distance(ps[i], ps[j]) for i in range(len(ps)) for j in range(i + 1, len(ps))]
        return sum(d) / len(d)

    def run(self):
        tr = Tracker(self.ev)
        tr.offer(self.agents[0].program, self.agents[0].report)
        cycle = 0

        def loop():
            nonlocal cycle
            while True:
                cycle += 1
                for a in self.agents:
                    a.gains = 0
                muts = []
                for a in self.agents:
                    desc, d = self.mutate(a)
                    tr.offer(a.program, a.report)
                    muts.append((a.name, desc, d))
                rec = None
                if self.use_recombination and cycle % self.recomb_every == 0:
                    rec = self.recombine()
                    for a in self.agents:
                        tr.offer(a.program, a.report)
                if self.evolve:
                    self.evolve_procedure()
                row = {"cycle": cycle, "units": self.ev.ledger.units, "best": tr.best_report.solved,
                       "diversity": round(self.diversity(), 2), "recomb_every": self.recomb_every,
                       "max_steps": self.max_steps, "recombination": rec,
                       "agents": [(a.name, a.report.solved) for a in self.agents]}
                self.log.append(row)
                if self.verbose:
                    print(f"  cycle {cycle:2d} units {row['units']:5d} best {row['best']:2d}/48 "
                          f"div {row['diversity']:.2f} recomb_every {self.recomb_every} "
                          f"agents {[s for _, s in row['agents']]}" + (f"  recomb {rec}" if rec else ""))

        until_exhausted(loop)
        return tr.result("swarm_rsi", trace=self.log, agents=[(a.name, a.program.summary(), a.report.solved) for a in self.agents])


def swarm_rsi(ev, seed=0, verbose=False, **ablations):
    res = Swarm(ev, seed, verbose=verbose, **ablations).run()
    if ablations:
        res.method = "swarm_rsi[" + ",".join(f"{k}={v}" for k, v in ablations.items()) + "]"
    return res
