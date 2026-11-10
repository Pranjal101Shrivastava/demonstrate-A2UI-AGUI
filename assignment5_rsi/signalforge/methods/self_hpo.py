"""Self-HPO: alternating harness and policy optimisation (arXiv:2610.22791, lab 10.14).

We split the controller into two parts:

* **harness** H = which mechanisms wrap the controller (the component set) together with
  the *curriculum*, meaning which steering instances the next policy step trains on.
* **policy**  theta = the numeric constants the controller runs with.

    H-step  the policy analyses its own failures on the steering split. The failing
            instances become the hard set, and the next curriculum is the hard set plus
            a regression sample. The policy proposes harness candidates (toggle each
            mechanism, keeping theta), scores them on that curriculum, and adopts the
            best if it also holds up on the full steering split.
    P-step  coordinate search over theta under the selected harness, scored on the
            curriculum. The result is adopted if it holds up on the full steering split.

Three conditions at the same budget make the "harness and policy are mutually
reinforcing" claim testable:

    policy_only    P-steps only (harness frozen at the seed: fixed-time, no mechanisms)
    harness_only   H-steps only (theta frozen at its initial values)
    joint          alternate H, P, H, P, ...
"""
import random
from dataclasses import replace

from ..program import COMPONENTS, PARAMS, SEED_PROGRAM, toggle
from .common import Tracker, until_exhausted


class SelfHPO:
    def __init__(self, ev, seed=0, mode="joint", regression=8, verbose=False):
        self.ev, self.mode, self.regression, self.verbose = ev, mode, regression, verbose
        self.rng = random.Random(seed)
        self.log = []

    def curriculum(self):
        hard = [r["instance"] for r in self.cur_rep.failures()]
        easy = [r["instance"] for r in self.cur_rep.results if r["solved"]]
        self.rng.shuffle(easy)
        ids = set(hard + easy[: self.regression])
        return [x for x in self.ev.split("steering") if x.iid in ids], len(hard)

    def _adopt_if_better(self, cand):
        rep = self.ev.run(cand, purpose="verify")
        if rep.key() > self.cur_rep.key():
            self.cur, self.cur_rep = cand, rep
            return True
        return False

    def h_step(self):
        cur_set, n_hard = self.curriculum()
        base = self.ev.run(self.cur, instances=cur_set, purpose="h-step")
        cands = [toggle(self.cur, c) for c in COMPONENTS]
        scored = sorted(((self.ev.run(e.child, instances=cur_set, purpose="h-step").key(), e) for e in cands),
                        key=lambda x: x[0], reverse=True)
        best_key, best = scored[0]
        adopted = best_key > base.key() and self._adopt_if_better(best.child)
        self.log.append({"step": "H", "hard_set": n_hard, "proposal": best.desc, "adopted": adopted,
                         "units": self.ev.ledger.units, "best": self.cur_rep.solved})

    def p_step(self, sweeps=1):
        cur_set, n_hard = self.curriculum()
        theta = self.cur
        base = self.ev.run(theta, instances=cur_set, purpose="p-step").key()
        for _ in range(sweeps):
            for name in theta.active_params():
                lo, hi, step, _ = PARAMS[name]
                for k in (-2, -1, 1, 2):
                    v = getattr(theta, name) + k * step
                    if not lo <= v <= hi:
                        continue
                    v = round(v, 1) if isinstance(step, float) else int(v)
                    cand = replace(theta, **{name: v})
                    key = self.ev.run(cand, instances=cur_set, purpose="p-step").key()
                    if key > base:
                        theta, base = cand, key
        adopted = theta.key != self.cur.key and self._adopt_if_better(theta)
        self.log.append({"step": "P", "hard_set": n_hard, "proposal": theta.summary(), "adopted": adopted,
                         "units": self.ev.ledger.units, "best": self.cur_rep.solved})

    def run(self):
        tr = Tracker(self.ev)
        self.cur, self.cur_rep = SEED_PROGRAM, self.ev.run(SEED_PROGRAM)
        tr.offer(self.cur, self.cur_rep)

        def loop():
            i = 0
            while True:
                if self.mode == "policy_only" or (self.mode == "joint" and i % 2 == 1):
                    self.p_step()
                else:
                    self.h_step()
                tr.offer(self.cur, self.cur_rep)
                if self.verbose:
                    print("  ", self.log[-1])
                i += 1

        until_exhausted(loop)
        return tr.result(f"self_hpo[{self.mode}]", trace=self.log)


def self_hpo(ev, seed=0, mode="joint", verbose=False):
    return SelfHPO(ev, seed, mode, verbose=verbose).run()
