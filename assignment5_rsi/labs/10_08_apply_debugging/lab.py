"""Lab 10.08: apply SO-RSI to a debugging task from this very project.

The task: a teammate adds a unit test for the simulator's discharge rule, and it fails.

    T1  a 60 s green with a long queue releases 30 vehicles   ("0.5 veh/s x 60 s", NEW, failing)
    T2  the first departure happens 2 s into green            (startup lost time)
    T3  departures are exactly 2 s apart                      (saturation headway)
    T4  nobody departs after the green has ended

A first-order debugger patches the code until T1 passes. Every attempt below is real: the
patched discharge rule is compiled and the four tests are run. We record what changed,
what happened and what was expected (the lab's step 3), then run the SO-RSI anomaly
detector over that trace (step 4), then a second-order probe for the root cause (step 5).
"""
import itertools
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from signalforge.labkit import banner, save, section, table  # noqa: E402
from signalforge.methods.so_rsi import detect  # noqa: E402
from signalforge.sim import SAT_HEADWAY, STARTUP_LOST  # noqa: E402

banner("LAB 10.08 · APPLY SO-RSI TO A REAL DEBUGGING TASK")

TEMPLATE = """
def departure_times(green, lost={lost}, headway={headway}):
    # same rule as signalforge/sim.py step 4: depart when elapsed >= lost and (elapsed - lost) % headway == 0
    return [e for e in range(green{extra}) if e >= lost and (e - lost) % headway == 0]
"""


def build(lost=STARTUP_LOST, headway=SAT_HEADWAY, extra=""):
    ns = {}
    exec(TEMPLATE.format(lost=lost, headway=headway, extra=extra), ns)
    return ns["departure_times"]


TESTS = {
    "T1 60 s green -> 30 departures": lambda f: len(f(60)) == 30,
    "T2 first departure at 2 s": lambda f: f(60)[0] == 2,
    "T3 headway exactly 2 s": lambda f: all(b - a == 2 for a, b in zip(f(60), f(60)[1:])),
    "T4 none after green ends": lambda f: max(f(60)) < 60,
}


def run_tests(fn):
    return {name: bool(t(fn)) for name, t in TESTS.items()}


section("The code as shipped")
shipped = build()
res0 = run_tests(shipped)
print(f"departure_times(60) has {len(shipped(60))} departures: {shipped(60)[:5]} ... {shipped(60)[-2:]}")
table([[k, "pass" if v else "FAIL"] for k, v in res0.items()], ["test", "result"])

section("First-order debugging: patch until T1 is green (each attempt executed)")
ATTEMPTS = [  # (op key, description, patch kwargs, what the developer expected, expected car count)
    (("decrease", "lost"), "lost 2 -> 1 (cars start sooner)", {"lost": 1}, "T1 passes, nothing else changes", 30),
    (("increase", "lost"), "lost 1 -> 2 (T2 broke, revert)", {"lost": 2}, "back to 3/4, then try elsewhere", 29),
    (("add", "range+1"), "range(green) -> range(green + 1)", {"extra": " + 1"}, "classic off-by-one, all pass", 30),
    (("decrease", "headway"), "headway 2 -> 1 (more throughput)", {"headway": 1}, "one more car -> 30", 30),
    (("decrease", "lost"), "lost 2 -> 1 again (maybe T2 is wrong)", {"lost": 1}, "T1 passes", 30),
    (("increase", "headway"), "headway 1 -> 2 (revert)", {"headway": 2}, "back to 3/4", 29),
]
trace = []
prev_pass = sum(res0.values())
rows = []
for op, desc, kw, exp_text, exp_cars in ATTEMPTS:
    r = run_tests(build(**kw))
    passed = sum(r.values())
    n = len(build(**kw)(60))
    entry = {"op": op, "desc": desc, "delta": passed - prev_pass, "accepted": passed == 4,
             "expected": 1.0, "n": n}
    trace.append(entry)
    # recurrence / opposing: the generic SO-RSI detector on the edit trace.
    # mismatch: here the developer's expectation is a car count, so compare that quantity.
    entry["anomalies"] = [a for a in detect(trace) if a != "mismatch"]
    if abs(n - exp_cars) >= 3:
        entry["anomalies"].append("mismatch")
    fails = [k.split()[0] for k, v in r.items() if not v]
    rows.append([len(trace), desc, exp_text, f"{passed}/4 (fails {','.join(fails) or '-'}; {entry['n']} cars)",
                 ", ".join(entry["anomalies"]) or "-"])
table(rows, ["#", "what changed", "what we expected", "what happened", "SO-RSI anomaly"])

section("Retrospective (lab step 4): which anomalies, and what they point at")
found = {a for t in trace for a in t["anomalies"]}
for a, meaning in (("recurrence", "attempt 5 repeats attempt 1: the same fix keeps 'almost' working"),
                   ("opposing", "lost and headway were each pushed one way and then back"),
                   ("mismatch", "headway 2->1 was meant to add ONE car and added 28: our model of the code is off")):
    print(f"  {'[x]' if a in found else '[ ]'} {a:10s} {meaning}")

section("Second-order probe (step 5): can ANY version of the code pass all four tests?")
space = list(itertools.product(range(0, 5), range(1, 4), ("", " + 1")))
sat = [(l, h, x) for l, h, x in space if all(run_tests(build(l, h, x)).values())]
print(f"searched {len(space)} code variants (lost 0-4, headway 1-3, with/without off-by-one): {len(sat)} pass all four")
pairs = {}
for drop in TESTS:
    ok = [(l, h, x) for l, h, x in space if all(v for k, v in run_tests(build(l, h, x)).items() if k != drop)]
    pairs[drop] = ok
    print(f"  without '{drop}': {len(ok)} variant(s) pass, e.g. {ok[:1]}")
culprit = [k for k, v in pairs.items() if v and (STARTUP_LOST, SAT_HEADWAY, "") in v]
print(f"\nRoot cause: the tests are mutually inconsistent, and dropping {culprit} makes the SHIPPED")
print("code pass. T1's author forgot the startup lost time: a 60 s green can only release")
print(f"floor((60 - {STARTUP_LOST} - 1) / {SAT_HEADWAY}) + 1 = {(60 - STARTUP_LOST - 1) // SAT_HEADWAY + 1} vehicles per approach.")
print("Fix the TEST (expect 29), not the code. Every first-order patch above 'fixed' T1 by")
print("breaking the physics that T2-T4 protect, which is exactly the thrashing SO-RSI is built to catch.")

save("10_08", {"trace": trace, "anomalies": sorted(found), "variants_passing_all": len(sat), "culprit": culprit})
