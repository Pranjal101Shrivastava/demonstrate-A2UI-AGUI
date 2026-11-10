"""Eight features of a *proposed* edit, read from the source diff alone (nothing is executed).

This is the Budget RSI idea (arXiv:2610.29121): score an edit before running it, from
coordinates of its diff. The paper's eight coordinates are repository-level (lines,
files added/removed, imports, functions). Our programs are one file, so the three
file/import coordinates are replaced by three code-structure coordinates that a static
reader can also compute:

    0 lines_added        '+' lines in the unified diff
    1 lines_deleted      '-' lines in the unified diff
    2 funcs_added        new top-level ``def`` names
    3 funcs_deleted      removed top-level ``def`` names
    4 branch_delta       change in the number of ``if`` statements
    5 switch_path_delta  change in the number of ``return True`` paths (ways to end a green)
    6 consts_changed     number of constants whose value changed
    7 const_log_change   sum of log(new/old) over changed constants (signed: <0 means the
                         edit tightens thresholds, >0 means it relaxes them)
"""
import ast
import difflib
import math

FEATURE_NAMES = (
    "lines_added", "lines_deleted", "funcs_added", "funcs_deleted",
    "branch_delta", "switch_path_delta", "consts_changed", "const_log_change",
)


def _structure(src):
    tree = ast.parse(src)
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    consts = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant):
            consts[n.targets[0].id] = n.value.value
    ifs = sum(isinstance(n, ast.If) for n in ast.walk(tree))
    true_returns = sum(
        isinstance(n, ast.Return) and isinstance(n.value, ast.Constant) and n.value.value is True
        for n in ast.walk(tree)
    )
    return funcs, consts, ifs, true_returns


def diff_features(parent_src, child_src):
    added = deleted = 0
    for line in difflib.unified_diff(parent_src.splitlines(), child_src.splitlines(), lineterm="", n=0):
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted += 1
    pf, pc, pif, pret = _structure(parent_src)
    cf, cc, cif, cret = _structure(child_src)
    changed = [k for k in pc.keys() & cc.keys() if pc[k] != cc[k]]
    log_change = sum(math.log(cc[k] / pc[k]) for k in changed if pc[k] and cc[k])
    return [
        float(added), float(deleted),
        float(len(cf - pf)), float(len(pf - cf)),
        float(cif - pif), float(cret - pret),
        float(len(changed)), round(log_change, 4),
    ]


def unified_diff(parent_src, child_src):
    return "\n".join(difflib.unified_diff(parent_src.splitlines(), child_src.splitlines(),
                                          "parent.py", "child.py", lineterm="", n=1))


# ---------------------------------------------------------------------------------------
# Task-specific features (lab 10.05: "feature choice matters for your task"). Still purely
# static: they are read off the two source files without running anything.
# ---------------------------------------------------------------------------------------
_CONSTS = ("MIN_GREEN", "FIXED_GREEN", "GAP_OUT", "MAX_GREEN", "PRESSURE_RATIO", "STARVE_LIMIT")
_HELPERS = ("starving", "capped", "cross_empty", "outweighed", "gapped_out")
RICH_FEATURE_NAMES = FEATURE_NAMES + tuple(f"dlog_{c}" for c in _CONSTS) + tuple(f"toggle_{h}" for h in _HELPERS)


def rich_diff_features(parent_src, child_src):
    """The 8 generic coordinates + signed log change per named constant + +-1 per helper added/removed."""
    base = diff_features(parent_src, child_src)
    pf, pc, _, _ = _structure(parent_src)
    cf, cc, _, _ = _structure(child_src)
    per = [math.log(cc[k] / pc[k]) if (k in pc and k in cc and pc[k] != cc[k]) else 0.0 for k in _CONSTS]
    tog = [1.0 if (h in cf and h not in pf) else -1.0 if (h in pf and h not in cf) else 0.0 for h in _HELPERS]
    return base + per + tog
