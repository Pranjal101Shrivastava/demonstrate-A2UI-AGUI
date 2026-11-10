"""Method 2: Second-Order RSI, diagnostic inquiry before patching (arXiv:2610.05701, labs 10.06-10.08).

Naive (first-order) RSI proposes an edit, keeps it if the score rises, and repeats. When
an edit fails it learns nothing about *why*. SO-RSI runs the same propose/evaluate/accept
loop, and also watches its own trace for three structural anomalies:

    recurrence   the same operator keeps failing           -> is this direction exhausted,
                                                              or is the step size wrong?
    opposing     X is pushed up, then down (or added, then -> do families want conflicting
                 removed) and both fail                       values of X?
    mismatch     the outcome contradicts what memory       -> is our model of this mechanism
                 expected (e.g. "add a component" was         wrong, e.g. right component
                 expected to help but made things worse)      with a wrong constant?

Each anomaly triggers a *diagnostic probe*: a small, real experiment run only on the
instances the incumbent fails, plus a few it passes (a regression check). Probes are
charged to the same budget (purpose "probe"), so the comparison with Naive RSI is fair.
Conclusions go into a persistent **inquiry memory**:

* ``tuned``     the constant that made a mechanism work (reused whenever it is added again)
* ``bans``      operators shown to be exhausted for the current incumbent
* ``findings``  the causal record: anomaly -> probe -> evidence -> action
* ``refuted``   recommendations that won on the probe set but lost on the full split
* ``expect``    a running model of what each operator does (used for mismatch detection)

The probe library knows which mechanisms can address which failure signature. That is
domain knowledge, the same role the paper gives to the LLM's diagnosis. It is listed in
``MECHANISMS`` so a reader can see exactly what the method "knows".
"""
import random
from dataclasses import dataclass, field, replace

from ..program import PARAMS, SEED_PROGRAM, apply_op, random_edit
from ..sim import WAIT_TARGET
from .common import Tracker, until_exhausted

LIGHT = {"balanced_light", "night_sparse", "platoon_pulses"}

# failure signature -> mechanisms (component, constant to sweep) that can address it
MECHANISMS = {
    "wait": [("starvation_guard", "starve_limit"), ("max_cap", "max_green")],
    "delay_light": [("actuated", "gap_out"), ("skip_empty", None)],
    "delay_heavy": [("pressure", "pressure_ratio"), ("actuated", "gap_out"), ("max_cap", "max_green")],
}
COMPONENT_PARAM = {"starvation_guard": "starve_limit", "max_cap": "max_green", "pressure": "pressure_ratio",
                   "actuated": "gap_out", "skip_empty": None}


def sweep_values(param, n=4):
    lo, hi, step, _ = PARAMS[param]
    vals = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    out = []
    for v in vals:
        v = round(round((v - lo) / step) * step + lo, 1)
        v = v if isinstance(step, float) else int(v)
        if v not in out:
            out.append(v)
    return out


@dataclass
class InquiryMemory:
    tuned: dict = field(default_factory=dict)        # component -> {param: value}
    bans: dict = field(default_factory=dict)         # incumbent key -> set of op keys
    findings: list = field(default_factory=list)
    expect: dict = field(default_factory=dict)       # op -> [sum_delta, n]
    refuted: set = field(default_factory=set)        # probe recommendations that failed full verification

    def expectation(self, op):
        s, n = self.expect.get(op, [0.0, 0])
        prior = 1.0 if op[0] == "add" else 0.0       # engineers expect a new mechanism to help
        return (s + prior) / (n + 1)

    def observe(self, op, delta):
        e = self.expect.setdefault(op, [0.0, 0])
        e[0] += delta
        e[1] += 1

    def banned(self, program):
        return self.bans.get(program.key, set())

    def ban(self, program, op):
        self.bans.setdefault(program.key, set()).add(op)


def detect(trace, window=8):
    """Return the anomalies the latest trace entry exhibits."""
    cur = trace[-1]
    if cur["accepted"]:
        return []
    recent = trace[-window:-1]
    out = []
    if sum(1 for t in recent if t["op"] == cur["op"] and not t["accepted"]) >= 1:
        out.append("recurrence")
    inverse = {"increase": "decrease", "decrease": "increase", "add": "remove", "remove": "add"}
    if any(t["op"] == (inverse[cur["op"][0]], cur["op"][1]) and not t["accepted"] for t in recent[-5:]):
        out.append("opposing")
    exp = cur["expected"]
    if (exp >= 0.5 and cur["delta"] <= -2) or (exp <= -0.5 and cur["delta"] >= 2):
        out.append("mismatch")
    return out


def _with_component(p, comp, param=None, value=None):
    q = replace(p, on=p.on | {comp})
    if param is not None and value is not None:
        q = replace(q, **{param: value})
    return q


class SORSI:
    def __init__(self, ev, seed=0, memory=None, regression=6, verbose=False, use_mechanism_map=True,
                 gate="anomaly"):
        """Ablations (lab 10.07): use_mechanism_map=False makes the structure probe try every
        mechanism (no domain knowledge). gate="always" probes after every failed edit, and
        gate="never" never probes (which is Naive RSI plus the memory's tuned constants, i.e. none)."""
        self.ev = ev
        self.use_map, self.gate = use_mechanism_map, gate
        self.rng = random.Random(seed)
        self.mem = memory or InquiryMemory()
        self.regression = regression
        self.verbose = verbose
        self.trace = []
        self.pending = []           # systematic edits recommended by probes
        self.probes_run = 0

    # ---------------------------------------------------------------- probes
    def _probe_set(self):
        fails = [r["instance"] for r in self.cur_rep.failures()]
        passes = [r["instance"] for r in self.cur_rep.results if r["solved"]]
        self.rng.shuffle(passes)
        ids = set(fails + passes[: self.regression])
        return [x for x in self.ev.split("steering") if x.iid in ids]

    def _probe_score(self, program, insts):
        r = self.ev.run(program, instances=insts, purpose="probe")
        return r.solved, -r.mean_delay

    def _best_variant(self, variants, label):
        """Evaluate candidate programs on the probe set and return the best that beats the incumbent."""
        insts = self._probe_set()
        base = self._probe_score(self.cur, insts)
        scored = []
        for desc, prog in variants:
            if prog.key == self.cur.key or prog.key in self.mem.refuted:
                continue
            scored.append((self._probe_score(prog, insts), desc, prog))
        self.probes_run += 1
        if not scored:
            return None, base, []
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0]
        evidence = [(d, s[0]) for s, d, _ in scored[:4]]
        return (best if best[0] > base else None), base, evidence

    def probe_mechanism(self, comp, why):
        """Is the mechanism right but its constant wrong? Sweep the component's constant."""
        param = COMPONENT_PARAM[comp]
        variants = [(f"add {comp} ({param}={v})", _with_component(self.cur, comp, param, v))
                    for v in (sweep_values(param) if param else [None])]
        best, base, ev = self._best_variant(variants, "mechanism")
        concl = "constant was wrong" if best else "mechanism does not help here"
        if best:
            self.mem.tuned[comp] = {param: getattr(best[2], param)} if param else {}
            self.pending.append((best[2], ("add", comp), best[1]))
        else:
            self.mem.ban(self.cur, ("add", comp))
        self._record(why, f"mechanism_probe({comp})", base, ev, concl)

    def probe_direction(self, param, why):
        """Recurrence on a nudge: is this direction exhausted, or are the steps too small?"""
        variants = [(f"set {param}={v}", replace(self.cur, **{param: v})) for v in sweep_values(param, 5)]
        best, base, ev = self._best_variant(variants, "direction")
        if best:
            self.pending.append((best[2], ("set", param), best[1]))
            concl = "step size too small: jump directly"
        else:
            self.mem.ban(self.cur, ("increase", param))
            self.mem.ban(self.cur, ("decrease", param))
            concl = "parameter exhausted for this incumbent"
        self._record(why, f"direction_probe({param})", base, ev, concl)

    def probe_structure(self, why):
        """Opposing edits / mismatch: attribute failures, then test the mechanisms that address them."""
        fails = self.cur_rep.failures()
        sig = {"wait": 0, "delay_light": 0, "delay_heavy": 0}
        for r in fails:
            if r["fail"] in ("wait", "both"):
                sig["wait"] += 1
            if r["fail"] in ("delay", "both"):
                sig["delay_light" if r["family"] in LIGHT else "delay_heavy"] += 1
        dominant = max(sig, key=sig.get)
        if not fails:
            return
        variants = []
        mechanisms = MECHANISMS[dominant] if self.use_map else list(COMPONENT_PARAM.items())
        for comp, param in mechanisms:
            if comp in self.cur.on:          # already present: re-tune its constant instead
                if param:
                    variants += [(f"set {param}={v}", replace(self.cur, **{param: v})) for v in sweep_values(param, 3)]
                continue
            known = self.mem.tuned.get(comp)
            vals = [known[param]] if (known and param) else (sweep_values(param, 3) if param else [None])
            variants += [(f"add {comp}" + (f" ({param}={v})" if param else ""), _with_component(self.cur, comp, param, v))
                         for v in vals]
        best, base, ev = self._best_variant(variants, "structure")
        concl = f"dominant failure signature = {dominant} {sig}"
        if best:
            self.pending.append((best[2], ("structural", dominant), best[1]))
            comp = best[1].split()[1]
            if best[1].startswith("add") and COMPONENT_PARAM.get(comp):
                self.mem.tuned[comp] = {COMPONENT_PARAM[comp]: getattr(best[2], COMPONENT_PARAM[comp])}
        self._record(why, f"structure_probe({dominant})", base, ev, concl + ("" if best else "; no mechanism helped"))

    def _record(self, anomaly, probe, base, evidence, conclusion):
        f = {"step": len(self.trace), "anomaly": anomaly, "probe": probe, "incumbent_probe_score": base[0],
             "evidence": evidence, "conclusion": conclusion}
        self.mem.findings.append(f)
        if self.verbose:
            print(f"    [{anomaly}] {probe}: {conclusion}; top variants {evidence[:3]}")

    # ---------------------------------------------------------------- main loop
    def propose(self):
        while self.pending:
            prog, op, desc = self.pending.pop(0)
            if prog.key != self.cur.key:
                return prog, op, desc, "probe"
        e = random_edit(self.cur, self.rng, banned=self.mem.banned(self.cur))
        prog = e.child
        if e.op[0] == "add" and e.op[1] in self.mem.tuned:       # reuse what inquiry learned
            prog = replace(prog, **self.mem.tuned[e.op[1]])
        return prog, e.op, e.desc, "explore"

    def run(self, start=SEED_PROGRAM):
        tr = Tracker(self.ev)
        self.cur, self.cur_rep = start, self.ev.run(start)
        tr.offer(self.cur, self.cur_rep)

        def loop():
            while True:
                prog, op, desc, source = self.propose()
                expected = self.mem.expectation(op)
                rep = self.ev.run(prog)
                delta = rep.solved - self.cur_rep.solved
                accepted = rep.key() > self.cur_rep.key()
                entry = {"op": op, "desc": desc, "source": source, "delta": delta, "expected": round(expected, 2),
                         "accepted": accepted, "units": self.ev.ledger.units}
                self.trace.append(entry)
                self.mem.observe(op, delta)
                if self.verbose:
                    print(f"  {len(self.trace):3d} {source:7s} {desc:42s} delta={delta:+d} "
                          f"{'ACCEPT' if accepted else 'reject'}")
                if source == "probe" or self.gate == "never":
                    anomalies = []
                elif self.gate == "always":
                    anomalies = [] if accepted else ["failure"]
                else:
                    anomalies = detect(self.trace)
                entry["anomalies"] = anomalies
                if accepted:
                    self.cur, self.cur_rep = prog, rep
                elif source == "probe":
                    self.mem.refuted.add(prog.key)   # helped on the probe set, not on the full split
                tr.offer(prog, rep)
                for a in anomalies:
                    verb, target = op
                    if a == "opposing" or (a == "mismatch" and verb in ("increase", "decrease", "remove")):
                        self.probe_structure(a)
                    elif verb == "add":
                        self.probe_mechanism(target, a)
                    elif verb in ("increase", "decrease"):
                        self.probe_direction(target, a)
                    else:
                        self.probe_structure(a)

        until_exhausted(loop)
        name = "so_rsi" + ("" if self.use_map else "[no-map]") + ("" if self.gate == "anomaly" else f"[gate={self.gate}]")
        return tr.result(name, trace=self.trace, memory=self.mem, probes=self.probes_run)


def so_rsi(ev, seed=0, memory=None, verbose=False, start=SEED_PROGRAM, **ablations):
    return SORSI(ev, seed, memory, verbose=verbose, **ablations).run(start)
