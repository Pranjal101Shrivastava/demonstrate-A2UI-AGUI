"""SignalForge exposed as RSIGym-style "Everything as a Service" (lab 10.16).

RSIGym (arXiv:2610.10310) gives an RSI agent its capabilities as reusable services behind
shared budget and permission controls. This facade puts the same pieces we already have
behind that interface:

    simulate(program, instance_id)  one rollout (trace-level metrics), charged 1 unit
    evaluate(program, split)        a scored benchmark run on fit/steering
    sandbox_exec(source)            compile untrusted controller source into a namespace with
                                    no builtins and check it defines decide(); no I/O possible
    heldout(program)                the final boundary, denied unless the caller holds the
                                    "final" permission

Each call is checked against the caller's permissions and charged to its budget.
"""
from .evaluator import BudgetExhausted, SearchEvaluator, final_report
from .program import compile_program
from .sim import simulate as _simulate


class ServiceError(Exception):
    pass


class Services:
    def __init__(self, budget, permissions=("simulate", "evaluate", "sandbox")):
        self.ev = SearchEvaluator(budget=budget)
        self.permissions = set(permissions)
        self.calls = []

    def _check(self, perm):
        self.calls.append(perm)
        if perm not in self.permissions:
            raise ServiceError(f"permission denied: '{perm}' is not granted to this agent")

    def simulate(self, program, instance_id):
        self._check("simulate")
        inst = [x for x in self.ev.split("steering") + self.ev.split("fit") if x.iid == instance_id]
        if not inst:
            raise ServiceError(f"unknown or out-of-boundary instance {instance_id}")
        return self.ev.run(program, instances=inst, purpose="svc.simulate").results[0]

    def evaluate(self, program, split="steering"):
        self._check("evaluate")
        return self.ev.run(program, split, purpose="svc.evaluate")

    def sandbox_exec(self, source):
        self._check("sandbox")
        ns = {"__builtins__": {"max": max, "min": min, "abs": abs}}
        try:
            exec(compile(source, "<sandbox>", "exec"), ns)
        except Exception as exc:                       # report, do not crash the agent
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        fn = ns.get("decide")
        if not callable(fn):
            return {"ok": False, "error": "source does not define decide(s)"}
        probe = {"phase": 0, "elapsed": 10, "green_q": 1, "cross_q": 2, "cross_wait": 5, "gap": 1, "t": 10}
        try:
            out = fn(probe)
        except Exception as exc:
            return {"ok": False, "error": f"decide() raised {type(exc).__name__}: {exc}"}
        return {"ok": isinstance(out, bool), "returns": out}

    def heldout(self, program):
        self._check("final")
        return final_report(program, who="services.heldout")

    @property
    def spent(self):
        return self.ev.ledger.units


__all__ = ["Services", "ServiceError", "BudgetExhausted", "compile_program", "_simulate"]
