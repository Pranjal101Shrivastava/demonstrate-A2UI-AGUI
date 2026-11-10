"""AReaL-RSI: a persistent research team with a leader and conditional memory (arXiv:2610.18083, lab 10.10).

* **Leader** picks a research *orientation* (a slice of the problem) for each campaign. It
  weighs how many failures the slice holds against how often the slice stayed unresolved.
* **Researchers** have different skills. ``structure`` toggles mechanisms, and ``tuning``
  moves constants (1-3 steps). Each investigates the orientation by running candidates
  on that slice of the steering split only, which is cheap.
* **Conditional memory** separates *resolved* findings (helped the slice and survived
  verification on the full steering split, so they are adopted by the whole team) from
  *unresolved* ones (helped locally but regressed elsewhere, or did not help). Researchers
  retrieve only resolved findings and skip edits already recorded as unresolved.
* **Evidence-based review** after each campaign revises the leader's orientation
  priorities and each researcher's skill settings.

``sharing=False`` runs the paper's comparison condition. Each researcher works alone with
a private incumbent and private memory, and orientations are chosen uniformly at random.
"""
import random
from dataclasses import dataclass, field

from ..program import SEED_PROGRAM, apply_op, all_ops
from ..evaluator import BudgetExhausted
from .common import Tracker, until_exhausted

ORIENTATIONS = {
    "light_traffic": {"balanced_light", "night_sparse", "platoon_pulses"},
    "heavy_balanced": {"balanced_heavy", "am_rush_ramp"},
    "asymmetric": {"ns_dominant", "ew_dominant"},
    "surge": {"stadium_surge"},
}


@dataclass
class ConditionalMemory:
    entries: list = field(default_factory=list)

    def store(self, orientation, desc, local_gain, global_delta, resolved):
        self.entries.append({"orientation": orientation, "desc": desc, "local_gain": local_gain,
                             "global_delta": global_delta, "status": "resolved" if resolved else "unresolved"})

    def unresolved_descs(self, orientation):
        return {e["desc"] for e in self.entries if e["orientation"] == orientation and e["status"] == "unresolved"}

    def count(self, orientation, status):
        return sum(1 for e in self.entries if e["orientation"] == orientation and e["status"] == status)


class Researcher:
    def __init__(self, name, skill, rng):
        self.name, self.skill, self.rng = name, skill, rng
        self.max_steps = 1
        self.resolved = 0

    def propose(self, program, avoid):
        ops = [o for o in all_ops(program)
               if (o[0] in ("add", "remove")) == (self.skill == "structure")]
        for _ in range(20):
            e = apply_op(program, self.rng.choice(ops), self.rng, steps=self.rng.randint(1, self.max_steps))
            if e.desc not in avoid:
                return e
        return e


class Team:
    def __init__(self, ev, seed=0, sharing=True, edits_per_campaign=3, verbose=False):
        self.ev, self.sharing, self.k, self.verbose = ev, sharing, edits_per_campaign, verbose
        self.rng = random.Random(seed)
        self.researchers = [Researcher("R1-structure", "structure", random.Random(seed * 7 + 1)),
                            Researcher("R2-tuning", "tuning", random.Random(seed * 7 + 2))]
        self.priority = {o: 1.0 for o in ORIENTATIONS}
        rep = ev.run(SEED_PROGRAM)
        # shared incumbent + memory, or one private copy per researcher
        self.state = {r.name: {"program": SEED_PROGRAM, "report": rep, "memory": ConditionalMemory()}
                      for r in self.researchers}
        self.shared = {"program": SEED_PROGRAM, "report": rep, "memory": ConditionalMemory()}
        self.campaigns = []

    def _st(self, r):
        return self.shared if self.sharing else self.state[r.name]

    def leader_select(self, st):
        if not self.sharing:
            return self.rng.choice(list(ORIENTATIONS))
        fails = st["report"].failures()
        mem = st["memory"]
        scores = {}
        for o, fams in ORIENTATIONS.items():
            n_fail = sum(1 for f in fails if f["family"] in fams)
            scores[o] = self.priority[o] * n_fail / (1 + 0.5 * mem.count(o, "unresolved"))
        return max(scores, key=scores.get) if any(scores.values()) else self.rng.choice(list(ORIENTATIONS))

    def investigate(self, r, orientation):
        st = self._st(r)
        fams = ORIENTATIONS[orientation]
        subset = [x for x in self.ev.split("steering") if x.family in fams]
        base = self.ev.run(st["program"], instances=subset, purpose="investigate")
        avoid = st["memory"].unresolved_descs(orientation)
        e = r.propose(st["program"], avoid)
        if e.desc in avoid:                      # nothing new to try in this orientation
            return e.desc, 0, None, False
        local = self.ev.run(e.child, instances=subset, purpose="investigate")
        local_gain = local.solved - base.solved
        if local_gain <= 0 and not (local_gain == 0 and local.mean_delay < base.mean_delay - 0.5):
            st["memory"].store(orientation, e.desc, local_gain, None, False)
            return e.desc, local_gain, None, False
        full = self.ev.run(e.child, purpose="verify")
        resolved = full.key() > st["report"].key()
        st["memory"].store(orientation, e.desc, local_gain, full.solved - st["report"].solved, resolved)
        if resolved:
            st["program"], st["report"] = e.child, full
            r.resolved += 1
        return e.desc, local_gain, full.solved - st["report"].solved if not resolved else full.solved, resolved

    def review(self, orientation, results):
        """Evidence-based review: revise orientation priority and researcher skills."""
        got = any(res for _, _, _, _, res in results)
        if self.sharing:
            self.priority[orientation] = min(2.0, self.priority[orientation] * 1.2) if got else max(0.3, self.priority[orientation] * 0.6)
        for r in self.researchers:
            mine = [x for x in results if x[0] == r.name]
            if r.skill == "tuning" and mine and not any(x[4] for x in mine):
                r.max_steps = min(3, r.max_steps + 1)       # small steps are not enough: widen
            elif r.skill == "tuning" and any(x[4] for x in mine):
                r.max_steps = max(1, r.max_steps - 1)

    def run(self):
        tr = Tracker(self.ev)
        tr.offer(self.shared["program"], self.shared["report"])

        def loop():
            idle = 0
            while True:
                u0 = self.ev.ledger.units
                results = []
                for r in self.researchers:
                    st = self._st(r)
                    orientation = self.leader_select(st)
                    for _ in range(self.k):
                        desc, lg, gd, res = self.investigate(r, orientation)
                        results.append((r.name, orientation, desc, lg, res))
                        tr.offer(self._st(r)["program"], self._st(r)["report"])
                self.review(orientation, [(n, o, d, l, s) for n, o, d, l, s in results])
                self.campaigns.append({"units": self.ev.ledger.units, "orientation": orientation,
                                       "resolved": [d for n, o, d, l, s in results if s],
                                       "best": tr.best_report.solved})
                if self.verbose and self.campaigns[-1]["resolved"]:
                    c = self.campaigns[-1]
                    print(f"  campaign {len(self.campaigns):2d} units {c['units']:5d} orientation={orientation:14s} "
                          f"resolved={c['resolved']} best={c['best']}/48")
                idle = idle + 1 if self.ev.ledger.units == u0 else 0
                if idle >= 8:                    # eight campaigns found nothing new to test
                    raise BudgetExhausted("converged: memory says every reachable edit was tried")

        until_exhausted(loop)
        mem = self.shared["memory"] if self.sharing else None
        return tr.result("areal_rsi" + ("" if self.sharing else "[independent]"), trace=self.campaigns,
                         memory=mem, priorities=dict(self.priority))


def areal_rsi(ev, seed=0, sharing=True, verbose=False):
    return Team(ev, seed, sharing, verbose=verbose).run()
