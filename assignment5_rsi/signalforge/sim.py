"""A one-intersection traffic simulator. This is the environment the RSI methods improve a controller for.

Model (deliberately small, but with real queueing):

* Four approaches N, S, E, W. Phase 0 gives green to N+S, phase 1 gives green to E+W.
* Time advances in 1-second steps. Arrivals are pre-generated per instance, so every
  controller sees exactly the same traffic (an instance is a fixed benchmark problem).
* During green a queue discharges one vehicle every ``SAT_HEADWAY`` seconds, after a
  ``STARTUP_LOST`` delay at the start of each green.
* Switching costs ``CLEARANCE`` seconds of yellow + all-red, when nobody moves.

The controller is a Python function ``decide(s) -> bool`` (True = switch now). It reads a
small state dict ``s`` with these keys:

    phase       0 (N/S green) or 1 (E/W green)
    elapsed     seconds since the current green started
    green_q     vehicles queued on the two green approaches
    cross_q     vehicles queued on the two red approaches
    cross_wait  how long the oldest vehicle on a red approach has waited (s)
    gap         seconds since a car last crossed the green detector (0 while a green queue remains)
    t           simulation time (s)

The score for one instance is the average delay per vehicle and the worst single wait.
An instance is *solved* when both are within the service targets below. That gives a
pass/fail benchmark like HumanEval: "solve rate" = fraction of instances solved.
"""
from collections import deque

SAT_HEADWAY = 2       # s between departures per approach during green
STARTUP_LOST = 2      # s at the start of each green with no departures
CLEARANCE = 4         # yellow + all-red seconds per switch
PHASES = ((0, 1), (2, 3))   # approach indices for phase 0 (N,S) and phase 1 (E,W)

DELAY_TARGET = 18.0   # s: average delay per vehicle must be at most this
WAIT_TARGET = 70      # s: no vehicle may wait longer than this (fairness / pedestrians)


def simulate(decide, instance):
    """Run one controller on one instance. Returns a dict of metrics."""
    arrivals = instance.arrivals
    horizon = instance.horizon
    queues = [deque(), deque(), deque(), deque()]
    nxt = [0, 0, 0, 0]
    last_arrival = [-10 ** 6] * 4
    phase, elapsed, clearing = 0, 0, 0
    delay_sum, vehicles, max_wait, switches = 0, 0, 0, 0
    s = {"phase": 0, "elapsed": 0, "green_q": 0, "cross_q": 0, "cross_wait": 0, "gap": 0, "t": 0}

    for t in range(horizon):
        for a in range(4):                       # 1. arrivals join the back of their queue
            arr = arrivals[a]
            i = nxt[a]
            while i < len(arr) and arr[i] == t:
                queues[a].append(t)
                last_arrival[a] = t
                i += 1
            nxt[a] = i

        if clearing:                             # 2. yellow/all-red: nobody moves
            clearing -= 1
            if clearing == 0:
                phase, elapsed = 1 - phase, 0
            continue

        g0, g1 = PHASES[phase]                   # 3. ask the controller
        c0, c1 = PHASES[1 - phase]
        qc0, qc1 = queues[c0], queues[c1]
        s["phase"] = phase
        s["elapsed"] = elapsed
        s["green_q"] = len(queues[g0]) + len(queues[g1])
        s["cross_q"] = len(qc0) + len(qc1)
        s["cross_wait"] = max(t - qc0[0] if qc0 else 0, t - qc1[0] if qc1 else 0)
        # a detector sees no gap while queued cars are still crossing it
        s["gap"] = 0 if s["green_q"] else t - max(last_arrival[g0], last_arrival[g1])
        s["t"] = t
        if decide(s):
            clearing = CLEARANCE
            switches += 1
            continue

        if elapsed >= STARTUP_LOST and (elapsed - STARTUP_LOST) % SAT_HEADWAY == 0:
            for a in (g0, g1):                   # 4. discharge one vehicle per green approach
                q = queues[a]
                if q:
                    w = t - q.popleft()
                    delay_sum += w
                    vehicles += 1
                    if w > max_wait:
                        max_wait = w
        elapsed += 1

    for q in queues:                             # 5. vehicles still waiting count with their wait so far
        for at in q:
            w = horizon - at
            delay_sum += w
            vehicles += 1
            if w > max_wait:
                max_wait = w

    avg_delay = delay_sum / vehicles if vehicles else 0.0
    delay_ok = avg_delay <= DELAY_TARGET
    wait_ok = max_wait <= WAIT_TARGET
    if delay_ok and wait_ok:
        fail = None
    elif not delay_ok and not wait_ok:
        fail = "both"
    else:
        fail = "delay" if not delay_ok else "wait"
    return {
        "instance": instance.iid,
        "family": instance.family,
        "solved": fail is None,
        "fail": fail,
        "avg_delay": round(avg_delay, 2),
        "max_wait": max_wait,
        "vehicles": vehicles,
        "switches": switches,
    }
