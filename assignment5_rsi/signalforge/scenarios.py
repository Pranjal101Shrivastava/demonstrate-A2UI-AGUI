"""Benchmark instances: eight traffic "families", each instance a seeded 10-minute traffic sample.

The splits mirror the Budget RSI paper's protocol (arXiv:2610.29121 as summarised in the course):

* ``fit``      16 instances: the only labels the Budget RSI readout may be trained on.
* ``steering`` 48 instances: what search uses to compare candidates ("steering counts").
* ``heldout``  100 instances: the final boundary. Search code never receives it; only
  :func:`signalforge.evaluator.final_report` may read it, once a search has finished.

Every split is stratified over the eight families and the seeds are disjoint, so no
instance appears in two splits.
"""
import random
from dataclasses import dataclass, field

HORIZON = 600  # seconds per instance

FAMILIES = (
    "balanced_light",   # 0.06 veh/s per approach: short greens and skipping empty phases help
    "balanced_heavy",   # near capacity: long greens cut the lost time spent switching
    "ns_dominant",      # N/S carries 4-5x the E/W traffic: needs asymmetric green splits
    "ew_dominant",      # mirror image of ns_dominant
    "am_rush_ramp",     # demand rises steadily from light to heavy across the 10 minutes
    "stadium_surge",    # moderate base, then one approach floods for two minutes
    "night_sparse",     # almost empty: fixed-time plans make lone cars wait for nothing
    "platoon_pulses",   # E/W arrives in platoons from an upstream signal, N/S steady
)


@dataclass
class Instance:
    iid: str
    family: str
    seed: int
    horizon: int
    arrivals: list = field(repr=False)   # four sorted lists of arrival seconds (N, S, E, W)


def _rates(family, rng, horizon):
    """Return a function rate(approach, t) in vehicles/second for this instance."""
    k = rng.uniform(0.85, 1.15)          # instance-level demand scaling
    if family == "balanced_light":
        return lambda a, t: 0.06 * k
    if family == "balanced_heavy":
        return lambda a, t: 0.165 * k
    if family in ("ns_dominant", "ew_dominant"):
        major = (0, 1) if family == "ns_dominant" else (2, 3)
        hi, lo = 0.26 * k, rng.uniform(0.04, 0.07)
        return lambda a, t: hi if a in major else lo
    if family == "am_rush_ramp":
        return lambda a, t: (0.04 + 0.16 * t / horizon) * k
    if family == "stadium_surge":
        surge = rng.randrange(4)
        start = rng.randrange(150, 330)
        return lambda a, t: 0.40 if (a == surge and start <= t < start + 120) else 0.08 * k
    if family == "night_sparse":
        return lambda a, t: 0.02 * k
    if family == "platoon_pulses":
        period = rng.choice((50, 60, 70))
        offset = rng.randrange(period)
        return lambda a, t: (0.10 * k if a < 2 else (0.55 if (t + offset) % period < 14 else 0.01))
    raise ValueError(family)


def make_instance(family, seed, horizon=HORIZON):
    rng = random.Random(f"{family}:{seed}")
    rate = _rates(family, rng, horizon)
    arrivals = [[t for t in range(horizon) if rng.random() < rate(a, t)] for a in range(4)]
    return Instance(iid=f"{family}#{seed}", family=family, seed=seed, horizon=horizon, arrivals=arrivals)


def _split(n, seed_base):
    out = []
    for i in range(n):
        fam = FAMILIES[i % len(FAMILIES)]
        out.append(make_instance(fam, seed_base + i))
    return out


_CACHE = {}


def splits():
    """The three fixed splits. Seeds are disjoint ranges, so splits never overlap."""
    if not _CACHE:
        _CACHE["fit"] = _split(16, 1_000)
        _CACHE["steering"] = _split(48, 2_000)
        _CACHE["heldout"] = _split(100, 9_000)
    return _CACHE


def family_of(instances, family):
    return [x for x in instances if x.family == family]
