"""Method 1: Budget RSI, which scores edits before running them (arXiv:2610.29121, course labs 10.03-10.05).

The mechanism as the course summarises it:

1. Fit one *linear readout* on [parent solve rate, 8 diff coordinates] from 96 scaffold
   edits, each labelled by evaluating the child on a 16-instance **fit** split.
2. Search a tree of programs with *Huxley-Godel Machine* selection. Draw a parent by
   Thompson sampling on the steering counts of already-evaluated nodes. The parent
   proposes K children. The readout scores them **without running them**, and only
   the top-scored child is expanded (evaluated on the 48-instance steering split).
3. Return the earliest evaluated node whose steering solve count is maximal.

Three selection modes share everything else, which makes the comparison controlled:

    readout       HGM parent + readout picks the child              (Budget RSI)
    parent_rate   HGM parent + readout that only sees parent rate   (the paper's ablation:
                  every child gets the same score, so the pick is arbitrary)
    random        uniform parent + random child                     (no HGM, no readout)

Where the *recursive* part lives: the readout is part of the improver. With
``online_refit=True`` (lab 10.05), every expansion becomes a new labelled example and the
readout is refitted, so the improver revises its own selection rule as it searches.
"""
import random

from ..diff_features import FEATURE_NAMES, RICH_FEATURE_NAMES, diff_features, rich_diff_features
from ..program import SEED_PROGRAM, random_edit, random_program
from ..stats import ridge, spearman
from .common import Tracker, until_exhausted


class LinearReadout:
    """score = w . [1, parent_rate, selected diff coordinates], fitted by ridge least squares.

    ``all_names`` names the full feature vector that will be passed in, which is the 8
    paper-style coordinates by default or ``RICH_FEATURE_NAMES`` for lab 10.05.
    ``features`` picks the subset the readout may use (lab 10.04 drops some).
    """

    def __init__(self, features=FEATURE_NAMES, use_parent=True, lam=1e-2, all_names=FEATURE_NAMES):
        self.all_names = tuple(all_names)
        self.features = tuple(features)
        self.use_parent = use_parent
        self.lam = lam
        self.w = None
        self.X, self.y = [], []

    @property
    def names(self):
        return ("bias",) + (("parent_rate",) if self.use_parent else ()) + self.features

    def row(self, parent_rate, feats):
        sel = [feats[self.all_names.index(f)] for f in self.features]
        return [1.0] + ([parent_rate] if self.use_parent else []) + sel

    def add(self, parent_rate, feats, label):
        self.X.append(self.row(parent_rate, feats))
        self.y.append(label)

    def fit(self):
        self.w = ridge(self.X, self.y, self.lam, free=(0,))
        return self

    def score(self, parent_rate, feats):
        return sum(a * b for a, b in zip(self.w, self.row(parent_rate, feats)))

    def coefficients(self):
        return dict(zip(self.names, self.w))


def collect_scaffold_edits(ev, seed=0, n_parents=12, per_parent=8, climb_steps=4, regime="climb",
                           featurize=diff_features):
    """96 labelled scaffold edits (12 parents x 8 children), each child run on the fit split.

    regime="climb"  (default) parents are snapshots of a cheap hill-climb *on the fit split*.
                    Each snapshot is followed by ``climb_steps`` more proposals. The labelled
                    edits therefore come from the same kind of improving parents the search
                    will expand later. This matches the paper, where scaffold edits come from
                    the agent's own improvement trajectory.
    regime="random" parents are random walks from the seed program. Lab 10.04 uses this
                    to show what distribution shift does to a readout.

    Returns rows of (parent_rate, features, child_rate, edit). Every evaluation is charged
    to the ledger under "readout-labels".
    """
    rng = random.Random(10_000 + seed)
    rows = []
    cur = SEED_PROGRAM
    cur_rep = ev.run(cur, "fit", purpose="readout-labels")
    for i in range(n_parents):
        if regime == "random":
            cur = SEED_PROGRAM if i == 0 else random_program(rng, depth=rng.randint(1, 6))
            cur_rep = ev.run(cur, "fit", purpose="readout-labels")
        elif i:
            for _ in range(climb_steps):
                e = random_edit(cur, rng)
                r = ev.run(e.child, "fit", purpose="readout-labels")
                if r.key() >= cur_rep.key():
                    cur, cur_rep = e.child, r
        for _ in range(per_parent):
            e = random_edit(cur, rng)
            crate = ev.run(e.child, "fit", purpose="readout-labels").rate
            rows.append((cur_rep.rate, featurize(cur.source, e.child.source), crate, e))
    return rows


def train_readout(rows, features=FEATURE_NAMES, use_parent=True, label_noise_seed=None, all_names=FEATURE_NAMES):
    r = LinearReadout(features, use_parent, all_names=all_names)
    labels = [row[2] for row in rows]
    if label_noise_seed is not None:            # negative control: break the feature-label link
        random.Random(label_noise_seed).shuffle(labels)
    for (prate, feats, _, _), lab in zip(rows, labels):
        r.add(prate, feats, lab)
    return r.fit()


def _thompson(nodes, rng):
    best, best_draw = None, -1.0
    for node in nodes:
        rep = node["report"]
        draw = rng.betavariate(1 + rep.solved, 1 + rep.n - rep.solved)
        if draw > best_draw:
            best, best_draw = node, draw
    return best


def search(ev, readout=None, mode="readout", seed=0, k_children=8, max_expansions=None,
           online_refit=False, featurize=diff_features):
    rng = random.Random(seed)
    tr = Tracker(ev)
    root_rep = ev.run(SEED_PROGRAM, purpose="expansion")
    nodes = [{"program": SEED_PROGRAM, "report": root_rep, "order": 0}]
    seen = {SEED_PROGRAM.key}
    tr.offer(SEED_PROGRAM, root_rep)
    log = []   # (predicted score, realised steering rate) per expansion: readout validity

    def loop():
        while max_expansions is None or len(nodes) - 1 < max_expansions:
            parent = rng.choice(nodes) if mode == "random" else _thompson(nodes, rng)
            p, prate = parent["program"], parent["report"].rate
            cands = []
            for _ in range(k_children * 3):          # propose K distinct, unseen children
                e = random_edit(p, rng)
                if e.child.key not in seen and all(e.child.key != c[0].child.key for c in cands):
                    cands.append((e, featurize(p.source, e.child.source)))
                if len(cands) == k_children:
                    break
            if not cands:
                continue
            if mode == "readout":
                scored = [(readout.score(prate, f), i) for i, (_, f) in enumerate(cands)]
                pred, idx = max(scored)
            elif mode == "parent_rate":
                pred, idx = (readout.score(prate, cands[0][1]) if readout else 0.0), 0
            else:
                pred, idx = 0.0, rng.randrange(len(cands))
            e, feats = cands[idx]
            rep = ev.run(e.child, purpose="expansion")
            seen.add(e.child.key)
            nodes.append({"program": e.child, "report": rep, "order": len(nodes), "edit": e})
            log.append({"pred": pred, "real": rep.rate, "desc": e.desc, "parent_rate": prate,
                        "solved": rep.solved, "program": e.child})
            tr.offer(e.child, rep)
            if online_refit and readout is not None:
                readout.add(prate, feats, rep.rate)
                readout.fit()

    until_exhausted(loop)
    top = max(n["report"].solved for n in nodes)
    chosen = min((n for n in nodes if n["report"].solved == top), key=lambda n: n["order"])
    res = tr.result(f"budget_rsi[{mode}{'+refit' if online_refit else ''}]", trace=log,
                    expansions=len(nodes) - 1,
                    readout_spearman=spearman([x["pred"] for x in log], [x["real"] for x in log]) if mode == "readout" else None)
    res.best, res.best_report = chosen["program"], chosen["report"]   # the paper's return rule
    return res


def budget_rsi(ev, seed=0, online_refit=False, k_children=8, rich=False):
    """The full method under a total budget: readout training is charged to the run."""
    fz, names = (rich_diff_features, RICH_FEATURE_NAMES) if rich else (diff_features, FEATURE_NAMES)
    rows = collect_scaffold_edits(ev, seed, featurize=fz)
    ro = train_readout(rows, features=names, all_names=names)
    res = search(ev, ro, "readout", seed, k_children=k_children, online_refit=online_refit, featurize=fz)
    res.method = "budget_rsi" + ("+refit" if online_refit else "")
    res.extras["coefficients"] = ro.coefficients()
    return res
