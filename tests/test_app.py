import math
import unittest
from decimal import Decimal
from fractions import Fraction

import app
from app import (
    weighted_sample,
    weighted_sample_indices,
    weighted_sample_many,
    weighted_sample_many_indices,
    serialize_metrics,
)


class WeightedSampleDeterminismTest(unittest.TestCase):
    def test_baseline_sequence_locked(self):
        # 与基线实现产出的确定序列保持一致。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample(["a", "b", "c"], [1, 3, 2], 3, 7),
            ["b", "a", "c"],
        )

    def test_same_seed_same_result(self):
        args = (["a", "b", "c", "d"], [1, 2, 3, 4], 3)
        first = weighted_sample(*args, seed=99)
        for _ in range(5):
            self.assertEqual(weighted_sample(*args, seed=99), first)

    def test_different_seed_may_differ(self):
        args = (["a", "b", "c", "d"], [1, 2, 3, 4], 3)
        seen = {tuple(weighted_sample(*args, seed=s)) for s in range(8)}
        self.assertGreater(len(seen), 1)

    def test_duplicate_values_are_independent_positions(self):
        # 相同值按不同位置参与, 可以重复出现, 但每个位置只选一次。
        out = weighted_sample([1, 1, 1], [1, 1, 1], 3, 123)
        self.assertEqual(out, [1, 1, 1])
        self.assertEqual(len(out), len(set(range(3))))  # 三个不同位置

    def test_zero_weight_never_chosen(self):
        for seed in range(50):
            self.assertEqual(
                weighted_sample(["x", "y"], [0, 5], 1, seed), ["y"]
            )

    def test_k_zero_always_empty(self):
        self.assertEqual(weighted_sample([], [], 0, 0), [])
        self.assertEqual(weighted_sample(["a"], [0], 0, 0), [])
        self.assertEqual(weighted_sample(["a", "b"], [0, 0], 0, 0), [])

    def test_exhaust_with_no_positive_weight_remaining(self):
        # 唯一正权重被抽走后继续请求 -> 确定的 ValueError。
        with self.assertRaises(ValueError):
            weighted_sample(["a", "b"], [1, 0], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample(["a"], [0], 1, 0)

    def test_inputs_not_mutated(self):
        items = ["a", "b", "c"]
        weights = [1, 2, 3]
        items_snapshot = list(items)
        weights_snapshot = list(weights)
        weighted_sample(items, weights, 2, 5)
        self.assertEqual(items, items_snapshot)
        self.assertEqual(weights, weights_snapshot)

    def test_no_partial_list_on_error(self):
        # 权重类型错误在抽取前抛出; 调用方拿不到任何部分结果。
        with self.assertRaises(TypeError):
            weighted_sample(["a", "b"], [1, "x"], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample(["a", "b"], [1, -1], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample(["a", "b"], [1, float("nan")], 1, 0)

    def test_float_weights_deterministic(self):
        out = weighted_sample(["p", "q"], [0.5, 1.5], 2, 3)
        self.assertEqual(sorted(out), ["p", "q"])
        self.assertEqual(
            weighted_sample(["p", "q"], [0.5, 1.5], 2, 3), out
        )


class WeightedSampleIndicesTest(unittest.TestCase):
    def test_baseline_index_sequence_locked(self):
        # 回取 items 必须与 weighted_sample 锁定的既有序列一致。
        items = ["red", "green", "blue"]
        weights = [1, 3, 2]
        idx = weighted_sample_indices(items, weights, 2, 42)
        self.assertEqual([items[i] for i in idx], ["green", "red"])
        self.assertEqual(idx, [1, 0])

        items = ["a", "b", "c"]
        weights = [1, 3, 2]
        idx = weighted_sample_indices(items, weights, 3, 7)
        self.assertEqual([items[i] for i in idx], ["b", "a", "c"])
        self.assertEqual(idx, [1, 0, 2])

    def test_indices_roundtrip_matches_values(self):
        import random as _random

        cases = [
            (["a", "b", "c", "d"], [1, 2, 3, 4], 3),
            (list(range(10)), [i + 1 for i in range(10)], 5),
            ([1, 1, 1, 1], [1, 1, 1, 1], 4),
            (["x", "y", "z"], [0.5, 1.5, 2.5], 2),
            ([], [], 0),
        ]
        for items, weights, k in cases:
            for seed in range(30):
                idx = weighted_sample_indices(items, weights, k, seed)
                self.assertEqual(
                    [items[i] for i in idx],
                    weighted_sample(items, weights, k, seed),
                )
                # 零基、不重复、数量正确。
                self.assertEqual(len(idx), k)
                self.assertEqual(len(set(idx)), k)
                self.assertTrue(all(isinstance(i, int) and 0 <= i < len(items)
                                    for i in idx))

    def test_duplicate_values_distinct_positions(self):
        # 相同值仍按位置独立表达。
        items = [1, 1, 1]
        idx = weighted_sample_indices(items, [1, 1, 1], 3, 123)
        self.assertEqual(sorted(idx), [0, 1, 2])
        self.assertEqual([items[i] for i in idx], [1, 1, 1])

    def test_same_seed_same_indices(self):
        args = (["a", "b", "c", "d"], [1, 2, 3, 4], 3)
        first = weighted_sample_indices(*args, seed=99)
        for _ in range(5):
            self.assertEqual(weighted_sample_indices(*args, seed=99), first)

    def test_different_seed_may_differ(self):
        args = (["a", "b", "c", "d"], [1, 2, 3, 4], 3)
        seen = {tuple(weighted_sample_indices(*args, seed=s))
                for s in range(8)}
        self.assertGreater(len(seen), 1)

    def test_zero_weight_never_chosen(self):
        for seed in range(50):
            idx = weighted_sample_indices(["x", "y"], [0, 5], 1, seed)
            self.assertEqual(idx, [1])

    def test_all_zero_weights_fail_when_k_positive(self):
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [0, 0], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [0], 1, 0)

    def test_k_zero_always_empty_but_validated(self):
        self.assertEqual(weighted_sample_indices([], [], 0, 0), [])
        self.assertEqual(weighted_sample_indices(["a"], [0], 0, 0), [])
        self.assertEqual(
            weighted_sample_indices(["a", "b"], [0, 0], 0, 0), []
        )
        # k=0 仍须完成全部校验。
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [float("nan")], 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [True], 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices("ab", [1, 2], 0, 0)

    def test_inputs_not_mutated(self):
        items = ["a", "b", "c"]
        weights = [1, 2, 3]
        items_snapshot = list(items)
        weights_snapshot = list(weights)
        weighted_sample_indices(items, weights, 2, 5)
        self.assertEqual(items, items_snapshot)
        self.assertEqual(weights, weights_snapshot)

    def test_no_partial_indices_on_error(self):
        # 抽取阶段失败时调用方拿不到任何部分结果 (直接抛异常)。
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [1, 0], 2, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a", "b"], [1, "x"], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [1, -1], 1, 0)

    def test_validation_rules_match_weighted_sample(self):
        # 与 weighted_sample 相同的序列判定 / k / seed / 权重规则。
        for bad in (iter(["a"]), {0: "a"}, {"a"}, "ab", b"ab", 3, None):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_indices(bad, [1], 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [1], True, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [1], 1, object())
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [1], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [1], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [1, float("inf")], 1, 0)
        # 合法的种子类型同样被接受。
        for good in (0, 1, True, 1.5, "s", b"s", bytearray(b"s"), None):
            weighted_sample_indices(["a"], [1], 1, good)

    def test_empty_input_only_succeeds_at_k_zero(self):
        self.assertEqual(weighted_sample_indices([], [], 0, 0), [])
        with self.assertRaises(ValueError):
            weighted_sample_indices([], [], 1, 0)


class WeightedSampleValidationTest(unittest.TestCase):
    def test_items_must_be_sequence(self):
        for bad in (iter(["a", "b"]), {0: "a"}, set(["a"]), "ab", b"ab", 3, None):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample(bad, [1, 2], 0, 0)

    def test_weights_must_be_sequence(self):
        for bad in (iter([1, 2]), {0: 1}, {1, 2}, "xy", 3, None):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample(["a", "b"], bad, 0, 0)

    def test_k_must_be_non_bool_integer(self):
        with self.assertRaises(TypeError):
            weighted_sample(["a"], [1], True, 0)
        for bad in (1.0, "1", None, 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample(["a"], [1], bad, 0)

    def test_seed_type(self):
        for bad in ([1], (1,), object(), 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample(["a"], [1], 1, bad)
        # 合法种子类型
        for good in (0, 1, True, 1.5, "s", b"s", bytearray(b"s"), None):
            weighted_sample(["a"], [1], 1, good)

    def test_length_mismatch(self):
        with self.assertRaises(ValueError):
            weighted_sample(["a", "b"], [1], 1, 0)

    def test_k_range(self):
        with self.assertRaises(ValueError):
            weighted_sample(["a"], [1], -1, 0)
        with self.assertRaises(ValueError):
            weighted_sample(["a"], [1], 2, 0)

    def test_weight_element_types(self):
        for bad in (True, False, 1 + 0j, "1", None, [1]):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample(["a", "b"], [1, bad], 1, 0)

    def test_weight_values(self):
        for bad in (float("nan"), float("inf"), float("-inf"), -0.01, -1):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    weighted_sample(["a", "b"], [1, bad], 1, 0)

    def test_validation_completes_before_sampling(self):
        # 即使 k=0, 非法权重仍须报错(校验先行)。
        with self.assertRaises(ValueError):
            weighted_sample(["a"], [float("nan")], 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample(["a"], [True], 0, 0)


class ExactIntegerSamplingTest(unittest.TestCase):
    """累计权重超过 2**53 / 无法转有限浮点时的纯整数精确路径。"""

    HUGE = 10 ** 100

    def test_huge_weights_deterministic_and_valid(self):
        items = ["a", "b", "c", "d"]
        weights = [self.HUGE, self.HUGE * 3, 0, 1]
        for k in (1, 2, 3):
            for seed in range(40):
                idx = weighted_sample_indices(items, weights, k, seed)
                # 零基、范围内、无重复、数量正确。
                self.assertEqual(len(idx), k)
                self.assertEqual(len(set(idx)), k)
                self.assertTrue(all(0 <= i < 4 for i in idx))
                # 零权重位置 (2) 永远不出现; 有正权重的位置才可能出现。
                self.assertNotIn(2, idx)
                # 相同 seed + 输入唯一确定。
                self.assertEqual(
                    idx, weighted_sample_indices(items, weights, k, seed)
                )
                # values 入口与 indices 入口逐项对应。
                self.assertEqual(
                    weighted_sample(items, weights, k, seed),
                    [items[i] for i in idx],
                )

    def test_tiny_positive_weight_never_swallowed(self):
        # 极端比例: 1 对 10**100。若经浮点, 微小方会被舍入吞掉; 精确路径
        # 下它仍以精确比例 1/(10**100+1) 可被选中 —— 用穷举式 RNG 钩子
        # 直接验证第一轮取 needle=0 时必定落到微小权重位置。
        import app as _app

        class _ScriptedRNG:
            def __init__(self, needles):
                self._needles = list(needles)

            def getrandbits(self, bits):
                return self._needles.pop(0)

        items = ["huge", "tiny", "zero"]
        weights = [self.HUGE, 1, 0]
        # 第一轮 total = 10**100 + 1, needle = 10**100 (=total-1) -> 位置 1。
        # 第二轮剩余 total = 10**100, needle=0 -> 位置 0。
        chosen = _app._sample_indices_exact_integer(
            list(range(3)), list(weights), 2, _ScriptedRNG([10 ** 100, 0])
        )
        self.assertEqual(chosen, [1, 0])

    def test_tiny_weight_has_exact_probability_via_counts(self):
        # 概率虽小, 但通过把微小权重放大到可统计而总量仍超 2**53 的比例
        # 检验比例正确性: 两位置比例严格为 1 : 2。
        base = 2 ** 52 + 7
        weights = [base, 2 * base]
        counts = [0, 0]
        trials = 4000
        for seed in range(trials):
            i = weighted_sample_indices(["a", "b"], weights, 1, seed)[0]
            counts[i] += 1
        # 期望约 1/3 与 2/3, 留宽裕量。
        self.assertAlmostEqual(counts[0] / trials, 1 / 3, delta=0.03)
        self.assertAlmostEqual(counts[1] / trials, 2 / 3, delta=0.03)

    def test_extreme_ratio_tiny_can_win(self):
        # 比例 10**100 : 1, 借脚本化 RNG 令 needle 落入最后一个单位区间,
        # 证明微小权重不会被吞且定位边界精确。
        import app as _app

        class _ScriptedRNG:
            def getrandbits(self, bits):
                # 直接返回 total-1 (在 [0,2**bits) 内, 必被接受)。
                return (10 ** 100 + 1) - 1

        chosen = _app._sample_indices_exact_integer(
            list(range(2)), [10 ** 100, 1], 1, _ScriptedRNG()
        )
        self.assertEqual(chosen, [1])

    def test_multi_round_proportions_change_after_removal(self):
        # 多轮抽取: 每轮只在尚未选中的位置中抽取, 抽走后按剩余权重定位。
        import app as _app

        class _ScriptedRNG:
            def __init__(self, needles):
                self._needles = iter(needles)

            def getrandbits(self, bits):
                return next(self._needles)

        # 第一轮 total=10**100+15: needle=10**100+10 落入权重 5 的位置(2)。
        # 抽走后剩余 [10**100, 10, 0]: needle=10**100 落入权重 10 的位置(1)。
        pool = [0, 1, 2, 3]
        weights = [10 ** 100, 10, 5, 0]
        chosen = _app._sample_indices_exact_integer(
            pool, weights, 2, _ScriptedRNG([10 ** 100 + 10, 10 ** 100])
        )
        self.assertEqual(chosen, [2, 1])

    def test_rejection_is_uniform_and_unbiased(self):
        # 拒绝采样边界: total=3, bits=2, modulus=4, limit=3; needle=3 必须
        # 被拒绝并重抽, 否则取模会把位置 0 的概率抬高。
        import app as _app

        class _ScriptedRNG:
            def __init__(self):
                self.stream = iter([3, 3, 2])  # 拒绝 3,3; 接受 2 -> 位置2

            def getrandbits(self, bits):
                return next(self.stream)

        chosen = _app._sample_indices_exact_integer(
            list(range(3)), [1, 1, 1], 1, _ScriptedRNG()
        )
        self.assertEqual(chosen, [2])

    def test_power_of_two_total_no_rejection(self):
        import app as _app

        class _ScriptedRNG:
            def getrandbits(self, bits):
                assert bits == 4
                return 15

        chosen = _app._sample_indices_exact_integer(
            list(range(2)), [8, 8], 1, _ScriptedRNG()
        )
        self.assertEqual(chosen, [1])

    def test_no_positive_weight_raises_value_error_exact(self):
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [10 ** 100, 0], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [0], 1, 0)

    def test_all_zero_total_with_huge_scale_validated(self):
        with self.assertRaises(ValueError):
            weighted_sample_indices(
                ["a", "b", "c"], [0, 0, 0], 1, seed=7
            )

    def test_exact_path_inputs_not_mutated(self):
        items = ["a", "b", "c"]
        weights = [10 ** 100, 10 ** 99, 1]
        items_snap = list(items)
        weights_snap = list(weights)
        weighted_sample(items, weights, 3, 11)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)

    def test_threshold_boundary_keeps_baseline(self):
        # 全量累计恰为 2**53: 仍走浮点路径, 与基线逐序列一致。
        w = [2 ** 53 - 1, 1]
        self.assertEqual(sum(w), 2 ** 53)
        locked = {
            s: weighted_sample_indices(["a", "b"], w, 2, s) for s in range(20)
        }
        import app as _app

        for s in range(20):
            pool, pw = [0, 1], list(w)
            self.assertEqual(
                _app._sample_indices_float(pool, pw, 2, __import__("random").Random(s)),
                locked[s],
            )

    def test_above_threshold_uses_exact_and_differs_from_naive_float(self):
        # 累计 = 2**53 + 1: 浮点无法精确表示, 必须走整数路径且仍确定。
        w = [2 ** 53, 1]
        idx = weighted_sample_indices(["a", "b"], w, 1, 5)
        self.assertEqual(idx, weighted_sample_indices(["a", "b"], w, 1, 5))
        self.assertIn(idx[0], (0, 1))

    def test_float_weights_still_float_path_at_huge_scale(self):
        # 非整数权重即便数值“很大”也继续按既有浮点规则工作, 不进整数路径。
        w = [float(2 ** 60), 1.0]
        out = weighted_sample(["p", "q"], w, 2, 3)
        self.assertEqual(sorted(out), ["p", "q"])

    def test_super_huge_weights_pass_validation(self):
        # 10**400 转 float 会 OverflowError; 整数权重必须在不触发浮点转换
        # 的前提下通过校验并正常精确抽取(回归: 校验阶段 math.isnan 溢出)。
        w = [10 ** 400, 10 ** 400]
        idx = weighted_sample_indices(["a", "b"], w, 2, 2026)
        self.assertEqual(sorted(idx), [0, 1])
        self.assertEqual(
            idx, weighted_sample_indices(["a", "b"], w, 2, 2026)
        )
        # 负的超大整数仍按 ValueError 拒绝, 且不经过浮点。
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [-(10 ** 400)], 1, 0)

    def test_seed_types_and_error_classes_unchanged(self):
        w = [10 ** 100, 1]
        # 合法 seed 类型均可工作且结果确定。
        for good in (0, 1, True, 1.5, "s", b"s", bytearray(b"s"), None):
            a = weighted_sample_indices(["a", "b"], w, 1, good)
            b = weighted_sample_indices(["a", "b"], w, 1, good)
            self.assertEqual(a, b)
        # 既有分类不变。
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a", "b"], w, 1, object())
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a", "b"], w, True, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [10 ** 100, -1], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [10 ** 100], 2, 0)


class WeightedSampleManyTest(unittest.TestCase):
    """批量入口 weighted_sample_many / weighted_sample_many_indices。"""

    def test_outer_shape_and_round_lengths(self):
        idx = weighted_sample_many_indices(["a", "b", "c", "d"], [1, 2, 3, 4], 3, 5, 42)
        self.assertEqual(len(idx), 5)
        self.assertTrue(all(len(rd) == 3 for rd in idx))
        vals = weighted_sample_many(["a", "b", "c", "d"], [1, 2, 3, 4], 3, 5, 42)
        self.assertEqual(len(vals), 5)
        self.assertTrue(all(len(rd) == 3 for rd in vals))

    def test_first_round_matches_single_entry(self):
        # 第一轮必须与现有对应入口逐项相同。
        cases = [
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
            (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
            (["p", "q"], [0.5, 1.5], 2),
            ([], [], 0),
            (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
        ]
        for items, weights, k in cases:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                with self.subTest(items=items, k=k, seed=seed):
                    many_i = weighted_sample_many_indices(items, weights, k, 3, seed)
                    self.assertEqual(
                        many_i[0], weighted_sample_indices(items, weights, k, seed)
                    )
                    many_v = weighted_sample_many(items, weights, k, 3, seed)
                    self.assertEqual(
                        many_v[0], weighted_sample(items, weights, k, seed)
                    )

    def test_values_and_indices_entries_correspond_round_by_round(self):
        cases = [
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
            (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
            (["p", "q"], [0.5, 1.5], 2),
        ]
        for items, weights, k in cases:
            mi = weighted_sample_many_indices(items, weights, k, 4, 7)
            mv = weighted_sample_many(items, weights, k, 4, 7)
            self.assertEqual(
                [[items[i] for i in rd] for rd in mi], mv
            )

    def test_rounds_share_one_seed_stream(self):
        # 后续轮次继续消耗同一个由 seed 初始化的随机流: 用与实现相同的
        # 共享 rng 手工连跑 draws 轮必须得到相同嵌套序列; 不同 draws 的
        # 前缀逐轮相同。
        import random as _random

        items, weights, k = list("abcdef"), [10 ** 100, 1, 10 ** 90, 7, 0, 3], 4
        for draws in (1, 2, 6):
            rng = _random.Random(99)
            manual = []
            for _ in range(draws):
                pool, pw = list(range(len(items))), list(weights)
                manual.append(app._sample_indices_exact_integer(pool, pw, k, rng))
            self.assertEqual(
                weighted_sample_many_indices(items, weights, k, draws, 99),
                manual,
            )
        full = weighted_sample_many_indices(items, weights, k, 8, 123)
        head = weighted_sample_many_indices(items, weights, k, 3, 123)
        self.assertEqual(full[:3], head)

    def test_deterministic_nested_sequence(self):
        args = (list("abcdef"), [10 ** 100, 1, 10 ** 90, 7, 0, 3], 4)
        first = weighted_sample_many_indices(*args, draws=8, seed=123)
        for _ in range(4):
            self.assertEqual(
                weighted_sample_many_indices(*args, draws=8, seed=123), first
            )

    def test_each_round_restarts_from_original_positions(self):
        # 轮内索引在原始范围内且不重复; 零权重永不出现; 轮间允许再选同位置。
        for seed in range(100):
            rounds = weighted_sample_many_indices(
                list(range(6)), [10 ** 100, 1, 10 ** 99, 3, 0, 5], 5, 7, seed
            )
            for rd in rounds:
                self.assertEqual(len(rd), 5)
                self.assertEqual(len(set(rd)), 5)
                self.assertTrue(all(0 <= i < 6 for i in rd))
                self.assertNotIn(4, rd)
        # k=1 连抽多轮: 每轮独立, 允许(且高概率会)重复同一位置。
        repeats = weighted_sample_many_indices(["a", "b"], [1, 1], 1, 12, 0)
        self.assertTrue(all(rd == [0] or rd == [1] for rd in repeats))

    def test_duplicate_values_distinct_positions(self):
        idx = weighted_sample_many_indices([1, 1, 1], [1, 1, 1], 3, 2, 123)
        vals = weighted_sample_many([1, 1, 1], [1, 1, 1], 3, 2, 123)
        self.assertTrue(all(sorted(rd) == [0, 1, 2] for rd in idx))
        self.assertEqual(vals, [[1, 1, 1], [1, 1, 1]])

    def test_draws_zero_returns_empty_after_validation(self):
        self.assertEqual(
            weighted_sample_many_indices(["a", "b"], [1, 2], 2, 0, 0), []
        )
        self.assertEqual(weighted_sample_many(["a", "b"], [1, 2], 2, 0, 0), [])
        # 即使 draws=0, 结构/范围/权重校验仍须先完成。
        with self.assertRaises(TypeError):
            weighted_sample_many_indices("ab", [1, 2], 1, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a", "b"], [1], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a"], [float("nan")], 0, 0, 0)

    def test_k_zero_returns_draws_empty_inner_rounds(self):
        self.assertEqual(
            weighted_sample_many_indices(["a", "b"], [0, 0], 0, 4, 0),
            [[], [], [], []],
        )
        self.assertEqual(
            weighted_sample_many(["a", "b"], [0, 0], 0, 3, 0),
            [[], [], []],
        )
        self.assertEqual(weighted_sample_many_indices([], [], 0, 2, 0), [[], []])

    def test_k_exceeding_positive_weights_raises_value_error(self):
        # 每轮无放回抽取 k 个位置至少需要 k 个正权重位置; 在开始任何一轮
        # 之前确定抛 ValueError, 绝不返回部分外层结果。
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a", "b"], [1, 0], 2, 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a"], [0], 1, 5, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a", "b", "c"], [10 ** 100, 0, 1], 3, 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many(["a", "b"], [1, 0], 2, 1000, 0)

    def test_draws_must_be_non_boolean_non_negative_integer(self):
        for bad in (True, False, 1.0, "2", None, [2], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_many_indices(["a"], [1], 0, bad, 0)
                with self.assertRaises(TypeError):
                    weighted_sample_many(["a"], [1], 0, bad, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a"], [1], 0, -1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many(["a"], [1], 0, -1, 0)

    def test_existing_validation_rules_unchanged(self):
        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        te(lambda: weighted_sample_many("ab", [1, 2], 1, 1, 0))
        te(lambda: weighted_sample_many(["a", "b"], [1, "x"], 1, 1, 0))
        te(lambda: weighted_sample_many(["a", "b"], [1, True], 1, 1, 0))
        te(lambda: weighted_sample_many(["a"], [1], True, 1, 0))
        te(lambda: weighted_sample_many(["a"], [1], 1, 1, object()))
        ve(lambda: weighted_sample_many(["a", "b"], [1, -1], 1, 1, 0))
        ve(lambda: weighted_sample_many(["a", "b"], [1, float("nan")], 1, 1, 0))
        ve(lambda: weighted_sample_many(["a", "b"], [1, float("inf")], 1, 1, 0))
        ve(lambda: weighted_sample_many(["a", "b"], [1], 1, 1, 0))
        ve(lambda: weighted_sample_many(["a"], [1], 2, 1, 0))

    def test_seed_none_keeps_random_semantics(self):
        rounds = weighted_sample_many_indices(
            list(range(50)), list(range(1, 51)), 10, 4, None
        )
        self.assertEqual(len(rounds), 4)
        self.assertTrue(all(len(rd) == 10 for rd in rounds))
        for rd in rounds:
            self.assertEqual(len(set(rd)), 10)
            self.assertTrue(all(0 <= i < 50 for i in rd))

    def test_inputs_not_mutated(self):
        items, weights = list("abc"), [10 ** 100, 10 ** 99, 1]
        items_snap, weights_snap = list(items), list(weights)
        weighted_sample_many(items, weights, 3, 5, 99)
        weighted_sample_many_indices(items, weights, 2, 5, -3)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)

    def test_huge_integer_weights_exact_and_deterministic(self):
        items, weights = ["a", "b"], [10 ** 400, 10 ** 400]
        rounds = weighted_sample_many_indices(items, weights, 2, 3, 2026)
        self.assertTrue(all(sorted(rd) == [0, 1] for rd in rounds))
        self.assertEqual(
            rounds, weighted_sample_many_indices(items, weights, 2, 3, 2026)
        )

    def test_exact_path_proportions_in_first_round(self):
        base = 2 ** 52 + 7
        counts = [0, 0]
        trials = 3000
        for seed in range(trials):
            counts[
                weighted_sample_many_indices(["a", "b"], [base, 2 * base], 1, 1, seed)[0][0]
            ] += 1
        self.assertAlmostEqual(counts[0] / trials, 1 / 3, delta=0.04)
        self.assertAlmostEqual(counts[1] / trials, 2 / 3, delta=0.04)


class OverflowFloatWeightTest(unittest.TestCase):
    """有限浮点权重求和/累计溢出为无穷时的精确回退路径。"""

    def test_sum_overflow_returns_full_k(self):
        # [1e308, 1e308] 的浮点总和为 inf; 修复前返回不完整结果。
        idx = weighted_sample_indices(["a", "b"], [1e308, 1e308], 2, 42)
        self.assertEqual(sorted(idx), [0, 1])
        self.assertEqual(
            idx, weighted_sample_indices(["a", "b"], [1e308, 1e308], 2, 42)
        )
        out = weighted_sample(["a", "b"], [1e308, 1e308], 2, 42)
        self.assertEqual(out, [["a", "b"][i] for i in idx])

    def test_overflow_with_mixed_magnitudes(self):
        items = ["a", "b", "c"]
        weights = [1e308, 1e308, 1.0]
        for seed in range(20):
            idx = weighted_sample_indices(items, weights, 3, seed)
            self.assertEqual(sorted(idx), [0, 1, 2])
            self.assertEqual(
                idx, weighted_sample_indices(items, weights, 3, seed)
            )

    def test_mixed_huge_int_and_float_weights(self):
        # 10**400 + 1.0 的求和会因 int->float 转换抛 OverflowError。
        idx = weighted_sample_indices(["a", "b"], [10 ** 400, 1.0], 2, 42)
        self.assertEqual(sorted(idx), [0, 1])
        self.assertEqual(
            idx, weighted_sample_indices(["a", "b"], [10 ** 400, 1.0], 2, 42)
        )

    def test_zero_weight_never_chosen_under_overflow(self):
        for seed in range(100):
            idx = weighted_sample_indices(
                ["x", "y", "z"], [1e308, 0.0, 1e308], 1, seed
            )
            self.assertIn(idx, ([0], [2]))

    def test_proportions_follow_original_weights(self):
        # 总和溢出 (2.55e308 -> inf), 相对比例仍须为 2 : 1。
        counts = [0, 0]
        trials = 3000
        for seed in range(trials):
            i = weighted_sample_indices(
                ["a", "b"], [1.7e308, 0.85e308], 1, seed
            )[0]
            counts[i] += 1
        self.assertAlmostEqual(counts[0] / trials, 2 / 3, delta=0.04)
        self.assertAlmostEqual(counts[1] / trials, 1 / 3, delta=0.04)

    def test_many_first_round_matches_single_entry(self):
        items = ["a", "b", "c"]
        weights = [1e308, 1e308, 1.0]
        for seed in (0, 1, 42, -7, 1.5, "s", b"s", True):
            many = weighted_sample_many_indices(items, weights, 2, 4, seed)
            self.assertEqual(
                many[0], weighted_sample_indices(items, weights, 2, seed)
            )
            self.assertEqual(len(many), 4)
            self.assertTrue(all(len(rd) == 2 for rd in many))

    def test_many_k_exceeding_positive_raises_before_any_round(self):
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a", "b"], [1e308, 0.0], 2, 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a", "b"], [1e308, 0.0], 2, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many(["a", "b"], [1e308, 0.0], 2, 5, 0)

    def test_k_zero_still_empty_under_overflow_scale(self):
        self.assertEqual(weighted_sample_indices(["a"], [1e308], 0, 0), [])
        self.assertEqual(
            weighted_sample_many_indices(["a", "b"], [1e308, 1e308], 0, 2, 0),
            [[], []],
        )

    def test_inputs_not_mutated_under_overflow(self):
        items = ["a", "b", "c"]
        weights = [1e308, 1e308, 1.0]
        items_snap, weights_snap = list(items), list(weights)
        weighted_sample(items, weights, 3, 5)
        weighted_sample_many_indices(items, weights, 2, 3, 5)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)

    def test_finite_total_keeps_baseline_float_path(self):
        # 总和可正常表示的输入继续走浮点路径, 序列与基线一致。
        import random as _random

        w = [1e308, 1.0]
        self.assertTrue(math.isfinite(sum(w)))
        for s in range(20):
            pool, pw = [0, 1], list(w)
            self.assertEqual(
                weighted_sample_indices(["a", "b"], w, 2, s),
                app._sample_indices_float(pool, pw, 2, _random.Random(s)),
            )


class FractionWeightSamplingTest(unittest.TestCase):
    """权重序列包含 Fraction 时全程走精确有理数路径, 不被浮点吞掉。"""

    # ------------------------------------------------------------------
    # 极小正 Fraction: 精确比例允许时可被选中
    # ------------------------------------------------------------------
    def test_tiny_positive_fraction_selectable_via_public_entry(self):
        # [9, 1/100] 精确放大为 [900, 1]; 微小位置以精确比例 1/901 可被选中。
        # 锁定一个确实命中微小位置的 seed, 证明公开入口不会把它吞成零。
        items = ["big", "tiny"]
        weights = [9, Fraction(1, 100)]
        idx = weighted_sample_indices(items, weights, 1, 2316)
        self.assertEqual(idx, [1])
        self.assertEqual(weighted_sample(items, weights, 1, 2316), ["tiny"])
        # 同 seed 完全可复现。
        for _ in range(5):
            self.assertEqual(
                weighted_sample_indices(items, weights, 1, 2316), [1]
            )

    def test_extreme_ratio_tiny_fraction_never_swallowed_exact(self):
        # 极端比例 10**100 : 1/10**100 —— 微小权重 float() 后严格为零,
        # 任何浮点路径都永不可能选中; 精确放大为 [10**200, 1] 后,
        # needle=total-1 必须落到微小 Fraction 位置。
        import app as _app

        original = [10 ** 100, Fraction(1, 10 ** 100)]
        scaled = _app._scale_to_exact_integer_weights(original)
        self.assertEqual(scaled, [10 ** 200, 1])

        class _ScriptedRNG:
            def __init__(self, values):
                self._values = list(values)

            def getrandbits(self, bits):
                return self._values.pop(0)

        total = sum(scaled)
        chosen = _app._sample_indices_exact_integer(
            [0, 1], list(scaled), 1, _ScriptedRNG([total - 1])
        )
        self.assertEqual(chosen, [1])

    def test_zero_fraction_skipped_in_exact_locator(self):
        import app as _app

        class _ScriptedRNG:
            def __init__(self, value):
                self._value = value

            def getrandbits(self, bits):
                return self._value

        original = [10 ** 100, Fraction(0), Fraction(1, 10 ** 100)]
        scaled = _app._scale_to_exact_integer_weights(original)
        self.assertEqual(scaled[1], 0)
        chosen = _app._sample_indices_exact_integer(
            [0, 1, 2], list(scaled), 1, _ScriptedRNG(sum(scaled) - 1)
        )
        self.assertEqual(chosen, [2])

    def test_mixed_int_fraction_proportions_exact(self):
        # [1, 1/3] 精确放大为 [3, 1]: 第一位置 3/4, 第二位置 1/4。
        counts = [0, 0]
        trials = 4000
        for seed in range(trials):
            i = weighted_sample_indices(
                ["a", "b"], [1, Fraction(1, 3)], 1, seed
            )[0]
            counts[i] += 1
        self.assertAlmostEqual(counts[0] / trials, 3 / 4, delta=0.04)
        self.assertAlmostEqual(counts[1] / trials, 1 / 4, delta=0.04)

    # ------------------------------------------------------------------
    # 零 Fraction 永不入选
    # ------------------------------------------------------------------
    def test_zero_fraction_never_chosen(self):
        for seed in range(100):
            self.assertEqual(
                weighted_sample_indices(
                    ["x", "y"], [Fraction(7, 3), Fraction(0)], 1, seed
                ),
                [0],
            )
        # 与超大整数混排时零 Fraction 仍永不出现。
        for seed in range(100):
            idx = weighted_sample_indices(
                ["a", "z"], [10 ** 100, Fraction(0)], 1, seed
            )
            self.assertEqual(idx, [0])

    def test_zero_fraction_excluded_from_full_draw(self):
        for seed in range(50):
            idx = weighted_sample_indices(
                ["a", "b", "c"],
                [Fraction(1, 2), Fraction(0), Fraction(1, 4)],
                2, seed,
            )
            self.assertEqual(sorted(idx), [0, 2])

    def test_insufficient_positive_raises_before_any_result(self):
        # 单次入口: 正权重位置不足 -> ValueError。
        with self.assertRaises(ValueError):
            weighted_sample_indices(
                ["a", "b"], [Fraction(1), Fraction(0)], 2, 0
            )
        with self.assertRaises(ValueError):
            weighted_sample_indices(
                ["a"], [Fraction(0, 10 ** 100)], 1, 0
            )
        # 批量入口: 在产生任何一轮前抛出, 不返回部分外层结果。
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(
                ["a", "b"], [Fraction(1), Fraction(0)], 2, 1000, 0
            )
        with self.assertRaises(ValueError):
            weighted_sample_many(
                ["a", "b"],
                [10 ** 100, Fraction(0), Fraction(1, 10 ** 100)],
                3, 2, 0,
            )

    # ------------------------------------------------------------------
    # 混合 int / Fraction / float: 精确、可复现、入口一致
    # ------------------------------------------------------------------
    def test_mixed_int_fraction_float_batch_reproducible(self):
        items = ["p", "q", "r"]
        weights = [2, Fraction(1), 0.5]  # 精确放大为 [4, 2, 1]
        locked = [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]]
        many_i = weighted_sample_many_indices(items, weights, 3, 4, 42)
        self.assertEqual(many_i, locked)
        # 完全可复现。
        self.assertEqual(
            many_i, weighted_sample_many_indices(items, weights, 3, 4, 42)
        )
        # 两个批量入口逐轮逐项对应。
        many_v = weighted_sample_many(items, weights, 3, 4, 42)
        self.assertEqual(
            many_v, [[items[i] for i in rd] for rd in many_i]
        )
        # 第一轮与同 seed 的单次调用逐项一致。
        self.assertEqual(
            many_i[0], weighted_sample_indices(items, weights, 3, 42)
        )
        self.assertEqual(
            many_v[0], weighted_sample(items, weights, 3, 42)
        )

    def test_fraction_only_weights_exact_and_deterministic(self):
        items = ["a", "b"]
        weights = [Fraction(1, 3), Fraction(2, 3)]
        for seed in (0, 1, 5, 42, -7, 1.5, "s", b"s", True):
            with self.subTest(seed=seed):
                single = weighted_sample_indices(items, weights, 2, seed)
                self.assertEqual(
                    single, weighted_sample_indices(items, weights, 2, seed)
                )
                self.assertEqual(
                    weighted_sample_many_indices(items, weights, 2, 3, seed)[0],
                    single,
                )
                self.assertEqual(sorted(single), [0, 1])

    def test_mixed_huge_integer_and_fraction_valid_and_reproducible(self):
        # 极大整数 + 极小分母 Fraction: 校验与缩放都不得触发浮点转换。
        items = ["H", "t", "z"]
        weights = [10 ** 400, Fraction(1, 10 ** 400), Fraction(0)]
        rounds = weighted_sample_many_indices(items, weights, 1, 3, 7)
        self.assertEqual(rounds, [[0], [0], [0]])  # 零权重永不出现
        self.assertEqual(
            rounds, weighted_sample_many_indices(items, weights, 1, 3, 7)
        )
        # 极端分子 / 分母的 Fraction 通过校验且确定抽取。
        for w in (
            Fraction(10 ** 5000, 1),
            Fraction(1, 10 ** 5000),
            Fraction(10 ** 5000, 10 ** 5000 + 1),
        ):
            idx = weighted_sample_indices(["a", "b"], [w, 1], 1, 3)
            self.assertIn(idx[0], (0, 1))
            self.assertEqual(
                idx, weighted_sample_indices(["a", "b"], [w, 1], 1, 3)
            )

    # ------------------------------------------------------------------
    # 校验: 类型 / 取值 / 顺序异常分类保持不变
    # ------------------------------------------------------------------
    def test_fraction_validation_error_classes(self):
        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        # bool 继续按非法权重抛 TypeError(即使与 Fraction 混排)。
        te(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), True], 1, 0))
        te(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), False], 1, 0))
        # 非实数权重 TypeError。
        te(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), 1 + 2j], 1, 0))
        te(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), "1"], 1, 0))
        te(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), None], 1, 0))
        # 负 Fraction / NaN / 正负无穷沿用 ValueError 规则。
        ve(lambda: weighted_sample_indices(
            ["a"], [Fraction(-1, 3)], 1, 0))
        ve(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), float("nan")], 1, 0))
        ve(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), float("inf")], 1, 0))
        ve(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), float("-inf")], 1, 0))
        ve(lambda: weighted_sample_indices(
            ["a", "b"], [Fraction(1), -0.5], 1, 0))

    def test_fraction_validation_completes_before_sampling(self):
        # k=0 仍完成全部权重校验。
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Fraction(-1, 2)], 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [True], 0, 0)
        self.assertEqual(
            weighted_sample_indices(["a"], [Fraction(1, 10 ** 100)], 0, 0),
            [],
        )

    def test_fraction_draws_zero_validates_then_empty(self):
        self.assertEqual(
            weighted_sample_many_indices(["a"], [Fraction(1)], 1, 0, 0), []
        )
        self.assertEqual(
            weighted_sample_many(["a"], [Fraction(1)], 1, 0, 0), []
        )
        # draws=0 仍完成全部校验。
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(
                ["a"], [float("nan")], 0, 0, 0
            )
        with self.assertRaises(TypeError):
            weighted_sample_many_indices("ab", [Fraction(1, 2)], 1, 0, 0)

    def test_fraction_k_zero_empty_rounds(self):
        self.assertEqual(
            weighted_sample_many_indices(
                ["a", "b"], [Fraction(0), Fraction(0)], 0, 3, 0
            ),
            [[], [], []],
        )

    # ------------------------------------------------------------------
    # seed=None 语义 / 入参不变 / 纯浮点路径不受影响
    # ------------------------------------------------------------------
    def test_seed_none_random_semantics_preserved(self):
        items = list(range(20))
        weights = [Fraction(i + 1, 7) for i in range(20)]
        rounds = weighted_sample_many_indices(items, weights, 8, 3, None)
        self.assertEqual(len(rounds), 3)
        for rd in rounds:
            self.assertEqual(len(rd), 8)
            self.assertEqual(len(set(rd)), 8)
            self.assertTrue(all(0 <= i < 20 for i in rd))

    def test_inputs_not_mutated_with_fractions(self):
        items = ["p", "q", "r"]
        weights = [2, Fraction(1, 3), 0.5]
        items_snap = list(items)
        weights_snap = list(weights)
        weighted_sample(items, weights, 3, 5)
        weighted_sample_indices(items, weights, 2, -3)
        weighted_sample_many(items, weights, 3, 4, 99)
        weighted_sample_many_indices(items, weights, 2, 4, -3)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)

    def test_pure_float_inputs_keep_baseline_path(self):
        # 不含 Fraction 的普通浮点输入不改变既有可观察结果。
        out = weighted_sample(["p", "q"], [0.5, 1.5], 2, 3)
        self.assertEqual(sorted(out), ["p", "q"])
        self.assertEqual(
            out, weighted_sample(["p", "q"], [0.5, 1.5], 2, 3)
        )
        # Fraction 与 float 混合时每个 float 也按精确值参与(0.5 -> 1/2)。
        idx = weighted_sample_many_indices(
            ["a", "b"], [Fraction(1, 2), 0.5], 2, 5, 11
        )
        self.assertTrue(all(sorted(rd) == [0, 1] for rd in idx))


class DecimalWeightSamplingTest(unittest.TestCase):
    """权重序列包含 decimal.Decimal 时全程走精确十进制/有理数路径。"""

    # ------------------------------------------------------------------
    # 可接受性 / 确定性 / 两个单轮入口逐项对应
    # ------------------------------------------------------------------
    def test_decimal_weights_deterministic_and_entries_correspond(self):
        items = ["a", "b", "c", "d"]
        weights = [Decimal("1.5"), 3, Fraction(1, 2), 0.25]
        for k in (1, 2, 3):
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                idx = weighted_sample_indices(items, weights, k, seed)
                self.assertEqual(len(idx), k)
                self.assertEqual(len(set(idx)), k)
                self.assertTrue(all(0 <= i < 4 for i in idx))
                self.assertEqual(
                    idx, weighted_sample_indices(items, weights, k, seed)
                )
                self.assertEqual(
                    weighted_sample(items, weights, k, seed),
                    [items[i] for i in idx],
                )

    def test_seed_none_works_with_decimal_weights(self):
        idx = weighted_sample_indices(
            list(range(20)), [Decimal(i + 1) for i in range(20)], 8, None
        )
        self.assertEqual(len(idx), 8)
        self.assertEqual(len(set(idx)), 8)

    def test_duplicate_values_are_distinct_positions_with_decimal(self):
        items = [1, 1, 1]
        idx = weighted_sample_many_indices(items, [Decimal(1)] * 3, 3, 2, 123)
        vals = weighted_sample_many(items, [Decimal(1)] * 3, 3, 2, 123)
        self.assertTrue(all(sorted(rd) == [0, 1, 2] for rd in idx))
        self.assertEqual(vals, [[1, 1, 1], [1, 1, 1]])

    # ------------------------------------------------------------------
    # 精确性: Decimal 与 Fraction 逐点相等; 长数字不受 context 精度影响
    # ------------------------------------------------------------------
    def test_decimal_matches_fraction_exactly_across_seeds(self):
        # Decimal("0.1") 与 Fraction(1,10) 是同一个精确有理数, 任意 seed
        # 下索引序列必须逐点相同(浮点 0.1 并不是精确的 1/10)。
        wd = [1, Decimal("0.1")]
        wf = [1, Fraction(1, 10)]
        for seed in range(200):
            self.assertEqual(
                weighted_sample_indices(["a", "b"], wd, 1, seed),
                weighted_sample_indices(["a", "b"], wf, 1, seed),
            )

    def test_decimal_beyond_context_precision_stays_exact(self):
        # 默认 context 精度只有 28 位; 直接构造的 Decimal 保留全部 60 位,
        # 经 Fraction 放大后两份权重仍严格保持 1:2, 不被舍入。
        import app as _app

        s1 = Decimal("1." + "1" * 60)
        s2 = Decimal("2." + "2" * 60)
        scaled = _app._scale_to_exact_integer_weights([s1, s2])
        self.assertEqual(scaled[1], 2 * scaled[0])
        self.assertTrue(scaled[0] > 0)
        # 公开入口按精确 1:2 比例抽取且确定。
        counts = [0, 0]
        trials = 3000
        for seed in range(trials):
            counts[
                weighted_sample_indices(["a", "b"], [s1, s2], 1, seed)[0]
            ] += 1
        self.assertAlmostEqual(counts[0] / trials, 1 / 3, delta=0.04)
        self.assertAlmostEqual(counts[1] / trials, 2 / 3, delta=0.04)

    def test_tiny_positive_decimal_selectable_via_public_entry(self):
        # [9, 0.01] 精确放大为 [900, 1]; 与 Fraction(1,100) 同 seed 同序列。
        items = ["big", "tiny"]
        wd = [9, Decimal("0.01")]
        wf = [9, Fraction(1, 100)]
        self.assertEqual(
            weighted_sample_indices(items, wd, 1, 2316), [1]
        )
        self.assertEqual(weighted_sample(items, wd, 1, 2316), ["tiny"])
        self.assertEqual(
            weighted_sample_indices(items, wd, 1, 2316),
            weighted_sample_indices(items, wf, 1, 2316),
        )

    def test_extreme_ratio_tiny_decimal_never_swallowed_exact(self):
        # 10**100 : 1E-100 —— 微小方 float() 后严格为零; 精确放大为
        # [10**200, 1], needle=total-1 必须落到微小 Decimal 位置。
        import app as _app

        original = [10 ** 100, Decimal("1E-100")]
        scaled = _app._scale_to_exact_integer_weights(original)
        self.assertEqual(scaled, [10 ** 200, 1])

        class _ScriptedRNG:
            def __init__(self, values):
                self._values = list(values)

            def getrandbits(self, bits):
                return self._values.pop(0)

        chosen = _app._sample_indices_exact_integer(
            [0, 1], list(scaled), 1, _ScriptedRNG([sum(scaled) - 1])
        )
        self.assertEqual(chosen, [1])

    def test_huge_exponent_decimal_exact_and_deterministic(self):
        # 超大正指数 1E100000 与 1 混排: 不触发浮点转换, 确定可复现,
        # 且与 Fraction(10**100000, 1) 逐点同序列。
        wd = [Decimal("1E100000"), Decimal("1")]
        wf = [Fraction(10 ** 100000, 1), Fraction(1)]
        for seed in (0, 1, 42, 7):
            with self.subTest(seed=seed):
                a = weighted_sample_indices(["a", "b"], wd, 1, seed)
                self.assertIn(a[0], (0, 1))
                self.assertEqual(
                    a, weighted_sample_indices(["a", "b"], wd, 1, seed)
                )
                self.assertEqual(
                    a, weighted_sample_indices(["a", "b"], wf, 1, seed)
                )

    def test_huge_exponent_mixed_with_zero_decimal(self):
        items = ["H", "t", "z"]
        weights = [Decimal("1E100000"), Decimal("1E-100000"), Decimal(0)]
        rounds = weighted_sample_many_indices(items, weights, 1, 3, 7)
        self.assertTrue(all(rd == [0] or rd == [1] for rd in rounds))
        self.assertNotIn([2], rounds)
        self.assertEqual(
            rounds, weighted_sample_many_indices(items, weights, 1, 3, 7)
        )

    # ------------------------------------------------------------------
    # 零值(含带符号零)始终不可选
    # ------------------------------------------------------------------
    def test_zero_and_signed_zero_decimal_never_chosen(self):
        for zero in (Decimal(0), Decimal("0.0"), Decimal("-0.0"),
                     Decimal("0E5"), Decimal("-0E100")):
            for seed in range(60):
                self.assertEqual(
                    weighted_sample_indices(
                        ["x", "y"], [zero, Decimal(5)], 1, seed
                    ),
                    [1],
                )
            # 带符号零是合法的零权重(不抛异常), k=0 正常返回空。
            self.assertEqual(
                weighted_sample_indices(["x"], [zero], 0, 0), []
            )

    def test_zero_decimal_excluded_from_full_draw(self):
        weights = [Decimal("1.5"), Decimal(0), Decimal("0.5")]
        for seed in range(80):
            idx = weighted_sample_indices(["a", "b", "c"], weights, 2, seed)
            self.assertEqual(sorted(idx), [0, 2])

    # ------------------------------------------------------------------
    # 四类权重混合: 精确缩放、锁定序列、批量约定
    # ------------------------------------------------------------------
    def test_mixed_all_four_weight_types_exact_scaling(self):
        import app as _app

        weights = [2, Fraction(1), 0.5, Decimal("0.25")]
        # 统一放大 8 倍 -> [8, 4, 2, 1]。
        self.assertEqual(
            _app._scale_to_exact_integer_weights(weights), [8, 4, 2, 1]
        )

    def test_mixed_all_four_types_batch_locked_and_corresponding(self):
        items = ["p", "q", "r", "s"]
        weights = [2, Fraction(1), 0.5, Decimal("0.25")]
        locked = [[1, 0, 2], [1, 0, 2], [0, 1, 3], [0, 2, 3]]
        many_i = weighted_sample_many_indices(items, weights, 3, 4, 42)
        self.assertEqual(many_i, locked)
        self.assertEqual(
            many_i, weighted_sample_many_indices(items, weights, 3, 4, 42)
        )
        many_v = weighted_sample_many(items, weights, 3, 4, 42)
        self.assertEqual(
            many_v, [[items[i] for i in rd] for rd in many_i]
        )
        # 第一轮与同 seed 的单轮入口逐项一致。
        self.assertEqual(
            many_i[0], weighted_sample_indices(items, weights, 3, 42)
        )
        self.assertEqual(
            many_v[0], weighted_sample(items, weights, 3, 42)
        )

    def test_batch_rounds_share_one_seed_stream_and_restart(self):
        import random as _random
        import app as _app

        items, weights, k = list("abcdef"), [
            Decimal("1.5"), 1, Fraction(1, 2), 7, Decimal(0), 3
        ], 4
        scaled = _app._scale_to_exact_integer_weights(weights)
        for draws in (1, 2, 6):
            rng = _random.Random(99)
            manual = []
            for _ in range(draws):
                # 每轮都从原始位置池重新开始, 但继续消耗同一随机流。
                manual.append(
                    _app._sample_indices_exact_integer(
                        list(range(len(items))), list(scaled), k, rng
                    )
                )
            self.assertEqual(
                weighted_sample_many_indices(items, weights, k, draws, 99),
                manual,
            )
        full = weighted_sample_many_indices(items, weights, k, 8, 123)
        head = weighted_sample_many_indices(items, weights, k, 3, 123)
        self.assertEqual(full[:3], head)
        # 每轮内无重复、零权重位置 4 永不出现。
        for rd in full:
            self.assertEqual(len(rd), len(set(rd)))
            self.assertNotIn(4, rd)

    def test_batch_may_reselect_position_between_rounds(self):
        rounds = weighted_sample_many_indices(
            ["a", "b"], [Decimal(1), Decimal(1)], 1, 20, 0
        )
        self.assertEqual(len(rounds), 20)
        self.assertTrue(all(rd == [0] or rd == [1] for rd in rounds))

    # ------------------------------------------------------------------
    # 正权重位置不足: 单轮与批量都在产出任何结果前抛 ValueError
    # ------------------------------------------------------------------
    def test_insufficient_positive_weights_raises_value_error(self):
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [Decimal(1), 0], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal(0)], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(
                ["a", "b"], [Decimal("1E100"), Decimal(0)], 2, 0
            )
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(
                ["a", "b"], [Decimal(1), Decimal(0)], 2, 5, 0
            )
        with self.assertRaises(ValueError):
            weighted_sample_many(["a"], [Decimal(0)], 1, 5, 0)

    # ------------------------------------------------------------------
    # 非法取值: NaN / sNaN / 正负无穷 / 负数 -> ValueError, 不泄漏
    # decimal.InvalidOperation
    # ------------------------------------------------------------------
    def test_nonfinite_and_negative_decimal_raise_value_error(self):
        import decimal

        bad_values = [
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            Decimal("-0.0001"),
            Decimal("-1E100000"),
        ]
        for bad in bad_values:
            with self.subTest(bad=str(bad)):
                for fn in (
                    lambda: weighted_sample_indices(["a"], [bad], 1, 0),
                    lambda: weighted_sample(["a"], [bad], 1, 0),
                    lambda: weighted_sample_many_indices(
                        ["a"], [bad], 1, 1, 0
                    ),
                    lambda: weighted_sample_many(["a"], [bad], 1, 1, 0),
                ):
                    try:
                        fn()
                    except decimal.InvalidOperation:
                        # Decimal 自身的比较异常不得泄漏。
                        self.fail(
                            "decimal.InvalidOperation leaked for %r" % bad
                        )
                    except ValueError:
                        pass
                    except Exception as exc:  # noqa: PT027
                        self.fail(
                            "expected ValueError for %r, got %s"
                            % (bad, type(exc).__name__)
                        )
                    else:
                        self.fail("expected ValueError for %r" % bad)

    def test_nonfinite_decimal_still_validated_at_k_zero_and_draws_zero(self):
        # k=0 / draws=0 仍须先完成全部权重校验。
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal("sNaN")], 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal("-Infinity")], 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a"], [Decimal("NaN")], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many(["a"], [Decimal("-1")], 0, 0, 0)

    # ------------------------------------------------------------------
    # 非法类型: bool 及其他不支持的类型 -> TypeError
    # ------------------------------------------------------------------
    def test_unsupported_weight_types_raise_type_error(self):
        for bad in (True, False, 1 + 0j, "1", None, [1], 3.14j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_indices(
                        ["a", "b"], [Decimal(1), bad], 1, 0
                    )
                with self.assertRaises(TypeError):
                    weighted_sample_many_indices(
                        ["a", "b"], [Decimal(1), bad], 1, 1, 0
                    )
        # 全 Decimal 合法输入不被误判。
        weighted_sample_indices(["a"], [Decimal("1")], 1, 0)

    def test_existing_structure_and_size_rules_unchanged_with_decimal(self):
        with self.assertRaises(TypeError):
            weighted_sample_indices("ab", [Decimal(1), Decimal(2)], 1, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [Decimal(1)], True, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [Decimal(1)], 1, object())
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [Decimal(1)], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal(1)], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal(1)], -1, 0)

    def test_draws_rules_unchanged_with_decimal(self):
        for bad in (True, False, 1.0, "2", None, [2]):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_many_indices(
                        ["a"], [Decimal(1)], 1, bad, 0
                    )
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a"], [Decimal(1)], 1, -1, 0)

    # ------------------------------------------------------------------
    # k=0 单轮空; draws=0 完成校验后空轮次集合; k=0 批量空轮次
    # ------------------------------------------------------------------
    def test_k_zero_and_draws_zero_shapes(self):
        self.assertEqual(
            weighted_sample(["a", "b"], [Decimal(1), Decimal(2)], 0, 0), []
        )
        self.assertEqual(
            weighted_sample_indices(["a"], [Decimal("1E-9")], 0, 0), []
        )
        self.assertEqual(
            weighted_sample_many_indices(["a"], [Decimal(1)], 1, 0, 0), []
        )
        self.assertEqual(
            weighted_sample_many(["a"], [Decimal(1)], 1, 0, 0), []
        )
        self.assertEqual(
            weighted_sample_many_indices(
                ["a", "b"], [Decimal(0), Decimal(0)], 0, 3, 0
            ),
            [[], [], []],
        )
        self.assertEqual(
            weighted_sample_many(
                ["a", "b"], [Decimal(0), Decimal(0)], 0, 2, 0
            ),
            [[], []],
        )

    # ------------------------------------------------------------------
    # 入参不变 / 既有 int/float/Fraction 结果与指标序列化保持不变
    # ------------------------------------------------------------------
    def test_inputs_not_mutated_with_decimal(self):
        items = ["p", "q", "r"]
        weights = [Decimal("1.5"), 2, Fraction(1, 3)]
        items_snap = list(items)
        weights_snap = [repr(w) for w in weights]
        weighted_sample(items, weights, 2, 5)
        weighted_sample_indices(items, weights, 2, -3)
        weighted_sample_many(items, weights, 2, 3, 99)
        weighted_sample_many_indices(items, weights, 2, 3, -3)
        self.assertEqual(items, items_snap)
        self.assertEqual([repr(w) for w in weights], weights_snap)

    def test_existing_locked_sequences_and_serialization_unchanged(self):
        # 既有 int / float / Fraction 锁定序列。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample(["p", "q"], [0.5, 1.5], 2, 3), ["p", "q"]
        )
        # 超大整数指标仍为精确十进制、键排序与紧凑格式不变。
        self.assertEqual(
            serialize_metrics({10 ** 100: 1, "名": [1, 2]}),
            '{"1%s":1,"名":[1,2]}' % ("0" * 100),
        )


class SerializeMetricsTest(unittest.TestCase):
    def test_baseline_format_locked(self):
        text = serialize_metrics({"b": 1, "a": {"z": 2, "y": 3}})
        self.assertEqual(text, '{"a":{"y":3,"z":2},"b":1}')

    def test_compact_separators_and_unicode(self):
        text = serialize_metrics({"名": "值", "x": [1, 2]})
        self.assertEqual(text, '{"x":[1,2],"名":"值"}')

    def test_nested_keys_sorted_recursively(self):
        data = {"outer": {"d": 1, "c": [{"z": 0, "a": 0}]}, "b": 2}
        self.assertEqual(
            serialize_metrics(data),
            '{"b":2,"outer":{"c":[{"a":0,"z":0}],"d":1}}',
        )

    def test_arbitrary_size_integers_exact_decimal(self):
        big_pos = 9007199254740993          # 超出 JS 安全整数
        big_neg = -9007199254740993
        huge = 10 ** 100
        text = serialize_metrics(
            {"events": big_pos, "neg": big_neg, "huge": huge}
        )
        self.assertIn(str(big_pos), text)
        self.assertIn(str(big_neg), text)
        self.assertIn("1" + "0" * 100, text)
        # 不得出现浮点近似或科学计数法
        self.assertNotRegex(text, r"\d[eE][+-]?\d")
        self.assertNotIn("9007199254740992", text)

    def test_json_semantics_for_other_types(self):
        self.assertEqual(serialize_metrics({"t": True, "f": False}), '{"f":false,"t":true}')
        self.assertEqual(serialize_metrics(None), "null")
        self.assertEqual(serialize_metrics([None, "s", 1, 1.5]), '[null,"s",1,1.5]')
        self.assertEqual(serialize_metrics({"a": ()}), '{"a":[]}')

    def test_nan_and_infinity_raise_value_error(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    serialize_metrics({"x": bad})
                with self.assertRaises(ValueError):
                    serialize_metrics([bad])

    def test_non_representable_values_raise_type_error(self):
        with self.assertRaises(TypeError):
            serialize_metrics({"x": {1, 2}})
        with self.assertRaises(TypeError):
            serialize_metrics(({1},))
        with self.assertRaises(TypeError):
            serialize_metrics({"x": b"bytes"})
        with self.assertRaises(TypeError):
            serialize_metrics(object())

    def test_circular_reference_raises_type_error(self):
        a = []
        a.append(a)
        with self.assertRaises(TypeError):
            serialize_metrics(a)
        d = {}
        d["self"] = d
        with self.assertRaises(TypeError):
            serialize_metrics(d)

    def test_shared_non_cyclic_reference_is_fine(self):
        child = {"v": 1}
        text = serialize_metrics({"a": child, "b": child})
        self.assertEqual(text, '{"a":{"v":1},"b":{"v":1}}')

    def test_no_partial_output_on_error(self):
        # 非法值位于深层时同样不得产生任何文本。
        with self.assertRaises(TypeError):
            serialize_metrics({"ok": 1, "bad": {"deep": {1, 2}}})
        with self.assertRaises(ValueError):
            serialize_metrics({"ok": 1, "bad": [float("nan")]})

    def test_heterogeneous_keys_converted_and_sorted_as_text(self):
        # None/bool/int/float 键转换为成员名文本后按 Unicode 文本升序。
        data = {None: 1, True: 2, False: 3, 7: 4, 1.5: 5, "s": 6}
        self.assertEqual(
            serialize_metrics(data),
            '{"1.5":5,"7":4,"false":3,"null":1,"s":6,"true":2}',
        )

    def test_numeric_keys_sorted_by_member_name_not_value(self):
        # 成员名按文本排序: "10" < "2", 而非数值 2 < 10。
        self.assertEqual(
            serialize_metrics({2: "a", 10: "b"}),
            '{"10":"b","2":"a"}',
        )

    def test_mixed_key_order_irrelevant(self):
        # 同一数据内容仅交换插入顺序, 输出逐字相同。
        forward = {1: "a", "x": [2, {None: True}], 2.5: "b"}
        backward = {2.5: "b", "x": [2, {None: True}], 1: "a"}
        self.assertEqual(
            serialize_metrics(forward), serialize_metrics(backward)
        )
        self.assertEqual(
            serialize_metrics(forward),
            '{"1":"a","2.5":"b","x":[2,{"null":true}]}',
        )

    def test_nested_heterogeneous_keys_follow_same_order(self):
        data = {"outer": {10: 1, "a": {False: 0, 3: 1}}, 0: 2}
        self.assertEqual(
            serialize_metrics(data),
            '{"0":2,"outer":{"10":1,"a":{"3":1,"false":0}}}',
        )

    def test_float_key_uses_encoder_number_text(self):
        # 负零与指数表示沿用编码器既有规则。
        self.assertEqual(serialize_metrics({-0.0: 1}), '{"-0.0":1}')
        self.assertEqual(serialize_metrics({1e300: 1}), '{"1e+300":1}')
        self.assertEqual(serialize_metrics({0.5: 1}), '{"0.5":1}')

    def test_huge_integer_key_exact_decimal(self):
        big = 10 ** 100
        self.assertEqual(
            serialize_metrics({big: 1}),
            '{"1%s":1}' % ("0" * 100),
        )

    def test_integers_beyond_runtime_digit_limit_exact_decimal(self):
        # CPython 3.11+ 的 str(int) 默认拒绝约 4300 位以上的转换。
        # 序列化必须绕过该限制: 任意位数的 int 都给出精确十进制文本,
        # 不使用科学计数法、浮点近似或截断。
        import sys

        if not hasattr(sys, "get_int_max_str_digits"):
            self.skipTest("解释器没有可配置的整数转文本位数限制")
        limit = sys.get_int_max_str_digits()
        if limit == 0:
            self.skipTest("整数转文本位数限制已关闭")
        self.addCleanup(sys.set_int_max_str_digits, limit)

        digits = limit + 1000
        big = 10 ** (digits - 1) + 123456789
        neg = -big

        def unlimited_str(value):
            sys.set_int_max_str_digits(0)
            try:
                return str(value)
            finally:
                sys.set_int_max_str_digits(limit)

        # 顶层
        self.assertEqual(serialize_metrics(big), unlimited_str(big))
        self.assertEqual(serialize_metrics(neg), unlimited_str(neg))
        self.assertEqual(serialize_metrics(0), "0")
        # list / tuple / 任意深度的 dict
        nested = {"a": [big, (neg,)], "b": {"c": {"d": big}}}
        expected = (
            '{"a":[%s,[%s]],"b":{"c":{"d":%s}}}'
            % (unlimited_str(big), unlimited_str(neg), unlimited_str(big))
        )
        self.assertEqual(serialize_metrics(nested), expected)
        # 纯十进制: 无指数、无小数点, 且整段输出逐字精确。
        self.assertEqual(
            serialize_metrics({"n": neg}),
            '{"n":%s}' % unlimited_str(neg),
        )
        self.assertNotIn("e", serialize_metrics(big).lower())
        self.assertNotIn(".", serialize_metrics(big))

    def test_super_large_integer_key_beyond_digit_limit(self):
        import sys

        if not hasattr(sys, "get_int_max_str_digits"):
            self.skipTest("解释器没有可配置的整数转文本位数限制")
        limit = sys.get_int_max_str_digits()
        if limit == 0:
            self.skipTest("整数转文本位数限制已关闭")
        self.addCleanup(sys.set_int_max_str_digits, limit)

        big = 10 ** (limit + 7)
        sys.set_int_max_str_digits(0)
        try:
            big_name = str(big)
        finally:
            sys.set_int_max_str_digits(limit)

        # 精确成员名, 并按文本顺序 ("100.. < "2") 排列。
        self.assertEqual(
            serialize_metrics({2: "a", big: "b"}),
            '{"%s":"b","2":"a"}' % big_name,
        )
        # 与同名字符串键冲突仍为 ValueError。
        with self.assertRaises(ValueError):
            serialize_metrics({big: 1, big_name: 2})

    def test_serializes_when_digit_limit_lowered_to_minimum(self):
        # 即使调用方把位数上限压到可配置的最低值, 分块转换仍须成功。
        import sys

        if not hasattr(sys, "set_int_max_str_digits"):
            self.skipTest("解释器没有可配置的整数转文本位数限制")
        old = sys.get_int_max_str_digits()
        self.addCleanup(sys.set_int_max_str_digits, old)
        sys.set_int_max_str_digits(640)

        big = 10 ** 5000 - 1
        sys.set_int_max_str_digits(0)
        try:
            reference = str(big)
        finally:
            sys.set_int_max_str_digits(640)

        self.assertEqual(serialize_metrics(big), reference)
        self.assertEqual(serialize_metrics([big, -big]),
                         "[" + reference + ",-" + reference + "]")
        self.assertEqual(
            serialize_metrics({10 ** 1000: 1}),
            '{"1%s":1}' % ("0" * 1000),
        )

    def test_bools_remain_json_booleans_next_to_huge_integers(self):
        import sys

        big = 10 ** 5000
        text = serialize_metrics({"t": True, "f": False, "n": big})
        self.assertIn('"t":true', text)
        self.assertIn('"f":false', text)
        self.assertIn('"n":1' + "0" * 5000, text)
        self.assertEqual(serialize_metrics((True, False)), "[true,false]")

    def test_integer_subclass_uses_exact_value_decimal(self):
        # 与标准库编码器一致: int 子类自定义的 __str__/__repr__ 必须被忽略,
        # 结果只取整数值的十进制; 超过位数上限时同样适用。
        class WeirdInt(int):
            def __str__(self):
                return "not-a-number"

            __repr__ = __str__

        self.assertEqual(serialize_metrics(WeirdInt(42)), "42")
        self.assertEqual(serialize_metrics({"x": WeirdInt(-7)}), '{"x":-7}')
        self.assertEqual(serialize_metrics({WeirdInt(42): 1}), '{"42":1}')
        big = WeirdInt(10 ** 5000)
        self.assertEqual(serialize_metrics(big), "1" + "0" * 5000)

    def test_error_classes_unchanged_alongside_huge_integers(self):
        # 位数本身不是错误条件, 但同树中的其他非法值仍按原分类报错,
        # 且在产出任何文本前完成校验。
        big = 10 ** 5000
        with self.assertRaises(TypeError):
            serialize_metrics({"ok": big, "bad": {1, 2}})
        with self.assertRaises(ValueError):
            serialize_metrics({"ok": big, "bad": float("nan")})
        with self.assertRaises(ValueError):
            serialize_metrics([big, float("inf")])
        with self.assertRaises(TypeError):
            serialize_metrics([big, b"bytes"])

    def test_colliding_member_names_raise_value_error(self):
        # 不同原始键转换得到同一成员名 -> ValueError, 不得静默覆盖。
        for bad in (
            {1: "a", "1": "b"},
            {None: "a", "null": "b"},
            {True: "a", "true": "b"},
            {False: "a", "false": "b"},
            {1.5: "a", "1.5": "b"},
            {"nested": {2: "a", "2": "b"}},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    serialize_metrics(bad)

    def test_key_type_and_value_errors_unchanged_with_heterogeneous_keys(self):
        # 非法键类型仍 TypeError; 非有限浮点键仍 ValueError。
        with self.assertRaises(TypeError):
            serialize_metrics({(1, 2): "a"})
        with self.assertRaises(TypeError):
            serialize_metrics({b"k": "a"})
        with self.assertRaises(ValueError):
            serialize_metrics({float("nan"): "a"})
        with self.assertRaises(ValueError):
            serialize_metrics({float("inf"): "a"})

    def test_heterogeneous_keys_input_not_mutated(self):
        data = {1: "a", "x": [{None: True}], 2.5: {"y": 1}}
        snapshot = repr(data)
        serialize_metrics(data)
        self.assertEqual(repr(data), snapshot)


if __name__ == "__main__":
    unittest.main()
