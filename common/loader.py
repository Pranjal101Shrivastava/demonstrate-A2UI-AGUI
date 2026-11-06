"""Discover and import the 24 examples (NN_tech/NN_mode/example.py)."""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def example_dirs():
    return sorted(p.parent for p in ROOT.glob("[0-9][0-9]_*/[0-9][0-9]_*/example.py"))


def load(path):
    path = pathlib.Path(path)
    if path.is_dir():
        path = path / "example.py"
    name = "ex_" + "_".join(path.parent.relative_to(ROOT).parts)
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    sys.path.insert(0, str(path.parent))  # lets an example import its sibling modules
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return mod
