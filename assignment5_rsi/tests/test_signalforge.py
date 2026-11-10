"""Unit tests: simulator physics, split hygiene, the final boundary, and each mechanism's core."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from signalforge import evaluator as E  # noqa: E402
from signalforge.diff_features import diff_features, rich_diff_features  # noqa: E402
from signalforge.evaluator import BudgetExhausted, SearchEvaluator, final_report  # noqa: E402
from signalforge.methods import budget_rsi as B  # noqa: E402
from signalforge.methods.areal_rsi import areal_rsi  # noqa: E402
from signalforge.methods.baselines import naive_rsi, random_search  # noqa: E402
from signalforge.methods.rsiflow import rsiflow  # noqa: E402
from signalforge.methods.self_hpo import self_hpo  # noqa: E402
from signalforge.methods.so_rsi import detect, so_rsi, sweep_values  # noqa: E402
from signalforge.methods.swarm_rsi import swarm_rsi  # noqa: E402
from signalforge.metrics import recursive_learnability, rsi_index  # noqa: E402
from signalforge.program import COMPONENTS, SEED_PROGRAM, Program, all_ops, apply_op, compile_program, toggle  # noqa: E402
from signalforge.scenarios import FAMILIES, Instance, splits  # noqa: E402
from signalforge.services import ServiceError, Services  # noqa: E402
from signalforge.sim import simulate  # noqa: E402
from signalforge.stats import ridge, spearman  # noqa: E402


class TestSimulator(unittest.TestCase):
    def test_saturation_flow_matches_lab_10_08(self):
        # one long queue on N, never switch: a 60 s green releases 29 cars (2 s lost, 2 s headway)
        inst = Instance("t", "test", 0, 60, [[0] * 40, [], [], []])
        res = simulate(lambda s: False, inst)
        # 29 served at t = 2, 4, ..., 58 and 11 still queued (censored at 60 s)
        expected = (sum(range(2, 60, 2)) + 11 * 60) / 40
        self.assertEqual(res["vehicles"], 40)
        self.assertAlmostEqual(res["avg_delay"], round(expected, 2))
        self.assertEqual(res["max_wait"], 60)

    def test_seed_program_is_deterministic(self):
        a, b = final_report(SEED_PROGRAM, who="test"), final_report(SEED_PROGRAM, who="test")
        self.assertEqual(a.solved, b.solved)
        self.assertEqual(a.solved, 31)

    def test_good_controller_beats_fixed_time(self):
        good = Program(on=frozenset({"actuated", "max_cap"}), gap_out=3, max_green=50)
        self.assertGreater(final_report(good, who="test").solved, final_report(SEED_PROGRAM, who="test").solved + 40)


class TestSplits(unittest.TestCase):
    def test_sizes_disjoint_stratified(self):
        s = splits()
        self.assertEqual([len(s[k]) for k in ("fit", "steering", "heldout")], [16, 48, 100])
        ids = [set(x.iid for x in s[k]) for k in ("fit", "steering", "heldout")]
        self.assertFalse(ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2])
        for k in ("fit", "steering", "heldout"):
            self.assertEqual({x.family for x in s[k]}, set(FAMILIES))


class TestProgram(unittest.TestCase):
    def test_every_operator_yields_compilable_source(self):
        p = Program(on=frozenset(COMPONENTS))
        for op in all_ops(p) + all_ops(SEED_PROGRAM):
            base = p if op in all_ops(p) else SEED_PROGRAM
            e = apply_op(base, op)
            self.assertIsInstance(compile_program(e.child)({"phase": 0, "elapsed": 99, "green_q": 0, "cross_q": 3,
                                                           "cross_wait": 200, "gap": 9, "t": 1}), bool)

    def test_diff_features_read_structure(self):
        e = toggle(SEED_PROGRAM, "starvation_guard")
        f = diff_features(SEED_PROGRAM.source, e.child.source)
        self.assertEqual(f[2], 1.0)    # one helper function added
        self.assertEqual(f[5], 1.0)    # one more 'return True' path
        self.assertEqual(len(rich_diff_features(SEED_PROGRAM.source, e.child.source)), 19)


class TestBoundary(unittest.TestCase):
    def test_search_cannot_see_heldout(self):
        ev = SearchEvaluator()
        with self.assertRaises(PermissionError):
            ev.split("heldout")
        with self.assertRaises(PermissionError):
            ev.run(SEED_PROGRAM, instances=splits()["heldout"][:1])

    def test_budget_enforced_and_cache_free(self):
        ev = SearchEvaluator(budget=60)
        ev.run(SEED_PROGRAM)                 # 48
        ev.run(SEED_PROGRAM)                 # cached: free
        self.assertEqual(ev.ledger.units, 48)
        with self.assertRaises(BudgetExhausted):
            ev.run(Program(min_green=10))

    def test_no_method_reads_heldout(self):
        before = len(E.FINAL_ACCESS_LOG)
        for fn in (random_search, naive_rsi, so_rsi, swarm_rsi, areal_rsi, rsiflow, self_hpo):
            fn(SearchEvaluator(budget=400), seed=0)
        B.search(SearchEvaluator(budget=400), None, "random", seed=0)
        self.assertEqual(len(E.FINAL_ACCESS_LOG), before)


class TestMechanisms(unittest.TestCase):
    def test_ridge_recovers_weights(self):
        X = [[1.0, x, x * x % 7] for x in range(20)]
        y = [2 + 3 * r[1] - 0.5 * r[2] for r in X]
        w = ridge(X, y, lam=0.0)
        self.assertAlmostEqual(w[1], 3, places=6)
        self.assertAlmostEqual(w[2], -0.5, places=6)

    def test_spearman(self):
        self.assertAlmostEqual(spearman([1, 2, 3], [10, 20, 30]), 1.0)
        self.assertAlmostEqual(spearman([1, 2, 3], [3, 2, 1]), -1.0)

    def test_readout_negative_control_changes_weights(self):
        rows = B.collect_scaffold_edits(SearchEvaluator(), 0)
        a, b = B.train_readout(rows), B.train_readout(rows, label_noise_seed=1)
        self.assertNotEqual(a.coefficients(), b.coefficients())

    def test_so_rsi_detector(self):
        t = [{"op": ("increase", "min_green"), "accepted": False, "delta": -1, "expected": 0.0}]
        t.append({"op": ("decrease", "min_green"), "accepted": False, "delta": -1, "expected": 0.0})
        self.assertIn("opposing", detect(t))
        t.append({"op": ("decrease", "min_green"), "accepted": False, "delta": -1, "expected": 0.0})
        self.assertIn("recurrence", detect(t))
        t.append({"op": ("add", "pressure"), "accepted": False, "delta": -5, "expected": 1.0})
        self.assertIn("mismatch", detect(t))

    def test_sweep_values_stay_on_grid(self):
        self.assertEqual(sweep_values("gap_out"), [1, 3, 6, 8])
        self.assertTrue(all(isinstance(v, float) for v in sweep_values("pressure_ratio")))

    def test_rsi_index(self):
        idx, _ = rsi_index({"a": 0.5, "b": 0.2}, {"a": 0.75, "b": 0.6})
        self.assertAlmostEqual(idx, 0.5)
        idx, per = rsi_index({"a": 1.0, "b": 0.5}, {"a": 0.9, "b": 0.5})
        self.assertIsNone(per["a"])          # no gap: excluded
        self.assertEqual(idx, 0.0)

    def test_learnability(self):
        rl = recursive_learnability({"half": [0, 1, 0, 1], "all": [1, 1, 1, 1]})
        self.assertEqual(rl, {"half": 1.0, "all": 0.0})


class TestServices(unittest.TestCase):
    def test_permissions_and_sandbox(self):
        svc = Services(budget=100)
        self.assertFalse(svc.sandbox_exec("import os\ndef decide(s):\n    return True")["ok"])
        self.assertTrue(svc.sandbox_exec(SEED_PROGRAM.source)["ok"])
        with self.assertRaises(ServiceError):
            svc.heldout(SEED_PROGRAM)


if __name__ == "__main__":
    unittest.main()
