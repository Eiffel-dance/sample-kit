import json
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
    weighted_sample_stream,
    weighted_sample_stream_indices,
    weighted_sample_checkpoint,
    weighted_sample_resume_indices,
    weighted_sample_resume,
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


class WeightedSampleStreamTest(unittest.TestCase):
    """按需逐轮入口 weighted_sample_stream / weighted_sample_stream_indices。"""

    def test_stream_matches_many_round_by_round(self):
        # 相同输入和种子下, 逐轮结果必须与批量入口完全一致。
        cases = [
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
            (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
            (["p", "q"], [0.5, 1.5], 2),
            ([], [], 0),
            (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
            (["p", "q", "r"], [2, Fraction(1), 0.5], 3),
            (["a", "b", "c"], [Decimal("1.5"), Decimal("0.5"), Decimal("2")], 3),
        ]
        for items, weights, k in cases:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                with self.subTest(items=items, k=k, seed=seed):
                    self.assertEqual(
                        list(weighted_sample_stream_indices(
                            items, weights, k, 4, seed)),
                        weighted_sample_many_indices(items, weights, k, 4, seed),
                    )
                    self.assertEqual(
                        list(weighted_sample_stream(items, weights, k, 4, seed)),
                        weighted_sample_many(items, weights, k, 4, seed),
                    )

    def test_first_round_matches_single_entry(self):
        cases = [
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
            (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
            (["p", "q"], [0.5, 1.5], 2),
            (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
        ]
        for items, weights, k in cases:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", True):
                with self.subTest(items=items, k=k, seed=seed):
                    stream_i = weighted_sample_stream_indices(
                        items, weights, k, 3, seed)
                    self.assertEqual(
                        next(iter(stream_i)),
                        weighted_sample_indices(items, weights, k, seed),
                    )
                    stream_v = weighted_sample_stream(
                        items, weights, k, 3, seed)
                    self.assertEqual(
                        next(iter(stream_v)),
                        weighted_sample(items, weights, k, seed),
                    )

    def test_returns_iterable_consumed_on_demand(self):
        # 返回可迭代对象而非已物化的外层序列; 逐轮消费, 前缀与批量一致。
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        stream = weighted_sample_stream_indices(items, weights, k, 100, 7)
        self.assertFalse(isinstance(stream, list))
        iterator = iter(stream)
        full = weighted_sample_many_indices(items, weights, k, 100, 7)
        for expected in full[:5]:
            self.assertEqual(next(iterator), expected)
        # 继续消费仍与批量逐轮一致。
        for expected in full[5:10]:
            self.assertEqual(next(iterator), expected)

    def test_values_and_indices_streams_correspond(self):
        items, weights = list("abcdef"), [1, 3, 2, 5, 0, 2]
        idx = list(weighted_sample_stream_indices(items, weights, 4, 5, 7))
        vals = list(weighted_sample_stream(items, weights, 4, 5, 7))
        self.assertEqual(vals, [[items[i] for i in rd] for rd in idx])

    def test_each_round_restarts_from_original_positions(self):
        for seed in range(50):
            for rd in weighted_sample_stream_indices(
                list(range(6)), [10 ** 100, 1, 10 ** 99, 3, 0, 5], 5, 7, seed
            ):
                self.assertEqual(len(rd), 5)
                self.assertEqual(len(set(rd)), 5)
                self.assertTrue(all(0 <= i < 6 for i in rd))
                self.assertNotIn(4, rd)  # 零权重位置永不出现

    def test_duplicate_values_distinct_positions(self):
        idx = list(weighted_sample_stream_indices([1, 1, 1], [1, 1, 1], 3, 2, 123))
        vals = list(weighted_sample_stream([1, 1, 1], [1, 1, 1], 3, 2, 123))
        self.assertTrue(all(sorted(rd) == [0, 1, 2] for rd in idx))
        self.assertEqual(vals, [[1, 1, 1], [1, 1, 1]])

    def test_draws_zero_validates_then_yields_nothing(self):
        self.assertEqual(
            list(weighted_sample_stream_indices(["a", "b"], [1, 2], 2, 0, 0)),
            [],
        )
        self.assertEqual(
            list(weighted_sample_stream(["a", "b"], [1, 2], 2, 0, 0)), []
        )
        # draws=0 仍须完成全部校验, 且在调用当场抛出(不等到迭代)。
        with self.assertRaises(TypeError):
            weighted_sample_stream_indices("ab", [1, 2], 1, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_stream_indices(["a", "b"], [1], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_stream_indices(["a"], [float("nan")], 0, 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_stream(["a"], [True], 0, 0, 0)

    def test_k_zero_yields_empty_lists(self):
        self.assertEqual(
            list(weighted_sample_stream_indices(["a", "b"], [0, 0], 0, 4, 0)),
            [[], [], [], []],
        )
        self.assertEqual(
            list(weighted_sample_stream(["a", "b"], [0, 0], 0, 3, 0)),
            [[], [], []],
        )
        self.assertEqual(
            list(weighted_sample_stream_indices([], [], 0, 2, 0)), [[], []]
        )

    def test_validation_fails_at_call_time_not_mid_iteration(self):
        # 所有失败结果都在产生第一轮之前确定: 调用当场抛异常, 而不是
        # 返回一个迭代到中途才抛错的迭代对象。
        def expect_raises(exc, fn, *args):
            with self.assertRaises(exc):
                fn(*args)  # 调用本身就必须抛出

        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a", "b"], [1, 0], 2, 3, 0)  # k 大于正权重个数
        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a"], [0], 1, 5, 0)  # 没有有效正权重
        expect_raises(
            ValueError, weighted_sample_stream,
            ["a", "b", "c"], [10 ** 100, 0, 1], 3, 2, 0)
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            ["a", "b"], [1, "x"], 1, 1, 0)
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            ["a", "b"], [1, True], 1, 1, 0)
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            ["a"], [1], True, 1, 0)
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            ["a"], [1], 1, 1, object())
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            ["a"], [1], 0, True, 0)
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            ["a"], [1], 0, 1.0, 0)
        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a"], [1], 0, -1, 0)
        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a", "b"], [1, -1], 1, 1, 0)
        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a", "b"], [1, float("inf")], 1, 1, 0)
        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a", "b"], [1], 1, 1, 0)  # 长度不一致
        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a"], [1], 2, 1, 0)  # k 超出范围
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            iter(["a"]), [1], 0, 1, 0)  # items 非可确定长度序列
        expect_raises(
            TypeError, weighted_sample_stream_indices,
            ["a"], iter([1]), 0, 1, 0)  # weights 非可确定长度序列
        # Decimal 非法值同样在调用当场抛出。
        expect_raises(
            ValueError, weighted_sample_stream_indices,
            ["a"], [Decimal("NaN")], 0, 0, 0)
        expect_raises(
            ValueError, weighted_sample_stream,
            ["a"], [Decimal("Infinity")], 1, 0, 0)

    def test_no_partial_results_before_error(self):
        # 非法调用得不到任何可迭代的部分结果: 调用直接抛异常。
        for exc, args in (
            (ValueError, (["a", "b"], [1, 0], 2, 1000, 0)),
            (TypeError, (["a", "b"], [1, "x"], 1, 1000, 0)),
        ):
            with self.subTest(args=args):
                try:
                    weighted_sample_stream_indices(*args)
                except exc:
                    pass
                else:
                    self.fail("no exception at call time for %r" % (args,))

    def test_inputs_not_mutated(self):
        items = ["p", "q", "r", "s"]
        weights = [Decimal("1.5"), 2, Fraction(1, 3), 0.5]
        items_snap, weights_snap = list(items), list(weights)
        stream_i = weighted_sample_stream_indices(items, weights, 3, 4, 99)
        stream_v = weighted_sample_stream(items, weights, 2, 4, -3)
        # 即使只消费部分轮次, 入参也不得被修改。
        next(iter(stream_i))
        list(stream_v)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)

    def test_exact_paths_supported(self):
        # 超大整数 / 极小精确权重 / 浮点求和溢出等确定性路径与批量一致。
        cases = [
            (["a", "b"], [10 ** 400, 10 ** 400], 2),
            (["H", "t", "z"], [10 ** 100, Decimal("1E-100"), Decimal("-0")], 2),
            (["a", "b", "c"], [1e308, 1e308, 1.0], 3),
            (["a", "b"], [9, Fraction(1, 100)], 1),
            (["a", "b"], [1, Fraction(1, 10 ** 100)], 1),
        ]
        for items, weights, k in cases:
            for seed in (0, 7, 2316):
                with self.subTest(items=items, k=k, seed=seed):
                    self.assertEqual(
                        list(weighted_sample_stream_indices(
                            items, weights, k, 3, seed)),
                        weighted_sample_many_indices(items, weights, k, 3, seed),
                    )
        # 零权重排除: 流式入口同样保证。
        for seed in range(50):
            for rd in weighted_sample_stream_indices(["x", "y"], [0, 5], 1, 3, seed):
                self.assertEqual(rd, [1])

    def test_seed_none_keeps_random_semantics(self):
        rounds = list(weighted_sample_stream_indices(
            list(range(50)), list(range(1, 51)), 10, 4, None))
        self.assertEqual(len(rounds), 4)
        for rd in rounds:
            self.assertEqual(len(rd), 10)
            self.assertEqual(len(set(rd)), 10)
            self.assertTrue(all(0 <= i < 50 for i in rd))

    def test_existing_entries_unchanged(self):
        # 既有入口的序列、返回类型不受新入口影响。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        many = weighted_sample_many_indices(
            ["p", "q", "r"], [2, Fraction(1), 0.5], 3, 4, 42)
        self.assertIsInstance(many, list)
        self.assertEqual(
            many, [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]]
        )


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
    """权重序列包含 decimal.Decimal 时按精确十进制值走整数精确路径。"""

    # ------------------------------------------------------------------
    # 基本行为: 确定性 / values<->indices / 完整一轮 / 重复值按位置
    # ------------------------------------------------------------------
    def test_decimal_deterministic_and_locked(self):
        items = ["a", "b", "c"]
        weights = [Decimal("1.5"), Decimal("0.5"), Decimal("2")]
        locked = [2, 0, 1]
        for _ in range(5):
            self.assertEqual(
                weighted_sample_indices(items, weights, 3, 42), locked
            )
        self.assertEqual(weighted_sample(items, weights, 3, 42),
                         [items[i] for i in locked])

    def test_decimal_full_draw_covers_all_positive_positions(self):
        items = ["a", "b", "c", "d"]
        weights = [Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), Decimal("0")]
        for seed in range(60):
            idx = weighted_sample_indices(items, weights, 3, seed)
            self.assertEqual(sorted(idx), [0, 1, 2])
            self.assertEqual(
                weighted_sample(items, weights, 3, seed),
                [items[i] for i in idx],
            )

    def test_decimal_duplicate_values_distinct_positions(self):
        idx = weighted_sample_indices([1, 1, 1], [Decimal(1)] * 3, 3, 123)
        self.assertEqual(sorted(idx), [0, 1, 2])
        self.assertEqual(weighted_sample([1, 1, 1], [Decimal(1)] * 3, 3, 123),
                         [1, 1, 1])

    # ------------------------------------------------------------------
    # 精确性: 与等价 Fraction 完全一致(逐 seed); 极小正值/超大指数
    # ------------------------------------------------------------------
    def test_decimal_matches_equivalent_fraction_exactly(self):
        # Decimal 的精确数值与对应 Fraction 相同, 放大后的整数权重逐点
        # 相同, 因此四个入口的随机流消耗与结果必须逐 seed 完全一致。
        dec_weights = [Decimal("0.1"), Decimal("0.2"), 3]
        frac_weights = [Fraction(1, 10), Fraction(1, 5), 3]
        items = ["a", "b", "c"]
        for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
            with self.subTest(seed=seed):
                self.assertEqual(
                    weighted_sample_indices(items, dec_weights, 2, seed),
                    weighted_sample_indices(items, frac_weights, 2, seed),
                )
                self.assertEqual(
                    weighted_sample_many_indices(items, dec_weights, 2, 4, seed),
                    weighted_sample_many_indices(items, frac_weights, 2, 4, seed),
                )

    def test_tiny_positive_decimal_selectable_via_public_entry(self):
        # [9, 0.01] 精确放大为 [900, 1]; 微小位置以精确比例 1/901 可被选中。
        # 该 seed 与等价 Fraction 用例一致(放大结果完全相同)。
        items = ["big", "tiny"]
        weights = [9, Decimal("0.01")]
        self.assertEqual(
            weighted_sample_indices(items, weights, 1, 2316), [1]
        )
        self.assertEqual(
            weighted_sample(items, weights, 1, 2316), ["tiny"]
        )

    def test_extreme_ratio_tiny_decimal_never_swallowed_exact(self):
        # 1E100 : 1E-100 —— float 后微小方严格为零; 精确放大为
        # [10**200, 1], needle=total-1 必须落到微小 Decimal 位置。
        import app as _app

        original = [Decimal("1E100"), Decimal("1E-100")]
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
        # 超大指数无法转有限浮点(float 在约 1E308 处溢出), 必须按精确
        # 十进制值参与, 比例仍精确。
        import app as _app

        weights = [Decimal("1E400"), Decimal("2E400")]
        self.assertEqual(
            _app._scale_to_exact_integer_weights(weights),
            [10 ** 400, 2 * 10 ** 400],
        )
        items = ["a", "b"]
        counts = [0, 0]
        trials = 3000
        for seed in range(trials):
            idx = weighted_sample_indices(items, weights, 1, seed)
            self.assertEqual(
                idx, weighted_sample_indices(items, weights, 1, seed)
            )
            counts[idx[0]] += 1
        # 比例严格 1 : 2。
        self.assertAlmostEqual(counts[0] / trials, 1 / 3, delta=0.04)
        self.assertAlmostEqual(counts[1] / trials, 2 / 3, delta=0.04)

    def test_super_huge_exponent_scaled_exactly(self):
        # 远在浮点范围之外的极大指数仍按精确十进制参与: 少量 seed 验证
        # 放大结果与抽样确定可用(统计比例由上一用例在 1E400 覆盖)。
        import app as _app

        weights = [Decimal("1E100000"), Decimal("1E100000")]
        self.assertEqual(
            _app._scale_to_exact_integer_weights(weights),
            [10 ** 100000, 10 ** 100000],
        )
        for seed in (0, 42, -7):
            idx = weighted_sample_indices(["a", "b"], weights, 2, seed)
            self.assertEqual(sorted(idx), [0, 1])
            self.assertEqual(
                idx, weighted_sample_indices(["a", "b"], weights, 2, seed)
            )

    def test_huge_exponent_mixed_with_integer_full_draw(self):
        weights = [Decimal("1E400"), 10 ** 100]
        for seed in range(20):
            idx = weighted_sample_indices(["a", "b"], weights, 2, seed)
            self.assertEqual(sorted(idx), [0, 1])

    def test_huge_and_tiny_mixed_batch_reproducible(self):
        # 极大正指数、极小正 Decimal、带符号零与大整数混排: 零权重永不
        # 出现, 微小正权重保留精确候选资格, 序列确定可复现。
        items = ["H", "t", "z"]
        weights = [10 ** 100, Decimal("1E-100"), Decimal("-0")]
        rounds = weighted_sample_many_indices(items, weights, 2, 3, 7)
        self.assertEqual(rounds, [[0, 1], [0, 1], [0, 1]])
        self.assertEqual(
            rounds, weighted_sample_many_indices(items, weights, 2, 3, 7)
        )
        self.assertEqual(
            weighted_sample_many(items, weights, 2, 3, 7),
            [[items[i] for i in rd] for rd in rounds],
        )

    # ------------------------------------------------------------------
    # 零(含带符号零)永不入选
    # ------------------------------------------------------------------
    def test_zero_and_signed_zero_decimal_never_chosen(self):
        for zero in (Decimal("0"), Decimal("-0"), Decimal("0.000"),
                     Decimal("-0.0000"), Decimal("0E3"), Decimal("-0E-3")):
            for seed in range(60):
                self.assertEqual(
                    weighted_sample_indices(
                        ["x", "y"], [zero, Decimal("5")], 1, seed
                    ),
                    [1],
                )
        # 与 float / Fraction 零混排时, 整组权重全为零且 k>0 仍按
        # ValueError 拒绝; 带符号 Decimal 零本身也不计入正权重位置。
        with self.assertRaises(ValueError):
            weighted_sample_indices(
                ["a", "b", "c"],
                [Decimal("-0"), 0.0, Fraction(0, 7)],
                1, seed=0,
            )
        self.assertEqual(
            weighted_sample_indices(
                ["a", "b", "c"],
                [Decimal("-0"), 5, Fraction(0)],
                1, 0,
            ),
            [1],
        )

    def test_signed_zero_excluded_from_full_draw(self):
        weights = [Decimal("1.5"), Decimal("-0"), Decimal("0.5")]
        for seed in range(60):
            self.assertEqual(
                sorted(weighted_sample_indices(["a", "b", "c"], weights, 2, seed)),
                [0, 2],
            )

    # ------------------------------------------------------------------
    # 混合 int / float / Fraction / Decimal
    # ------------------------------------------------------------------
    def test_mixed_all_four_weight_types_batch_reproducible(self):
        items = ["p", "q", "r", "s"]
        # 2, 1, 1/2, 1/4 -> LCM=4 放大为 [8, 4, 2, 1]。
        weights = [2, Fraction(1), 0.5, Decimal("0.25")]
        locked = [[1, 0, 2, 3], [1, 0, 2, 3], [0, 1, 3, 2], [1, 2, 0, 3]]
        many_i = weighted_sample_many_indices(items, weights, 4, 4, 42)
        self.assertEqual(many_i, locked)
        self.assertEqual(
            many_i, weighted_sample_many_indices(items, weights, 4, 4, 42)
        )
        many_v = weighted_sample_many(items, weights, 4, 4, 42)
        self.assertEqual(
            many_v, [[items[i] for i in rd] for rd in many_i]
        )
        # 第一轮与对应单轮入口逐项一致。
        self.assertEqual(
            many_i[0], weighted_sample_indices(items, weights, 4, 42)
        )
        self.assertEqual(
            many_v[0], weighted_sample(items, weights, 4, 42)
        )

    def test_mixed_decimal_float_int_proportions_exact(self):
        # [1, 0.5, Decimal(0.25)] -> [4, 2, 1], 比例 4:2:1。
        items = ["a", "b", "c"]
        weights = [1, 0.5, Decimal("0.25")]
        counts = [0, 0, 0]
        trials = 5000
        for seed in range(trials):
            counts[
                weighted_sample_indices(items, weights, 1, seed)[0]
            ] += 1
        self.assertAlmostEqual(counts[0] / trials, 4 / 7, delta=0.03)
        self.assertAlmostEqual(counts[1] / trials, 2 / 7, delta=0.03)
        self.assertAlmostEqual(counts[2] / trials, 1 / 7, delta=0.03)

    # ------------------------------------------------------------------
    # 批量入口约定: 每轮重启、共享随机流、轮间可重复位置
    # ------------------------------------------------------------------
    def test_batch_rounds_share_stream_and_restart(self):
        import app as _app

        items = ["a", "b", "c", "d"]
        weights = [Decimal("1.5"), 1, Fraction(1, 2), 0.25]
        scaled = _app._scale_to_exact_integer_weights(weights)
        for draws in (1, 2, 5):
            import random as _random

            rng = _random.Random(99)
            manual = [
                _app._sample_indices_exact_integer(
                    list(range(4)), list(scaled), 3, rng
                )
                for _ in range(draws)
            ]
            self.assertEqual(
                weighted_sample_many_indices(items, weights, 3, draws, 99),
                manual,
            )
        full = weighted_sample_many_indices(items, weights, 3, 6, 123)
        head = weighted_sample_many_indices(items, weights, 3, 2, 123)
        self.assertEqual(full[:2], head)

    def test_batch_positions_may_reappear_across_rounds(self):
        rounds = weighted_sample_many_indices(
            ["a", "b"], [Decimal("1"), Decimal("1")], 1, 20, 0
        )
        self.assertEqual(len(rounds), 20)
        self.assertTrue(all(rd == [0] or rd == [1] for rd in rounds))
        # 同一轮内不重复; 20 轮里位置允许(且高概率)重复出现。
        self.assertTrue(any(rd == rounds[0] for rd in rounds[1:]))

    # ------------------------------------------------------------------
    # 校验: NaN / sNaN / ±Inf / 负数 -> ValueError, 无 decimal 异常泄漏
    # ------------------------------------------------------------------
    def test_decimal_invalid_values_raise_value_error(self):
        for bad in (
            Decimal("NaN"),
            Decimal("sNaN"),
            Decimal("-NaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            Decimal("+Inf"),
            Decimal("-0.000000001"),
            Decimal("-1E100"),
        ):
            with self.subTest(bad=str(bad)):
                with self.assertRaises(ValueError):
                    weighted_sample_indices(["a"], [bad], 1, 0)
                with self.assertRaises(ValueError):
                    weighted_sample(["a"], [bad], 1, 0)
                with self.assertRaises(ValueError):
                    weighted_sample_many_indices(["a"], [bad], 1, 1, 0)

    def test_decimal_comparison_exception_does_not_leak(self):
        # NaN 与有序比较会抛 decimal.InvalidOperation; 调用方只能看到
        # ValueError, 即使 NaN 混在其它权重之后也是如此。
        import decimal

        for bad in (Decimal("NaN"), Decimal("sNaN")):
            for weights in ([bad], [Decimal(1), bad],
                            [Decimal(1), 1, Fraction(1), 0.5, bad]):
                try:
                    weighted_sample_indices(
                        ["x"] * len(weights), weights, 1, 0
                    )
                except ValueError:
                    pass
                except decimal.InvalidOperation:
                    self.fail("decimal.InvalidOperation leaked")
                else:
                    self.fail("no exception for %r" % bad)

    def test_decimal_invalid_validated_at_k_zero_and_draws_zero(self):
        # k=0 与 draws=0 都必须先完成全部校验。
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal("NaN")], 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal("-1")], 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a"], [Decimal("sNaN")], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many(["a"], [Decimal("Infinity")], 1, 0, 0)

    # ------------------------------------------------------------------
    # 校验: bool / 其他类型 -> TypeError; 长度/k 沿用 ValueError
    # ------------------------------------------------------------------
    def test_decimal_unsupported_weight_type_raises_type_error(self):
        for bad in (True, False, 1 + 2j, "0.1", None, [Decimal(1)]):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_indices(
                        ["a", "b"], [Decimal(1), bad], 1, 0
                    )
                with self.assertRaises(TypeError):
                    weighted_sample_many_indices(
                        ["a", "b"], [Decimal(1), bad], 1, 1, 0
                    )

    def test_decimal_existing_structural_rules_unchanged(self):
        with self.assertRaises(ValueError):
            weighted_sample(["a", "b"], [Decimal(1)], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample(["a"], [Decimal(1)], 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample(["a"], [Decimal(1)], -1, 0)
        with self.assertRaises(TypeError):
            weighted_sample("ab", [Decimal(1), Decimal(2)], 1, 0)
        with self.assertRaises(TypeError):
            weighted_sample(["a", "b"], "xy", 1, 0)
        with self.assertRaises(TypeError):
            weighted_sample(["a"], [Decimal(1)], True, 0)
        with self.assertRaises(TypeError):
            weighted_sample(["a"], [Decimal(1)], 1, object())

    def test_decimal_draws_rules_unchanged(self):
        for bad in (True, False, 1.0, "2", None, 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_many_indices(
                        ["a"], [Decimal(1)], 0, bad, 0
                    )
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(["a"], [Decimal(1)], 0, -1, 0)

    # ------------------------------------------------------------------
    # 正权重不足 / k=0 / draws=0
    # ------------------------------------------------------------------
    def test_insufficient_positive_decimal_raises_before_any_result(self):
        with self.assertRaises(ValueError):
            weighted_sample_indices(
                ["a", "b"], [Decimal("1"), Decimal("0")], 2, 0
            )
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [Decimal("-0")], 1, 0)
        # 批量入口必须在任何一轮之前抛出, 不返回部分外层结果。
        with self.assertRaises(ValueError):
            weighted_sample_many_indices(
                ["a", "b"], [Decimal("1"), Decimal("0")], 2, 1000, 0
            )
        with self.assertRaises(ValueError):
            weighted_sample_many(
                ["a", "b", "c"],
                [Decimal("1E100"), Decimal(0), Decimal("1E-100")],
                3, 2, 0,
            )

    def test_k_zero_and_draws_zero_decimal(self):
        self.assertEqual(
            weighted_sample(["a"], [Decimal("1.5")], 0, 0), []
        )
        self.assertEqual(
            weighted_sample_indices(["a"], [Decimal("1.5")], 0, 0), []
        )
        self.assertEqual(
            weighted_sample_many_indices(["a"], [Decimal(1)], 1, 0, 0), []
        )
        self.assertEqual(
            weighted_sample_many(["a"], [Decimal(1)], 1, 0, 0), []
        )
        self.assertEqual(
            weighted_sample_many_indices(
                ["a", "b"], [Decimal(0), Decimal("-0")], 0, 3, 0
            ),
            [[], [], []],
        )

    # ------------------------------------------------------------------
    # 入参不变 / seed=None / seed 类型
    # ------------------------------------------------------------------
    def test_inputs_not_mutated_with_decimal(self):
        items = ["p", "q", "r", "s"]
        weights = [Decimal("1.5"), 2, Fraction(1, 3), 0.5]
        items_snap = list(items)
        weights_snap = list(weights)
        weighted_sample(items, weights, 3, 5)
        weighted_sample_indices(items, weights, 2, -3)
        weighted_sample_many(items, weights, 3, 4, 99)
        weighted_sample_many_indices(items, weights, 2, 4, -3)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)

    def test_seed_types_and_none_with_decimal(self):
        weights = [Decimal("1E100"), Decimal("1E-100")]
        for good in (0, 1, True, 1.5, "s", b"s", bytearray(b"s"), None):
            a = weighted_sample_indices(["a", "b"], weights, 1, good)
            b = weighted_sample_indices(["a", "b"], weights, 1, good)
            self.assertEqual(a, b)
            if good is not None:
                rounds = weighted_sample_many_indices(
                    list(range(6)),
                    [Decimal(i + 1) / Decimal(7) for i in range(6)],
                    3, 2, good,
                )
                for rd in rounds:
                    self.assertEqual(len(rd), 3)
                    self.assertEqual(len(set(rd)), 3)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [Decimal(1)], 1, object())

    # ------------------------------------------------------------------
    # 旧行为与序列化不受影响
    # ------------------------------------------------------------------
    def test_existing_sequences_and_serialization_unchanged(self):
        # 旧的 int/float/Fraction 锁定序列保持。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample(["p", "q"], [0.5, 1.5], 2, 3), ["p", "q"]
        )
        # serialize_metrics 不受 Decimal 改动影响, 键排序/紧凑/Unicode 不变。
        self.assertEqual(
            serialize_metrics({"名": "值", "x": [1, 2]}),
            '{"x":[1,2],"名":"值"}',
        )
        self.assertEqual(
            serialize_metrics({"n": 10 ** 100}),
            '{"n":1%s}' % ("0" * 100),
        )


class WeightedSampleCheckpointTest(unittest.TestCase):
    """可暂停/恢复会话 weighted_sample_checkpoint / weighted_sample_resume_indices。"""

    CASES = [
        (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
        (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
        (["p", "q"], [0.5, 1.5], 2),
        (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
        (["p", "q", "r"], [2, Fraction(1), 0.5], 3),
        (["a", "b", "c"], [Decimal("1.5"), Decimal("0.5"), Decimal("2")], 3),
        (["a", "b"], [1, 0], 1),
        (["H", "t", "z"], [10 ** 100, Decimal("1E-100"), Decimal("-0")], 2),
        ([1, 1, 1], [1, 1, 1], 3),
    ]

    def test_resume_rounds_equal_batch_window(self):
        # 从断点继续的每一轮都等于批量入口对应零基区间。
        for items, weights, k in self.CASES:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                for start in (0, 1, 3):
                    with self.subTest(k=k, seed=seed, start=start):
                        total = start + 9
                        full = weighted_sample_many_indices(
                            items, weights, k, total, seed
                        )
                        state = weighted_sample_checkpoint(
                            items, weights, k, seed, start
                        )
                        rounds, next_state = weighted_sample_resume_indices(
                            items, weights, k, state, 9
                        )
                        self.assertEqual(rounds, full[start:])
                        self.assertEqual(next_state["position"], total)

    def test_chunked_chain_covers_the_same_stream(self):
        # 分块 3 + 4 + 5 推进, 每块都可能从 json 往返后的状态继续。
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        full = weighted_sample_many_indices(items, weights, k, 14, 42)
        state = weighted_sample_checkpoint(items, weights, k, 42, start=2)
        collected = []
        for chunk in (3, 4, 5):
            rounds, state = weighted_sample_resume_indices(
                items, weights, k, state, chunk
            )
            collected.extend(rounds)
            # 中途状态可经 json 文本往返后继续。
            state = json.loads(json.dumps(state))
        self.assertEqual(collected, full[2:])
        self.assertEqual(state["position"], 14)

    def test_start_zero_checkpoint_first_round_matches_single_entry(self):
        for items, weights, k in self.CASES:
            with self.subTest(k=k):
                state = weighted_sample_checkpoint(items, weights, k, 42)
                rounds, _ = weighted_sample_resume_indices(
                    items, weights, k, state, 1
                )
                self.assertEqual(
                    rounds[0], weighted_sample_indices(items, weights, k, 42)
                )

    def test_draws_zero_returns_empty_and_unchanged_position_state(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 7, start=5)
        rounds, next_state = weighted_sample_resume_indices(
            items, weights, k, state, 0
        )
        self.assertEqual(rounds, [])
        self.assertEqual(next_state["position"], 5)
        # 新状态仍可继续, 且接着产出的轮次与 start=5 的窗口一致。
        more, _ = weighted_sample_resume_indices(items, weights, k, next_state, 2)
        self.assertEqual(
            more, weighted_sample_many_indices(items, weights, k, 2, 7, start=5)
        )
        # 原状态不被修改。
        self.assertEqual(state["position"], 5)

    def test_k_zero_empty_rounds_advance_position(self):
        # k=0 时每轮为空索引且位置照常推进(不消耗随机流)。
        for items, weights in (([], []), (["a", "b"], [1, 2]),
                              (["a"], [0])):
            state = weighted_sample_checkpoint(items, weights, 0, 0)
            rounds, next_state = weighted_sample_resume_indices(
                items, weights, 0, state, 4
            )
            self.assertEqual(rounds, [[], [], [], []])
            self.assertEqual(next_state["position"], 4)
            again, third = weighted_sample_resume_indices(
                items, weights, 0, next_state, 2
            )
            self.assertEqual(again, [[], []])
            self.assertEqual(third["position"], 6)

    def test_zero_weight_never_chosen_and_duplicate_values_distinct(self):
        items = [1, 1, 1, 1]
        weights = [0, 1, 0, 1]
        full = weighted_sample_many_indices(items, weights, 2, 60, 77)
        state = weighted_sample_checkpoint(items, weights, 2, 77, start=10)
        rounds, _ = weighted_sample_resume_indices(items, weights, 2, state, 50)
        self.assertEqual(rounds, full[10:])
        for rd in rounds:
            self.assertEqual(len(rd), 2)
            self.assertEqual(len(set(rd)), 2)
            self.assertTrue(all(i in (1, 3) for i in rd))

    def test_exact_and_float_paths_both_resume_correctly(self):
        # 浮点路径(小整数)与精确路径(大整数 / Fraction / Decimal)。
        for items, weights, k in (
            (["a", "b"], [1, 2], 2),
            (["a", "b"], [10 ** 400, 10 ** 400], 2),
            (["a", "b"], [9, Fraction(1, 100)], 1),
            (["a", "b"], [Decimal("1E400"), Decimal("2E400")], 1),
            (["a", "b", "c"], [1e308, 1e308, 1.0], 3),
        ):
            for seed in (0, 7, 2316):
                state = weighted_sample_checkpoint(items, weights, k, seed, start=4)
                rounds, _ = weighted_sample_resume_indices(
                    items, weights, k, state, 3
                )
                self.assertEqual(
                    rounds,
                    weighted_sample_many_indices(
                        items, weights, k, 3, seed, start=4
                    ),
                )

    # ------------------------------------------------------------------
    # 状态: JSON 原生 / serialize_metrics / json 解析后恢复 / 版本与位置
    # ------------------------------------------------------------------
    def test_state_contains_version_position_and_validation_info(self):
        state = weighted_sample_checkpoint(
            list("abcd"), [1, 3, 2, 0], 3, 42, start=2
        )
        self.assertEqual(state["version"], 1)
        self.assertEqual(state["position"], 2)
        self.assertEqual(state["k"], 3)
        self.assertEqual(state["n"], 4)
        self.assertIn("items_digest", state)
        self.assertIn("weights_digest", state)
        self.assertIn("seed", state)
        self.assertIn("rng", state)
        self.assertIn("digest", state)

    def test_state_is_json_native_and_survives_json_roundtrip(self):
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        state = weighted_sample_checkpoint(items, weights, k, 42, start=3)
        # allow_nan=False: 若状态含 NaN/Infinity 会直接失败。
        text = json.dumps(state, allow_nan=False)
        restored = json.loads(text)
        rounds, _ = weighted_sample_resume_indices(items, weights, k, restored, 5)
        self.assertEqual(
            rounds,
            weighted_sample_many_indices(items, weights, k, 5, 42, start=3),
        )

    def test_state_works_with_serialize_metrics_and_recovers_after_parse(self):
        items, weights, k = (
            ["p", "q", "r"], [2, Fraction(1), 0.5], 3
        )
        state = weighted_sample_checkpoint(items, weights, k, 42, start=2)
        # 状态必须能直接交给 serialize_metrics(紧凑、键排序、任意精度)。
        text = serialize_metrics(state)
        parsed = json.loads(text)
        rounds, next_state = weighted_sample_resume_indices(
            items, weights, k, parsed, 4
        )
        self.assertEqual(
            rounds,
            weighted_sample_many_indices(items, weights, k, 4, 42, start=2),
        )
        self.assertEqual(next_state["position"], 6)
        # 下一状态仍可直接序列化并再次恢复。
        parsed_again = json.loads(serialize_metrics(next_state))
        more, _ = weighted_sample_resume_indices(
            items, weights, k, parsed_again, 2
        )
        self.assertEqual(
            more,
            weighted_sample_many_indices(items, weights, k, 2, 42, start=6),
        )

    def test_state_has_no_process_identity_dependency(self):
        # 恢复只依赖传入的 items/weights/k 与状态, 不依赖对象身份:
        # 用内容相同的全新序列对象恢复必须成功。
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 42)
        rounds, _ = weighted_sample_resume_indices(
            list("abcd"), [1, 3, 2, 0], k, dict(state), 3
        )
        self.assertEqual(
            rounds, weighted_sample_many_indices(items, weights, k, 3, 42)
        )

    def test_all_supported_seed_types_roundtrip(self):
        # None 由 random.Random 按系统熵播种, 不保证跨调用可复现(与既有
        # 入口语义一致), 单独验证其断点可创建并从同一快照确定性续接。
        deterministic_seeds = (0, 1, True, False, 1.5, -0.0, "s", b"s",
                               bytearray(b"s"), -99)
        for seed in deterministic_seeds:
            with self.subTest(seed=seed):
                state = weighted_sample_checkpoint(
                    ["a", "b"], [1, 2], 1, seed
                )
                restored = json.loads(json.dumps(state))
                rounds, _ = weighted_sample_resume_indices(
                    ["a", "b"], [1, 2], 1, restored, 2
                )
                self.assertEqual(
                    rounds,
                    weighted_sample_many_indices(["a", "b"], [1, 2], 1, 2, seed),
                )
        state_none = weighted_sample_checkpoint(
            ["a", "b"], [1, 2], 1, None
        )
        restored_none = json.loads(json.dumps(state_none))
        rounds_a, _ = weighted_sample_resume_indices(
            ["a", "b"], [1, 2], 1, restored_none, 2
        )
        rounds_b, _ = weighted_sample_resume_indices(
            ["a", "b"], [1, 2], 1,
            json.loads(json.dumps(state_none)), 2,
        )
        # 同一份快照无论恢复多少次都给出同一续接序列。
        self.assertEqual(rounds_a, rounds_b)
        self.assertEqual(len(rounds_a), 2)

    def test_bool_seed_is_not_swallowed_by_integer(self):
        # True 与 1 必须在状态中可区分(且二者结果也确实可能相同, 这里
        # 只验证往返后类型不丢失, 序列与各自直接采样一致)。
        for seed in (True, False):
            state = weighted_sample_checkpoint(["a", "b"], [1, 2], 1, seed)
            restored = json.loads(json.dumps(state))
            rounds, _ = weighted_sample_resume_indices(
                ["a", "b"], [1, 2], 1, restored, 2
            )
            self.assertEqual(
                rounds,
                weighted_sample_many_indices(["a", "b"], [1, 2], 1, 2, seed),
            )

    # ------------------------------------------------------------------
    # 断点创建: 沿用批量入口的全部输入校验
    # ------------------------------------------------------------------
    def test_checkpoint_validation_matches_batch_entry(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        te(lambda: weighted_sample_checkpoint("abcd", weights, k, 0))
        te(lambda: weighted_sample_checkpoint(items, iter(weights), k, 0))
        te(lambda: weighted_sample_checkpoint(items, weights, True, 0))
        te(lambda: weighted_sample_checkpoint(items, weights, 1.0, 0))
        te(lambda: weighted_sample_checkpoint(items, weights, k, object()))
        te(lambda: weighted_sample_checkpoint(items, [1, True, 2, 0], k, 0))
        te(lambda: weighted_sample_checkpoint(items, [1, "x", 2, 0], k, 0))
        te(lambda: weighted_sample_checkpoint(items, weights, k, 0, True))
        te(lambda: weighted_sample_checkpoint(items, weights, k, 0, 1.0))
        ve(lambda: weighted_sample_checkpoint(["a", "b"], [1], 1, 0))
        ve(lambda: weighted_sample_checkpoint(items, weights, 5, 0))
        ve(lambda: weighted_sample_checkpoint(items, weights, -1, 0))
        ve(lambda: weighted_sample_checkpoint(items, [1, -1, 2, 0], 1, 0))
        ve(lambda: weighted_sample_checkpoint(items, [1, float("nan"), 2, 0], 1, 0))
        ve(lambda: weighted_sample_checkpoint(items, [1, float("inf"), 2, 0], 1, 0))
        ve(lambda: weighted_sample_checkpoint(["a"], [Decimal("NaN")], 0, 0))
        ve(lambda: weighted_sample_checkpoint(items, weights, k, 0, -1))
        ve(lambda: weighted_sample_checkpoint(["a", "b"], [1, 0], 2, 0))

    def test_checkpoint_does_not_mutate_inputs(self):
        items, weights = list("abcd"), [1, 3, 2, 0]
        items_snap, weights_snap = list(items), list(weights)
        weighted_sample_checkpoint(items, weights, 3, 42, start=5)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)

    # ------------------------------------------------------------------
    # 恢复: 状态类型 / 结构 / 版本 / 摘要
    # ------------------------------------------------------------------
    def test_non_mapping_state_raises_type_error(self):
        for bad in (None, [], "{}", 1, True, (), {1, 2}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_resume_indices(
                        list("abcd"), [1, 3, 2, 0], 3, bad, 1
                    )

    def test_draws_type_and_value_rules(self):
        state = weighted_sample_checkpoint(list("abcd"), [1, 3, 2, 0], 3, 0)
        for bad in (True, False, 1.0, "1", None, [1], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_resume_indices(
                        list("abcd"), [1, 3, 2, 0], 3, state, bad
                    )
        with self.assertRaises(ValueError):
            weighted_sample_resume_indices(
                list("abcd"), [1, 3, 2, 0], 3, state, -1
            )

    def test_invalid_state_structure_raises_value_error(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)

        def ve(mutator):
            import copy as _copy
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_resume_indices(items, weights, k, bad, 1)

        ve(lambda s: s.pop("version"))
        ve(lambda s: s.pop("rng"))
        ve(lambda s: s.update(extra=1))
        ve(lambda s: s.update(position=-1))
        ve(lambda s: s.update(position=True))
        ve(lambda s: s.update(k=True))
        ve(lambda s: s.update(n=-1))
        ve(lambda s: s.update(exact=1))
        ve(lambda s: s.update(items_digest=1))
        ve(lambda s: s.update(seed=["z", 1]))
        ve(lambda s: s.update(rng={"v": 3}))
        ve(lambda s: s.update(digest=1))

    def test_unsupported_version_raises_value_error(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)
        for bad_version in (0, 2, 99, True, "1", 1.0):
            bad = dict(state)
            bad["version"] = bad_version
            with self.subTest(bad_version=bad_version):
                with self.assertRaises(ValueError):
                    weighted_sample_resume_indices(items, weights, k, bad, 1)

    def test_state_mismatch_with_inputs_raises_value_error(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)

        def ve(label, i2, w2, k2):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    weighted_sample_resume_indices(i2, w2, k2, state, 1)

        ve("k differs", items, weights, 2)
        ve("items differ", list("abce"), weights, k)
        ve("weights differ", items, [1, 3, 2, 1], k)
        # 同值不同类型(1 -> 1.0)可能改变抽样路径, 必须视为不匹配。
        ve("weight type swap", items, [1.0, 3, 2, 0], k)
        ve("fewer positions", items[:3], weights[:3], k)
        ve(
            "more positions",
            ["a", "b", "c", "d", "e"], [1, 3, 2, 0, 1], k,
        )

    def test_tampered_fields_without_valid_digest_raise_value_error(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)

        def ve(mutator):
            import copy as _copy
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_resume_indices(items, weights, k, bad, 1)

        ve(lambda s: s.update(position=s["position"] + 5))
        ve(lambda s: s["rng"]["mt"].__setitem__(0, s["rng"]["mt"][0] ^ 1))
        ve(lambda s: s.update(digest="0" * 64))
        ve(lambda s: s.update(seed=["i", 123]))
        ve(lambda s: s.update(exact=not s["exact"]))

    def test_out_of_range_rng_state_raises_value_error_even_with_digest(self):
        # 即使攻击者重算了绑定摘要, 越界的 MT 状态字/索引也必须统一抛
        # ValueError, 而不能让 random.setstate 的 OverflowError 泄漏。
        import copy as _copy
        from app import _checkpoint_binding_digest
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)
        for pos, value in (
            (0, 10 ** 40), (1, -5), (623, 1 << 32), (624, 625), (624, -1),
        ):
            bad = _copy.deepcopy(state)
            bad["rng"]["mt"][pos] = value
            bad["digest"] = _checkpoint_binding_digest(
                bad["seed"], bad["position"], bad["k"], bad["n"],
                bad["items_digest"], bad["weights_digest"],
                bad["exact"], bad["rng"],
            )
            with self.subTest(pos=pos, value=value):
                with self.assertRaises(ValueError):
                    weighted_sample_resume_indices(items, weights, k, bad, 1)

    def test_resume_input_validation_matches_sample_rules(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        te(lambda: weighted_sample_resume_indices("abcd", weights, k, state, 1))
        te(lambda: weighted_sample_resume_indices(items, iter(weights), k, state, 1))
        te(lambda: weighted_sample_resume_indices(items, weights, True, state, 1))
        te(lambda: weighted_sample_resume_indices(items, [1, True, 2, 0], k, state, 1))
        ve(lambda: weighted_sample_resume_indices(items, [1, -1, 2, 0], k, state, 1))
        ve(lambda: weighted_sample_resume_indices(items, [1, float("nan"), 2, 0], k, state, 1))
        ve(lambda: weighted_sample_resume_indices(["a", "b"], [1, 0], 2,
                                                  weighted_sample_checkpoint(["a", "b"], [1, 0], 1), 1))

    def test_no_partial_rounds_on_error(self):
        # 任何非法恢复都只能抛出异常, 不会同时返回部分轮次。
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)
        bad = dict(state)
        bad["position"] = 10 ** 9
        with self.assertRaises(ValueError):
            weighted_sample_resume_indices(items, weights, k, bad, 5)
        with self.assertRaises(ValueError):
            weighted_sample_resume_indices(items, weights, k, state, -5)

    def test_resume_does_not_mutate_inputs_or_state(self):
        items, weights = list("abcd"), [1, 3, 2, 0]
        items_snap, weights_snap = list(items), list(weights)
        state = weighted_sample_checkpoint(items, weights, 3, 42, start=2)
        import copy
        state_snap = copy.deepcopy(state)
        weighted_sample_resume_indices(items, weights, 3, state, 4)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)
        self.assertEqual(state, state_snap)

    def test_resume_without_replay_is_consistent_but_fast(self):
        # 大位置处的恢复逐轮等于 start=同位置的批量结果, 且不需要为校验
        # 从头重放(此处仅验证一致性; 性能由实现结构保证)。
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        big = weighted_sample_checkpoint(items, weights, k, 42, start=2000)
        rounds, next_state = weighted_sample_resume_indices(
            items, weights, k, big, 3
        )
        self.assertEqual(
            rounds,
            weighted_sample_many_indices(items, weights, k, 3, 42, start=2000),
        )
        self.assertEqual(next_state["position"], 2003)


class WeightedSampleResumeValuesTest(unittest.TestCase):
    """按元素值恢复入口 weighted_sample_resume。"""

    CASES = [
        (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
        (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
        (["p", "q"], [0.5, 1.5], 2),
        (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
        (["p", "q", "r"], [2, Fraction(1), 0.5], 3),
        (["a", "b", "c"], [Decimal("1.5"), Decimal("0.5"), Decimal("2")], 3),
        (["a", "b"], [1, 0], 1),
        (["H", "t", "z"], [10 ** 100, Decimal("1E-100"), Decimal("-0")], 2),
        ([1, 1, 1], [1, 1, 1], 3),
    ]

    def test_rounds_map_index_rounds_position_by_position(self):
        # 每轮元素值与按索引入口的每轮原始位置逐项映射一致。
        for items, weights, k in self.CASES:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                for start in (0, 1, 3):
                    with self.subTest(k=k, seed=seed, start=start):
                        state = weighted_sample_checkpoint(
                            items, weights, k, seed, start
                        )
                        idx_rounds, idx_next = weighted_sample_resume_indices(
                            items, weights, k, state, 6
                        )
                        val_rounds, val_next = weighted_sample_resume(
                            items, weights, k, state, 6
                        )
                        self.assertEqual(
                            val_rounds,
                            [[items[i] for i in rd] for rd in idx_rounds],
                        )
                        # 两个入口产出的下一状态完全相同。
                        self.assertEqual(val_next, idx_next)
                        self.assertEqual(val_next["position"], start + 6)

    def test_rounds_equal_batch_values_window(self):
        # 逐轮等于 weighted_sample_many 对应零基区间。
        for items, weights, k in self.CASES:
            for seed in (0, 42, "s"):
                for start in (0, 2):
                    with self.subTest(k=k, seed=seed, start=start):
                        full = weighted_sample_many(
                            items, weights, k, start + 7, seed
                        )
                        state = weighted_sample_checkpoint(
                            items, weights, k, seed, start
                        )
                        rounds, next_state = weighted_sample_resume(
                            items, weights, k, state, 7
                        )
                        self.assertEqual(rounds, full[start:])
                        self.assertEqual(next_state["position"], start + 7)

    def test_start_zero_first_round_matches_single_entry(self):
        for items, weights, k in self.CASES:
            with self.subTest(k=k):
                state = weighted_sample_checkpoint(items, weights, k, 42)
                rounds, _ = weighted_sample_resume(items, weights, k, state, 1)
                self.assertEqual(rounds[0], weighted_sample(items, weights, k, 42))

    def test_chunked_chain_with_json_roundtrip(self):
        # 分块 3 + 4 + 5, 中途状态经 json 文本往返后继续, 覆盖同一随机流。
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        full = weighted_sample_many(items, weights, k, 14, 42)
        state = weighted_sample_checkpoint(items, weights, k, 42, start=2)
        collected = []
        for chunk in (3, 4, 5):
            rounds, state = weighted_sample_resume(items, weights, k, state, chunk)
            collected.extend(rounds)
            state = json.loads(json.dumps(state))
        self.assertEqual(collected, full[2:])
        self.assertEqual(state["position"], 14)

    def test_next_state_feeds_either_resume_entry(self):
        # 值入口产出的下一状态可交给按索引入口继续, 反之亦然。
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        state = weighted_sample_checkpoint(items, weights, k, 7, start=1)
        vals, mid = weighted_sample_resume(items, weights, k, state, 3)
        idx, end = weighted_sample_resume_indices(items, weights, k, mid, 2)
        full_i = weighted_sample_many_indices(items, weights, k, 5, 7, start=1)
        self.assertEqual(vals, [[items[i] for i in rd] for rd in full_i[:3]])
        self.assertEqual(idx, full_i[3:])
        self.assertEqual(end["position"], 6)

    def test_draws_zero_returns_empty_and_unchanged_state_copy(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 7, start=5)
        rounds, next_state = weighted_sample_resume(items, weights, k, state, 0)
        self.assertEqual(rounds, [])
        # 位置与随机状态不变, 且是可继续使用的状态副本。
        self.assertEqual(next_state["position"], 5)
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)
        more, _ = weighted_sample_resume(items, weights, k, next_state, 2)
        self.assertEqual(
            more, weighted_sample_many(items, weights, k, 2, 7, start=5)
        )
        # 原状态不被修改。
        self.assertEqual(state["position"], 5)

    def test_k_zero_empty_rounds_advance_position(self):
        # k=0 时每轮为空列表, 位置照常推进且不消耗随机流。
        for items, weights in (([], []), (["a", "b"], [1, 2]), (["a"], [0])):
            state = weighted_sample_checkpoint(items, weights, 0, 0)
            rounds, next_state = weighted_sample_resume(items, weights, 0, state, 4)
            self.assertEqual(rounds, [[], [], [], []])
            self.assertEqual(next_state["position"], 4)
            again, third = weighted_sample_resume(items, weights, 0, next_state, 2)
            self.assertEqual(again, [[], []])
            self.assertEqual(third["position"], 6)

    def test_duplicate_values_consume_distinct_positions(self):
        # 相同值的不同位置分别消耗: 值序列与索引序列逐项对应, 位置不重复。
        items = [1, 1, 1, 1]
        weights = [0, 1, 0, 1]
        state = weighted_sample_checkpoint(items, weights, 2, 77, start=10)
        val_rounds, _ = weighted_sample_resume(items, weights, 2, state, 50)
        idx_rounds, _ = weighted_sample_resume_indices(
            items, weights, 2,
            weighted_sample_checkpoint(items, weights, 2, 77, start=10), 50,
        )
        self.assertEqual(
            val_rounds, [[items[i] for i in rd] for rd in idx_rounds]
        )
        for rd in idx_rounds:
            self.assertEqual(len(set(rd)), 2)  # 无重复位置
            self.assertTrue(all(i in (1, 3) for i in rd))  # 零权重永不出现
        full = weighted_sample_many([1, 1, 1], [1, 1, 1], 3, 4, 123)
        state = weighted_sample_checkpoint([1, 1, 1], [1, 1, 1], 3, 123)
        rounds, _ = weighted_sample_resume([1, 1, 1], [1, 1, 1], 3, state, 4)
        self.assertEqual(rounds, full)

    def test_exact_and_float_paths_both_resume_correctly(self):
        for items, weights, k in (
            (["a", "b"], [1, 2], 2),
            (["a", "b"], [10 ** 400, 10 ** 400], 2),
            (["a", "b"], [9, Fraction(1, 100)], 1),
            (["a", "b"], [Decimal("1E400"), Decimal("2E400")], 1),
            (["a", "b", "c"], [1e308, 1e308, 1.0], 3),
        ):
            for seed in (0, 7, 2316):
                state = weighted_sample_checkpoint(items, weights, k, seed, start=4)
                rounds, _ = weighted_sample_resume(items, weights, k, state, 3)
                self.assertEqual(
                    rounds,
                    weighted_sample_many(items, weights, k, 3, seed, start=4),
                )

    def test_state_survives_serialize_metrics_and_json_parse(self):
        items, weights, k = (["p", "q", "r"], [2, Fraction(1), 0.5], 3)
        state = weighted_sample_checkpoint(items, weights, k, 42, start=2)
        parsed = json.loads(serialize_metrics(state))
        rounds, next_state = weighted_sample_resume(items, weights, k, parsed, 4)
        self.assertEqual(
            rounds, weighted_sample_many(items, weights, k, 4, 42, start=2)
        )
        self.assertEqual(next_state["position"], 6)
        # 下一状态仍为 JSON 原生值, 可再次序列化/解析并继续恢复。
        parsed_again = json.loads(serialize_metrics(next_state))
        more, _ = weighted_sample_resume(items, weights, k, parsed_again, 2)
        self.assertEqual(
            more, weighted_sample_many(items, weights, k, 2, 42, start=6)
        )

    # ------------------------------------------------------------------
    # 校验: 与按索引入口完全相同的异常类别
    # ------------------------------------------------------------------
    def test_non_mapping_state_raises_type_error(self):
        for bad in (None, [], "{}", 1, True, (), {1, 2}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_resume(list("abcd"), [1, 3, 2, 0], 3, bad, 1)

    def test_draws_type_and_value_rules(self):
        state = weighted_sample_checkpoint(list("abcd"), [1, 3, 2, 0], 3, 0)
        for bad in (True, False, 1.0, "1", None, [1], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_resume(list("abcd"), [1, 3, 2, 0], 3, state, bad)
        with self.assertRaises(ValueError):
            weighted_sample_resume(list("abcd"), [1, 3, 2, 0], 3, state, -1)

    def test_invalid_state_and_mismatch_raise_value_error(self):
        import copy as _copy

        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)

        def ve(mutator):
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_resume(items, weights, k, bad, 1)

        ve(lambda s: s.pop("version"))
        ve(lambda s: s.pop("rng"))
        ve(lambda s: s.update(extra=1))
        ve(lambda s: s.update(position=-1))
        ve(lambda s: s.update(version=2))
        ve(lambda s: s.update(position=s["position"] + 5))
        ve(lambda s: s.update(digest="0" * 64))
        # 与当前输入不匹配。
        with self.assertRaises(ValueError):
            weighted_sample_resume(items, weights, 2, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_resume(list("abce"), weights, k, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_resume(items, [1.0, 3, 2, 0], k, state, 1)

    def test_input_validation_matches_sample_rules(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        te(lambda: weighted_sample_resume("abcd", weights, k, state, 1))
        te(lambda: weighted_sample_resume(items, iter(weights), k, state, 1))
        te(lambda: weighted_sample_resume(items, weights, True, state, 1))
        te(lambda: weighted_sample_resume(items, [1, True, 2, 0], k, state, 1))
        te(lambda: weighted_sample_resume(items, [1, "x", 2, 0], k, state, 1))
        ve(lambda: weighted_sample_resume(items, [1, -1, 2, 0], k, state, 1))
        ve(lambda: weighted_sample_resume(items, [1, float("nan"), 2, 0], k, state, 1))
        ve(lambda: weighted_sample_resume(items, [1, Decimal("NaN"), 2, 0], k, state, 1))
        ve(lambda: weighted_sample_resume(items, weights, 5, state, 1))
        # 权重不足在产生任何轮次前抛 ValueError。
        ve(lambda: weighted_sample_resume(
            ["a", "b"], [1, 0], 2,
            weighted_sample_checkpoint(["a", "b"], [1, 0], 1), 1))

    def test_no_partial_rounds_on_error(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)
        bad = dict(state)
        bad["position"] = 10 ** 9
        with self.assertRaises(ValueError):
            weighted_sample_resume(items, weights, k, bad, 5)
        with self.assertRaises(ValueError):
            weighted_sample_resume(items, weights, k, state, -5)

    def test_resume_does_not_mutate_inputs_or_state(self):
        import copy

        items, weights = list("abcd"), [1, 3, 2, 0]
        items_snap, weights_snap = list(items), list(weights)
        state = weighted_sample_checkpoint(items, weights, 3, 42, start=2)
        state_snap = copy.deepcopy(state)
        weighted_sample_resume(items, weights, 3, state, 4)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)
        self.assertEqual(state, state_snap)


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


class ExactDecimalFractionSerializationTest(unittest.TestCase):
    """指标值新增的精确 Decimal / Fraction 序列化支持。"""

    # ------------------------------------------------------------------
    # 有限 Decimal: 不带引号的合法 JSON 数字, 保留自身十进制表示
    # ------------------------------------------------------------------
    def test_finite_decimal_emits_unquoted_json_number(self):
        for literal in (
            "0", "-0", "1", "-1", "1.50", "-1.50", "0.01", "100.0",
            "1E+2", "1E-2", "1E0", "1.50E+2", "-1E-100", "123456789.987654321",
        ):
            with self.subTest(literal=literal):
                text = serialize_metrics({"v": Decimal(literal)})
                # 整体必须是合法 JSON, Decimal 出现为数字而非字符串。
                parsed = json.loads(text)
                self.assertEqual(parsed["v"], json.loads(str(Decimal(literal))))
                # 数字文本不带引号: 去掉键部分后不应出现引号包裹。
                self.assertNotIn('"%s"' % str(Decimal(literal)), text)

    def test_decimal_preserves_precision_exponent_trailing_zero_signed_zero(self):
        # 按 Decimal 自身十进制表示逐字保留: 精度、指数形式、尾随零、负零。
        # 用 (值, 期望文本) 列表而非 dict: 这些 Decimal 数值相同但文本不同
        # (如 0.00 / -0.0000 / -0 数值都为零), 作为 dict 键会相互覆盖。
        cases = [
            (Decimal("1.50"), "1.50"),
            (Decimal("0.00"), "0.00"),
            (Decimal("-0.0000"), "-0.0000"),
            (Decimal("-0"), "-0"),
            (Decimal("1E+2"), "1E+2"),
            (Decimal("-1E-100"), "-1E-100"),
            (Decimal("1E100000"), "1E+100000"),
            (Decimal("100.0"), "100.0"),
            (Decimal("9.99999999999999999999"), "9.99999999999999999999"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(serialize_metrics(value), expected)
        nested = {
            "a": Decimal("1.50"),
            "b": [Decimal("1E+2"), (Decimal("-0.00"), {"c": Decimal("100.0")})],
        }
        self.assertEqual(
            serialize_metrics(nested),
            '{"a":1.50,"b":[1E+2,[-0.00,{"c":100.0}]]}',
        )

    def test_decimal_recursive_in_all_container_positions(self):
        tree = {
            "top": Decimal("3.14"),
            "list": [Decimal("1"), Decimal("-2.5")],
            "tuple": (Decimal("0.5"),),
            "deep": {"d": [{"e": (Decimal("2.71828"),)}]},
        }
        text = serialize_metrics(tree)
        json.loads(text)  # 合法 JSON
        self.assertEqual(
            text,
            '{"deep":{"d":[{"e":[2.71828]}]},"list":[1,-2.5],'
            '"top":3.14,"tuple":[0.5]}',
        )

    def test_decimal_huge_exponent_and_coeff_exact_beyond_float(self):
        # 远超双精度范围的指数与超长系数都逐字精确, 不经过浮点。
        self.assertEqual(serialize_metrics(Decimal("1E100000")), "1E+100000")
        long_coeff = Decimal("9." + "9" * 5000)
        self.assertEqual(
            serialize_metrics({"x": long_coeff}),
            '{"x":9.' + "9" * 5000 + "}",
        )

    def test_decimal_subclass_custom_text_is_ignored(self):
        class WeirdDecimal(Decimal):
            def __str__(self):
                return "not-a-number"

            __repr__ = __str__

        self.assertEqual(serialize_metrics(WeirdDecimal("1.50")), "1.50")
        self.assertEqual(
            serialize_metrics({"x": WeirdDecimal("-0")}), '{"x":-0}'
        )

    # ------------------------------------------------------------------
    # 非有限 Decimal: 统一 ValueError, 不输出扩展字面量, 异常不外泄
    # ------------------------------------------------------------------
    def test_non_finite_decimal_raises_value_error_everywhere(self):
        for bad in (
            Decimal("NaN"), Decimal("sNaN"), Decimal("-NaN"),
            Decimal("Infinity"), Decimal("-Infinity"), Decimal("+Inf"),
        ):
            with self.subTest(bad=str(bad)):
                with self.assertRaises(ValueError):
                    serialize_metrics(bad)
                with self.assertRaises(ValueError):
                    serialize_metrics({"x": bad})
                with self.assertRaises(ValueError):
                    serialize_metrics([bad])
                with self.assertRaises(ValueError):
                    serialize_metrics({"deep": [{"x": (bad,)}]})

    def test_decimal_comparison_exception_does_not_leak_on_serialize(self):
        import decimal

        for bad in (Decimal("NaN"), Decimal("sNaN")):
            for tree in (
                bad,
                [Decimal(1), bad],
                {"a": 1, "b": [bad]},
                (Decimal(1), 1, Fraction(1), 1.5, bad),
            ):
                try:
                    serialize_metrics(tree)
                except ValueError:
                    pass
                except decimal.InvalidOperation:
                    self.fail("decimal.InvalidOperation leaked")
                else:
                    self.fail("no exception for non-finite Decimal")

    def test_non_finite_decimal_never_emitted_as_extension_literal(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            for bad in (
                Decimal(token),
                Decimal("s" + token) if token == "NaN" else Decimal(token),
            ):
                try:
                    serialize_metrics({"x": bad})
                except ValueError:
                    continue
                self.fail("non-finite Decimal serialized")

    # ------------------------------------------------------------------
    # Fraction: 固定 [分子, 正分母] 两个精确整数
    # ------------------------------------------------------------------
    def test_fraction_emits_two_integer_array(self):
        self.assertEqual(serialize_metrics(Fraction(3, 4)), "[3,4]")
        self.assertEqual(
            serialize_metrics({"f": Fraction(3, 4)}), '{"f":[3,4]}'
        )

    def test_integer_valued_fraction_keeps_two_elements(self):
        self.assertEqual(serialize_metrics(Fraction(6, 2)), "[3,1]")
        self.assertEqual(serialize_metrics(Fraction(0, 5)), "[0,1]")
        self.assertEqual(serialize_metrics({"f": Fraction(-4, 2)}), '{"f":[-2,1]}')

    def test_fraction_denominator_always_positive(self):
        # 规范化: 符号落在分子, 分母恒正。
        for args, num in (
            ((3, 4), 3), ((-3, 4), -3), ((3, -4), -3), ((-3, -4), 3),
            ((10 ** 100, 7), 10 ** 100), ((10 ** 100, -7), -(10 ** 100)),
        ):
            with self.subTest(args=args):
                f = Fraction(*args)
                text = serialize_metrics(f)
                payload = json.loads(text)
                self.assertEqual(payload, [num, f.denominator])
                self.assertEqual(len(payload), 2)
                self.assertGreater(f.denominator, 0)
                self.assertEqual(text, "[%s,%d]" % (
                    _unlimited_int_str(num), f.denominator))

    def test_fraction_huge_components_exact_without_float(self):
        import sys

        f = Fraction(10 ** 5000 + 1, 10 ** 4000 - 3)
        text = serialize_metrics(f)
        self.assertEqual(
            text,
            "[" + _unlimited_int_str(f.numerator) + ","
            + _unlimited_int_str(f.denominator) + "]",
        )
        # 两个分量必须是整数字面量(无小数点、无指数、无引号)。
        body = text[1:-1]
        for part in body.split(","):
            self.assertNotIn(".", part)
            self.assertNotIn("e", part.lower())
            self.assertNotIn('"', part)
        # 即使运行时整数转文本上限被压低, 仍须精确输出。
        if hasattr(sys, "set_int_max_str_digits"):
            old = sys.get_int_max_str_digits()
            self.addCleanup(sys.set_int_max_str_digits, old)
            sys.set_int_max_str_digits(640)
            self.assertEqual(
                serialize_metrics(f),
                "[" + _unlimited_int_str(f.numerator) + ","
                + _unlimited_int_str(f.denominator) + "]",
            )

    def test_fraction_recursive_and_distinguishable_from_number(self):
        tree = {
            "ratio": Fraction(1, 3),
            "mix": [Fraction(-5, 2), {"whole": Fraction(7, 1)}],
            "t": (Fraction(0, 9),),
        }
        text = serialize_metrics(tree)
        self.assertEqual(
            text,
            '{"mix":[[-5,2],{"whole":[7,1]}],"ratio":[1,3],"t":[[0,1]]}',
        )
        parsed = json.loads(text)
        # 独立调用方能直接区分普通 JSON 数值与 Fraction 的二整数数组。
        self.assertEqual(parsed["ratio"], [1, 3])
        self.assertIsInstance(parsed["ratio"], list)
        self.assertEqual(parsed["mix"][0], [-5, 2])

    def test_fraction_subclass_custom_text_is_ignored(self):
        class WeirdFraction(Fraction):
            def __str__(self):
                return "not-a-fraction"

            __repr__ = __str__

        self.assertEqual(serialize_metrics(WeirdFraction(3, 4)), "[3,4]")

    # ------------------------------------------------------------------
    # Decimal / Fraction 只能作为值, 不能成为新的字典键类型
    # ------------------------------------------------------------------
    def test_decimal_and_fraction_keys_rejected_with_type_error(self):
        for key in (
            Decimal("1.5"), Decimal("0"), Decimal("1E2"),
            Fraction(1, 2), Fraction(0), Fraction(3),
        ):
            with self.subTest(key=repr(key)):
                with self.assertRaises(TypeError):
                    serialize_metrics({key: 1})
                with self.assertRaises(TypeError):
                    serialize_metrics({"nested": {key: 1}})
                with self.assertRaises(TypeError):
                    serialize_metrics([{key: 1}])

    # ------------------------------------------------------------------
    # 校验先于文本: 错误嵌套再深也不返回部分 JSON
    # ------------------------------------------------------------------
    def test_all_nested_inputs_validated_before_text(self):
        with self.assertRaises(ValueError):
            serialize_metrics(
                {"ok": 1, "bad": {"deep": [Decimal("NaN")]}}
            )
        with self.assertRaises(ValueError):
            serialize_metrics(
                [Fraction(1, 2), {"x": Decimal("Infinity")}]
            )
        with self.assertRaises(TypeError):
            serialize_metrics(
                {"ok": Decimal("1"), "bad": {"deep": {1, 2}}}
            )
        with self.assertRaises(TypeError):
            serialize_metrics([Fraction(1, 2), b"bytes"])

    def test_circular_reference_with_exact_numbers_raises_type_error(self):
        a = [Decimal("1.5")]
        a.append(a)
        with self.assertRaises(TypeError):
            serialize_metrics(a)
        d = {"f": Fraction(1, 2)}
        d["self"] = d
        with self.assertRaises(TypeError):
            serialize_metrics(d)

    def test_non_finite_float_still_value_error_alongside_exact_numbers(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                serialize_metrics([Decimal("1"), Fraction(1, 2), bad])

    # ------------------------------------------------------------------
    # 既有键规则 / 紧凑格式 / 入参不变
    # ------------------------------------------------------------------
    def test_existing_key_collision_rules_still_apply(self):
        with self.assertRaises(ValueError):
            serialize_metrics({1: Decimal("1"), "1": Fraction(1, 2)})
        with self.assertRaises(ValueError):
            serialize_metrics({"nested": {2: Decimal("1"), "2": 2}})

    def test_compact_unicode_sorted_format_preserved_with_exact_values(self):
        data = {"名": Decimal("1.50"), "x": [Fraction(1, 2)], "a": 1}
        self.assertEqual(
            serialize_metrics(data),
            '{"a":1,"x":[[1,2]],"名":1.50}',
        )

    def test_exact_number_inputs_not_mutated(self):
        data = {
            "d": [Decimal("1.50")],
            "f": (Fraction(1, 2),),
            "nested": {"x": Decimal("-0")},
        }
        snapshot = repr(data)
        tuple_before = data["f"]
        serialize_metrics(data)
        self.assertEqual(repr(data), snapshot)
        self.assertIs(data["f"], tuple_before)
        self.assertEqual(str(data["d"][0]), "1.50")
        self.assertEqual(str(data["nested"]["x"]), "-0")


def _unlimited_int_str(value):
    """临时关闭整数转文本位数限制后取 str, 仅用于构造期望值。"""
    import sys

    if not hasattr(sys, "set_int_max_str_digits"):
        return str(value)
    old = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(0)
    try:
        return str(value)
    finally:
        sys.set_int_max_str_digits(old)


if __name__ == "__main__":
    unittest.main()
