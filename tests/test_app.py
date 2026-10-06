import json
import math
import unittest
from decimal import Decimal
from fractions import Fraction

import app
from app import (
    weighted_sample,
    weighted_sample_indices,
    weighted_sample_excluding,
    weighted_sample_excluding_indices,
    weighted_sample_many,
    weighted_sample_many_indices,
    weighted_sample_schedule,
    weighted_sample_schedule_indices,
    weighted_sample_schedule_counts,
    weighted_sample_schedule_stream,
    weighted_sample_schedule_stream_indices,
    weighted_sample_schedule_checkpoint,
    weighted_sample_schedule_resume_indices,
    weighted_sample_schedule_resume,
    weighted_sample_k_schedule_indices,
    weighted_sample_k_schedule,
    weighted_sample_k_schedule_stream_indices,
    weighted_sample_k_schedule_counts,
    weighted_sample_k_schedule_checkpoint,
    weighted_sample_k_schedule_resume_indices,
    weighted_sample_k_schedule_resume,
    weighted_sample_plan_indices,
    weighted_sample_plan,
    weighted_sample_plan_counts,
    weighted_sample_plan_checkpoint,
    weighted_sample_plan_resume_indices,
    weighted_sample_plan_resume,
    weighted_sample_partition_indices,
    weighted_sample_partition,
    weighted_sample_partition_checkpoint,
    weighted_sample_partition_resume_indices,
    weighted_sample_partition_resume,
    weighted_sample_stratified_indices,
    weighted_sample_stratified,
    weighted_sample_stratified_counts,
    weighted_sample_stratified_checkpoint,
    weighted_sample_stratified_resume_indices,
    weighted_sample_stratified_resume,
    weighted_sample_stratified_schedule_indices,
    weighted_sample_stratified_schedule,
    weighted_sample_stratified_schedule_counts,
    weighted_sample_stratified_schedule_stream_indices,
    weighted_sample_stratified_schedule_stream,
    weighted_sample_stratified_schedule_checkpoint,
    weighted_sample_stratified_schedule_resume_indices,
    weighted_sample_stratified_schedule_resume,
    weighted_sample_stream,
    weighted_sample_stream_indices,
    weighted_sample_many_excluding,
    weighted_sample_many_excluding_indices,
    weighted_sample_stream_excluding,
    weighted_sample_stream_excluding_indices,
    weighted_sample_counts,
    weighted_sample_excluding_counts,
    weighted_sample_checkpoint,
    weighted_sample_resume_indices,
    weighted_sample_resume,
    weighted_sample_excluding_checkpoint,
    weighted_sample_excluding_resume_indices,
    weighted_sample_excluding_resume,
    serialize_metrics,
    deserialize_metrics,
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
        ([], [], 0),
    ]

    def test_value_rounds_match_index_rounds_position_by_position(self):
        # 每轮元素值必须是索引轮次的逐项映射, 下一状态与按索引入口相同。
        for items, weights, k in self.CASES:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                for start in (0, 1, 3):
                    with self.subTest(k=k, seed=seed, start=start):
                        state = weighted_sample_checkpoint(
                            items, weights, k, seed, start
                        )
                        idx_rounds, idx_next = weighted_sample_resume_indices(
                            items, weights, k, state, 7
                        )
                        val_rounds, val_next = weighted_sample_resume(
                            items, weights, k,
                            json.loads(json.dumps(state)), 7,
                        )
                        self.assertEqual(
                            val_rounds,
                            [[items[i] for i in rd] for rd in idx_rounds],
                        )
                        self.assertEqual(val_next, idx_next)

    def test_value_rounds_equal_batch_values_window(self):
        # 逐轮等于 weighted_sample_many 的零基区间 [start, start+draws)。
        for items, weights, k in self.CASES:
            for seed in (0, 7, 42, -3, "s", True):
                for start, draws in ((0, 5), (2, 4), (10, 3)):
                    with self.subTest(k=k, seed=seed, start=start):
                        state = weighted_sample_checkpoint(
                            items, weights, k, seed, start
                        )
                        rounds, next_state = weighted_sample_resume(
                            items, weights, k, state, draws
                        )
                        self.assertEqual(
                            rounds,
                            weighted_sample_many(
                                items, weights, k,
                                start + draws, seed, start=0,
                            )[start:],
                        )
                        self.assertEqual(next_state["position"], start + draws)

    def test_duplicate_values_consume_distinct_positions(self):
        # 相同值的不同位置分别消耗: 每轮三个值但来自三个互不重复的位置。
        items = [1, 1, 1, 1]
        weights = [1, 1, 1, 1]
        state = weighted_sample_checkpoint(items, weights, 3, 123)
        idx_rounds, _ = weighted_sample_resume_indices(
            items, weights, 3, state, 40
        )
        val_rounds, _ = weighted_sample_resume(
            [1, 1, 1, 1], [1, 1, 1, 1], 3,
            weighted_sample_checkpoint(items, weights, 3, 123), 40,
        )
        self.assertEqual(val_rounds, [[1, 1, 1] for _ in range(40)])
        # 位置层面仍然互不重复(值层面无法直接观察, 由索引轮次佐证)。
        for rd in idx_rounds:
            self.assertEqual(len(set(rd)), 3)
        self.assertEqual(
            val_rounds, [[items[i] for i in rd] for rd in idx_rounds]
        )

    def test_zero_weight_positions_never_appear(self):
        # 零权重位置永不出现; 两个正权重位置的值相同也仍按位置独立消耗。
        items = ["x", "v", "x"]
        weights = [0, 1, 1]
        state = weighted_sample_checkpoint(items, weights, 2, 77, start=5)
        rounds, _ = weighted_sample_resume(items, weights, 2, state, 60)
        full = weighted_sample_many(items, weights, 2, 65, 77)
        self.assertEqual(rounds, full[5:])
        for rd in rounds:
            # 每轮恰好抽满两个正权重位置(位置 1、2), 值为 "v" 与 "x"。
            self.assertEqual(sorted(rd), ["v", "x"])

    def test_chunked_chain_covers_the_same_value_stream(self):
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        full = weighted_sample_many(items, weights, k, 14, 42)
        state = weighted_sample_checkpoint(items, weights, k, 42, start=2)
        collected = []
        for chunk in (3, 4, 5):
            rounds, state = weighted_sample_resume(items, weights, k, state, chunk)
            collected.extend(rounds)
            # 中途状态经 serialize_metrics + json 解析后仍可继续恢复。
            state = json.loads(serialize_metrics(state))
        self.assertEqual(collected, full[2:])
        self.assertEqual(state["position"], 14)

    def test_next_state_can_reenter_either_resume_entry(self):
        # 值入口产出的下一状态也能交给索引入口, 二者继续推进的位置一致。
        items, weights, k = ["p", "q", "r"], [2, Fraction(1), 0.5], 3
        state = weighted_sample_checkpoint(items, weights, k, 42, start=2)
        val_rounds, next_state = weighted_sample_resume(
            items, weights, k, state, 4
        )
        self.assertEqual(
            val_rounds,
            weighted_sample_many(items, weights, k, 6, 42)[2:],
        )
        idx_rounds, state2 = weighted_sample_resume_indices(
            items, weights, k, next_state, 2
        )
        self.assertEqual(
            [items[i] for i in idx_rounds[0]],
            weighted_sample_many(items, weights, k, 8, 42)[6],
        )
        self.assertEqual(state2["position"], 8)
        # 再回到值入口仍逐轮一致。
        more, state3 = weighted_sample_resume(items, weights, k, state2, 2)
        self.assertEqual(
            more, weighted_sample_many(items, weights, k, 10, 42)[8:]
        )
        self.assertEqual(state3["position"], 10)

    def test_state_is_json_native_and_survives_serialize_roundtrip(self):
        items, weights, k = (
            list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        )
        state = weighted_sample_checkpoint(items, weights, k, 42, start=3)
        text = serialize_metrics(state)
        parsed = json.loads(text)
        rounds, next_state = weighted_sample_resume(
            items, weights, k, parsed, 5
        )
        self.assertEqual(
            rounds, weighted_sample_many(items, weights, k, 8, 42)[3:]
        )
        # 下一状态再次经 serialize_metrics / json 后仍可继续恢复。
        again = json.loads(serialize_metrics(next_state))
        more, _ = weighted_sample_resume(items, weights, k, again, 2)
        self.assertEqual(
            more, weighted_sample_many(items, weights, k, 10, 42)[8:]
        )

    def test_seed_none_snapshot_is_deterministic_on_resume(self):
        items, weights = list(range(20)), list(range(1, 21))
        state = weighted_sample_checkpoint(items, weights, 5, None)
        rounds_a, next_a = weighted_sample_resume(
            items, weights, 5, json.loads(json.dumps(state)), 4
        )
        rounds_b, next_b = weighted_sample_resume(
            items, weights, 5, json.loads(json.dumps(state)), 4
        )
        self.assertEqual(rounds_a, rounds_b)
        self.assertEqual(next_a, next_b)
        idx_rounds, _ = weighted_sample_resume_indices(
            items, weights, 5, json.loads(json.dumps(state)), 4
        )
        self.assertEqual(rounds_a, [[items[i] for i in rd] for rd in idx_rounds])

    def test_draws_zero_returns_empty_and_unchanged_state_copy(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 7, start=5)
        rounds, next_state = weighted_sample_resume(
            items, weights, k, state, 0
        )
        self.assertEqual(rounds, [])
        self.assertEqual(next_state["position"], 5)
        # position 与 RNG 快照都不变, digest 因而也保持不变。
        self.assertEqual(next_state["rng"], state["rng"])
        self.assertEqual(next_state["digest"], state["digest"])
        self.assertIsNot(next_state, state)
        # 用返回状态继续与直接从原状态继续逐轮一致。
        more, _ = weighted_sample_resume(items, weights, k, next_state, 2)
        self.assertEqual(
            more, weighted_sample_many(items, weights, k, 7, 7)[5:]
        )
        # 原状态不被修改。
        self.assertEqual(state["position"], 5)

    def test_k_zero_draws_empty_lists_advance_position_without_rng(self):
        for items, weights in (([], []), (["a", "b"], [1, 2]),
                               (["a"], [0])):
            state = weighted_sample_checkpoint(items, weights, 0, 0)
            rng_before = state["rng"]
            rounds, next_state = weighted_sample_resume(
                items, weights, 0, state, 4
            )
            self.assertEqual(rounds, [[], [], [], []])
            self.assertEqual(next_state["position"], 4)
            # 不消耗随机流: RNG 快照与创建时一致。
            self.assertEqual(next_state["rng"], rng_before)
            again, third = weighted_sample_resume(
                items, weights, 0, next_state, 2
            )
            self.assertEqual(again, [[], []])
            self.assertEqual(third["position"], 6)
            self.assertEqual(third["rng"], rng_before)

    def test_validation_starts_with_sample_entry_checks(self):
        # items/weights/k 的结构、权重与范围校验先于 state / draws:
        # 即便 state 同时损坏且 draws 非法, 仍报告采样入口的异常类别。
        good_state = weighted_sample_checkpoint(
            list("abcd"), [1, 3, 2, 0], 3, 0
        )
        tampered = dict(good_state)
        tampered["version"] = 2

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        te(lambda: weighted_sample_resume("abcd", [1, 3, 2, 0], 3,
                                          tampered, -1))
        te(lambda: weighted_sample_resume(list("abcd"),
                                          iter([1, 3, 2, 0]), 3,
                                          tampered, -1))
        te(lambda: weighted_sample_resume(list("abcd"), [1, 3, 2, 0],
                                          True, tampered, -1))
        te(lambda: weighted_sample_resume(list("abcd"),
                                          [1, True, 2, 0], 3,
                                          tampered, -1))
        ve(lambda: weighted_sample_resume(list("abcd"),
                                          [1, -1, 2, 0], 3,
                                          tampered, -1))
        ve(lambda: weighted_sample_resume(list("abcd"),
                                          [1, float("nan"), 2, 0], 3,
                                          tampered, -1))
        ve(lambda: weighted_sample_resume(list("abcd"),
                                          [1, 3, 2, 0], 5,
                                          tampered, -1))
        # Decimal NaN: decimal 异常不得泄漏, 统一 ValueError。
        ve(lambda: weighted_sample_resume(
            ["a"], [Decimal("NaN")], 0, tampered, -1))
        # 正权重不足仍是 ValueError, 且在产生轮次前判定。
        ve(lambda: weighted_sample_resume(
            ["a", "b"], [1, 0], 2,
            weighted_sample_checkpoint(["a", "b"], [1, 0], 1), 3))

    def test_state_and_draws_resume_entry_rules(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        # 采样输入本身合法时, state 映射检查先于 draws 之外的状态结构。
        for bad_state in (None, [], "{}", 1, True, (), {1, 2}):
            te(lambda bs=bad_state: weighted_sample_resume(
                items, weights, k, bs, 1))
        # draws 规则。
        state = weighted_sample_checkpoint(items, weights, k, 0)
        for bad in (True, False, 1.0, "1", None, [1], 1 + 0j):
            te(lambda b=bad: weighted_sample_resume(
                items, weights, k, state, b))
        ve(lambda: weighted_sample_resume(items, weights, k, state, -1))
        # 状态结构 / 版本 / 绑定仍按 ValueError。
        import copy as _copy
        for mutator in (
            lambda s: s.pop("version"),
            lambda s: s.pop("rng"),
            lambda s: s.update(extra=1),
            lambda s: s.update(digest="0" * 64),
        ):
            bad = _copy.deepcopy(state)
            mutator(bad)
            ve(lambda b=bad: weighted_sample_resume(items, weights, k, b, 1))
        bad = dict(state)
        bad["version"] = 99
        ve(lambda: weighted_sample_resume(items, weights, k, bad, 1))
        ve(lambda: weighted_sample_resume(
            list("abce"), weights, k, state, 1))
        ve(lambda: weighted_sample_resume(
            items, [1.0, 3, 2, 0], k, state, 1))

    def test_no_partial_rounds_on_error(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, 0)
        bad = dict(state)
        bad["position"] = 10 ** 9  # 未重算摘要 -> digest 失配
        with self.assertRaises(ValueError):
            weighted_sample_resume(items, weights, k, bad, 5)
        with self.assertRaises(ValueError):
            weighted_sample_resume(items, weights, k, state, -5)

    def test_does_not_mutate_inputs_or_state(self):
        items, weights = list("abcd"), [1, 3, 2, 0]
        items_snap, weights_snap = list(items), list(weights)
        state = weighted_sample_checkpoint(items, weights, 3, 42, start=2)
        import copy
        state_snap = copy.deepcopy(state)
        weighted_sample_resume(items, weights, 3, state, 4)
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)
        self.assertEqual(state, state_snap)


class WeightedSampleExcludingCheckpointTest(unittest.TestCase):
    """排除采样会话的断点/恢复入口:
    weighted_sample_excluding_checkpoint /
    weighted_sample_excluding_resume_indices / weighted_sample_excluding_resume。"""

    CASES = [
        (list("abcdef"), [1, 3, 2, 5, 0, 2], 3, [1, 4]),
        (list(range(20)), [10 ** 80 + i for i in range(20)], 8, [0, 5, 19]),
        (["p", "q", "r"], [0.5, 1.5, 2.0], 2, [2]),
        (list("xyz"), [10 ** 100, 1, 10 ** 50], 2, [0]),
        (["p", "q", "r"], [2, Fraction(1), 0.5], 2, [1]),
        (["a", "b", "c", "d"],
         [Decimal("1.5"), Decimal("0.5"), Decimal("2"), Decimal("0")], 3, [3]),
        (["a", "b", "c"], [1, 0, 1], 1, []),
        ([1, 1, 1, 1], [1, 1, 1, 1], 3, [2]),
    ]

    def test_resume_rounds_equal_batch_excluding_window(self):
        # 从断点继续的每一轮都等于批量排除入口对应零基区间。
        for items, weights, k, excluded in self.CASES:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", True):
                for start in (0, 1, 3):
                    with self.subTest(k=k, seed=seed, start=start):
                        total = start + 9
                        full = weighted_sample_many_excluding_indices(
                            items, weights, k, excluded, total, seed
                        )
                        state = weighted_sample_excluding_checkpoint(
                            items, weights, k, excluded, seed, start
                        )
                        rounds, next_state = (
                            weighted_sample_excluding_resume_indices(
                                items, weights, k, excluded, state, 9
                            )
                        )
                        self.assertEqual(rounds, full[start:])
                        self.assertEqual(next_state["position"], total)

    def test_chunked_chain_equals_one_shot(self):
        # 多次续接与一次性生成逐项相同, 中途状态可经 json 往返。
        items, weights, k, excluded = (
            list("abcdef"), [1, 3, 2, 5, 0, 2], 3, [1, 4]
        )
        full = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 14, 42
        )
        state = weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 42, start=2
        )
        collected = []
        for chunk in (3, 4, 5):
            rounds, state = weighted_sample_excluding_resume_indices(
                items, weights, k, excluded, state, chunk
            )
            collected.extend(rounds)
            state = json.loads(json.dumps(state))
        self.assertEqual(collected, full[2:])
        self.assertEqual(state["position"], 14)

    def test_start_zero_first_round_matches_single_excluding_entry(self):
        for items, weights, k, excluded in self.CASES:
            with self.subTest(k=k, excluded=excluded):
                state = weighted_sample_excluding_checkpoint(
                    items, weights, k, excluded, 42
                )
                rounds, _ = weighted_sample_excluding_resume_indices(
                    items, weights, k, excluded, state, 1
                )
                self.assertEqual(
                    rounds[0],
                    weighted_sample_excluding_indices(
                        items, weights, k, excluded, 42
                    ),
                )

    def test_empty_excluded_matches_plain_checkpoint_and_resume(self):
        # excluded 为空时与普通断点/恢复入口逐项一致。
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 4
        for seed in (0, 7, 42, "s"):
            with self.subTest(seed=seed):
                plain_state = weighted_sample_checkpoint(
                    items, weights, k, seed, start=3
                )
                excl_state = weighted_sample_excluding_checkpoint(
                    items, weights, k, [], seed, start=3
                )
                self.assertEqual(excl_state["position"], 3)
                self.assertEqual(excl_state["excluded"], [])
                # RNG 快照与位置一致(仅多了 excluded 字段与不同摘要绑定)。
                self.assertEqual(excl_state["rng"], plain_state["rng"])
                excl_rounds, _ = weighted_sample_excluding_resume_indices(
                    items, weights, k, [], excl_state, 5
                )
                plain_rounds, _ = weighted_sample_resume_indices(
                    items, weights, k, plain_state, 5
                )
                self.assertEqual(excl_rounds, plain_rounds)
                self.assertEqual(
                    excl_rounds,
                    weighted_sample_many_indices(items, weights, k, 5, seed,
                                                 start=3),
                )

    def test_excluded_set_semantics_give_identical_state_and_rounds(self):
        # 重复位置与排列顺序不影响断点状态与恢复结果。
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 3
        state_a = weighted_sample_excluding_checkpoint(
            items, weights, k, [1, 4], 42, start=2
        )
        state_b = weighted_sample_excluding_checkpoint(
            items, weights, k, [4, 1, 1, 4], 42, start=2
        )
        self.assertEqual(state_a, state_b)
        self.assertEqual(state_a["excluded"], [1, 4])
        rounds_a, _ = weighted_sample_excluding_resume_indices(
            items, weights, k, [1, 4], state_a, 6
        )
        rounds_b, _ = weighted_sample_excluding_resume_indices(
            items, weights, k, (4, 1), state_b, 6
        )
        self.assertEqual(rounds_a, rounds_b)

    def test_excluded_positions_never_appear(self):
        items, weights, k = list("abcdef"), [1, 3, 2, 5, 0, 2], 3
        state = weighted_sample_excluding_checkpoint(
            items, weights, k, [0, 2, 4], 7, start=4
        )
        rounds, _ = weighted_sample_excluding_resume_indices(
            items, weights, k, [4, 0, 2], state, 60
        )
        for rd in rounds:
            self.assertEqual(len(rd), 3)
            self.assertEqual(len(set(rd)), 3)
            self.assertTrue(all(i in (1, 3, 5) for i in rd))

    def test_draws_zero_returns_empty_and_unchanged_state_copy(self):
        items, weights, k, excluded = list("abcd"), [1, 3, 2, 0], 2, [1]
        state = weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 7, start=5
        )
        rounds, next_state = weighted_sample_excluding_resume_indices(
            items, weights, k, excluded, state, 0
        )
        self.assertEqual(rounds, [])
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)
        # 用返回的状态继续与直接从原状态继续逐轮一致。
        more, _ = weighted_sample_excluding_resume_indices(
            items, weights, k, excluded, next_state, 2
        )
        self.assertEqual(
            more,
            weighted_sample_many_excluding_indices(
                items, weights, k, excluded, 2, 7, start=5
            ),
        )
        self.assertEqual(state["position"], 5)

    def test_k_zero_empty_rounds_advance_position_without_rng(self):
        for items, weights, excluded in (
            ([], [], []),
            (["a", "b"], [1, 2], [0]),
            (["a"], [0], []),
            (["a"], [1], [0]),
        ):
            state = weighted_sample_excluding_checkpoint(
                items, weights, 0, excluded, 0
            )
            rng_before = state["rng"]
            rounds, next_state = weighted_sample_excluding_resume_indices(
                items, weights, 0, excluded, state, 4
            )
            self.assertEqual(rounds, [[], [], [], []])
            self.assertEqual(next_state["position"], 4)
            # 不消耗随机流: RNG 快照与创建时一致。
            self.assertEqual(next_state["rng"], rng_before)

    def test_value_resume_matches_index_resume_and_next_state(self):
        # 值入口每轮是索引轮次的逐项映射, 下一状态逐字段一致。
        for items, weights, k, excluded in self.CASES:
            for seed in (0, 42, "s"):
                with self.subTest(k=k, seed=seed):
                    state = weighted_sample_excluding_checkpoint(
                        items, weights, k, excluded, seed, start=2
                    )
                    idx_rounds, idx_next = (
                        weighted_sample_excluding_resume_indices(
                            items, weights, k, excluded, state, 7
                        )
                    )
                    val_rounds, val_next = weighted_sample_excluding_resume(
                        items, weights, k, excluded,
                        json.loads(json.dumps(state)), 7,
                    )
                    self.assertEqual(
                        val_rounds,
                        [[items[i] for i in rd] for rd in idx_rounds],
                    )
                    self.assertEqual(val_next, idx_next)

    def test_value_resume_equals_batch_values_window(self):
        items, weights, k, excluded = (
            list("abcdef"), [1, 3, 2, 5, 0, 2], 3, [1, 4]
        )
        state = weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 42, start=3
        )
        rounds, next_state = weighted_sample_excluding_resume(
            items, weights, k, excluded, state, 5
        )
        self.assertEqual(
            rounds,
            weighted_sample_many_excluding(
                items, weights, k, excluded, 8, 42
            )[3:],
        )
        self.assertEqual(next_state["position"], 8)

    def test_state_is_json_native_and_survives_metrics_roundtrip(self):
        items, weights, k, excluded = (
            ["p", "q", "r", "s"], [2, Fraction(1), 0.5, 0], 2, [3]
        )
        state = weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 42, start=2
        )
        self.assertEqual(state["version"], 1)
        self.assertEqual(state["position"], 2)
        self.assertEqual(state["k"], 2)
        self.assertEqual(state["n"], 4)
        self.assertEqual(state["excluded"], [3])
        for key in ("items_digest", "weights_digest", "seed", "exact",
                    "rng", "digest"):
            self.assertIn(key, state)
        # allow_nan=False: 若状态含 NaN/Infinity 会直接失败。
        text = json.dumps(state, allow_nan=False)
        rounds, next_state = weighted_sample_excluding_resume_indices(
            items, weights, k, excluded, json.loads(text), 4
        )
        self.assertEqual(
            rounds,
            weighted_sample_many_excluding_indices(
                items, weights, k, excluded, 4, 42, start=2
            ),
        )
        # serialize_metrics / deserialize_metrics 往返后仍可继续恢复。
        restored = deserialize_metrics(serialize_metrics(next_state))
        more, _ = weighted_sample_excluding_resume_indices(
            items, weights, k, excluded, restored, 2
        )
        self.assertEqual(
            more,
            weighted_sample_many_excluding_indices(
                items, weights, k, excluded, 2, 42, start=6
            ),
        )
        # 值入口同样接受还原后的状态。
        vrounds, _ = weighted_sample_excluding_resume(
            items, weights, k, excluded,
            deserialize_metrics(serialize_metrics(state)), 3,
        )
        self.assertEqual(vrounds, [[items[i] for i in rd] for rd in
                                   rounds[:3]])

    def test_checkpoint_validation_and_error_categories(self):
        items, weights, k, excluded = list("abcd"), [1, 3, 2, 0], 2, [1]

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        te(lambda: weighted_sample_excluding_checkpoint(
            "abcd", weights, k, excluded, 0))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, iter(weights), k, excluded, 0))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, weights, True, excluded, 0))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, object()))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, "12", 0))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, [1.0], 0))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, [True], 0))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 0, True))
        te(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 0, 1.0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, [4], 0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, [-1], 0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, weights, 5, excluded, 0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, weights, -1, excluded, 0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, [1, -1, 2, 0], 1, excluded, 0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, [1, float("nan"), 2, 0], 1, excluded, 0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 0, -1))
        # 未排除位置的正权重不足。
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, weights, 2, [0, 1, 2], 0))
        ve(lambda: weighted_sample_excluding_checkpoint(
            items, weights, 1, [0, 1, 2], 0))

    def test_resume_state_and_input_error_categories(self):
        items, weights, k, excluded = list("abcd"), [1, 3, 2, 0], 2, [1]
        state = weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 0
        )

        def te(fn):
            with self.assertRaises(TypeError):
                fn()

        def ve(fn):
            with self.assertRaises(ValueError):
                fn()

        # 非映射状态。
        for bad in (None, [], "{}", 1, True, (), {1, 2}):
            te(lambda b=bad: weighted_sample_excluding_resume_indices(
                items, weights, k, excluded, b, 1))
            te(lambda b=bad: weighted_sample_excluding_resume(
                items, weights, k, excluded, b, 1))
        # excluded 结构或成员类型错误。
        te(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, "12", state, 1))
        te(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, [1.0], state, 1))
        te(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, [True], state, 1))
        # excluded 越界。
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, [4], state, 1))
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, [-1], state, 1))
        # draws 规则。
        for bad in (True, 1.0, "1", None, [1]):
            te(lambda b=bad: weighted_sample_excluding_resume_indices(
                items, weights, k, excluded, state, b))
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, excluded, state, -1))
        # 状态结构 / 版本 / 摘要 / 绑定。
        import copy as _copy
        for mutator in (
            lambda s: s.pop("excluded"),
            lambda s: s.pop("version"),
            lambda s: s.pop("rng"),
            lambda s: s.update(extra=1),
            lambda s: s.update(excluded=[1, 1]),
            lambda s: s.update(excluded=[2, 1]),
            lambda s: s.update(excluded="1"),
            lambda s: s.update(excluded=[True]),
            lambda s: s.update(position=-1),
            lambda s: s.update(digest="0" * 64),
        ):
            bad = _copy.deepcopy(state)
            mutator(bad)
            ve(lambda b=bad: weighted_sample_excluding_resume_indices(
                items, weights, k, excluded, b, 1))
        bad = dict(state)
        bad["version"] = 2
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, excluded, bad, 1))
        # 状态与输入不匹配(含 excluded 集合不同)。
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, [2], state, 1))
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, weights, k, [1, 2], state, 1))
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, weights, 1, excluded, state, 1))
        ve(lambda: weighted_sample_excluding_resume_indices(
            list("abce"), weights, k, excluded, state, 1))
        ve(lambda: weighted_sample_excluding_resume_indices(
            items, [1.0, 3, 2, 0], k, excluded, state, 1))
        # 值入口同样的错误分类。
        te(lambda: weighted_sample_excluding_resume(
            items, weights, k, excluded, None, 1))
        ve(lambda: weighted_sample_excluding_resume(
            items, weights, k, excluded, bad, 1))

    def test_no_partial_rounds_on_error(self):
        items, weights, k, excluded = list("abcd"), [1, 3, 2, 0], 2, [1]
        state = weighted_sample_excluding_checkpoint(
            items, weights, k, excluded, 0
        )
        bad = dict(state)
        bad["position"] = 10 ** 9  # 未重算摘要 -> digest 失配
        with self.assertRaises(ValueError):
            weighted_sample_excluding_resume_indices(
                items, weights, k, excluded, bad, 5
            )
        with self.assertRaises(ValueError):
            weighted_sample_excluding_resume_indices(
                items, weights, k, excluded, state, -5
            )

    def test_does_not_mutate_inputs_or_state(self):
        items, weights, excluded = list("abcd"), [1, 3, 2, 0], [1]
        items_snap, weights_snap = list(items), list(weights)
        state = weighted_sample_excluding_checkpoint(
            items, weights, 2, excluded, 42, start=2
        )
        import copy
        state_snap = copy.deepcopy(state)
        weighted_sample_excluding_resume_indices(
            items, weights, 2, excluded, state, 4
        )
        weighted_sample_excluding_resume(
            items, weights, 2, excluded, state, 3
        )
        self.assertEqual(items, items_snap)
        self.assertEqual(weights, weights_snap)
        self.assertEqual(excluded, [1])
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


class DeserializeMetricsTest(unittest.TestCase):
    """deserialize_metrics: 指标序列化文本的精确还原入口。"""

    # ------------------------------------------------------------------
    # 参数类型: 只接受 str
    # ------------------------------------------------------------------
    def test_non_str_raises_type_error(self):
        for bad in (b"1", bytearray(b"1"), 1, 1.5, None, True, False,
                    [], {}, object(), Decimal("1")):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaises(TypeError):
                    deserialize_metrics(bad)

    def test_str_and_str_subclass_accepted(self):
        class WeirdStr(str):
            pass

        self.assertEqual(deserialize_metrics("1"), 1)
        self.assertEqual(deserialize_metrics(WeirdStr('{"a": 1}')), {"a": 1})

    # ------------------------------------------------------------------
    # JSON 结构还原: null / bool / str / list / dict
    # ------------------------------------------------------------------
    def test_scalar_values(self):
        self.assertIs(deserialize_metrics("null"), None)
        self.assertIs(deserialize_metrics("true"), True)
        self.assertIs(deserialize_metrics("false"), False)
        self.assertEqual(deserialize_metrics('"文本"'), "文本")
        self.assertEqual(deserialize_metrics("0"), 0)
        self.assertEqual(deserialize_metrics("-7"), -7)

    def test_empty_object_and_array(self):
        self.assertEqual(deserialize_metrics("{}"), {})
        self.assertEqual(deserialize_metrics("[]"), [])
        self.assertEqual(deserialize_metrics('{"a": {}, "b": []}'),
                         {"a": {}, "b": []})
        self.assertEqual(deserialize_metrics("[{}, []]"), [{}, []])

    def test_whitespace_and_unicode_escapes(self):
        self.assertEqual(
            deserialize_metrics('  {\n\t "a" : [ 1 , 2 ] }\r\n '),
            {"a": [1, 2]},
        )
        self.assertEqual(deserialize_metrics('"\\u00e9"'), "é")
        self.assertEqual(deserialize_metrics('"\\ud83d\\ude00"'), "\U0001F600")
        self.assertEqual(deserialize_metrics('{"\\u0061": 1}'), {"a": 1})

    def test_deep_nesting_arrays_and_objects(self):
        depth = 200
        text = "[" * depth + "1" + "]" * depth
        value = deserialize_metrics(text)
        for _ in range(depth):
            self.assertIsInstance(value, list)
            value = value[0]
        self.assertEqual(value, 1)
        obj_text = '{"k":' * depth + "1" + "}" * depth
        value = deserialize_metrics(obj_text)
        for _ in range(depth):
            self.assertIsInstance(value, dict)
            value = value["k"]
        self.assertEqual(value, 1)

    def test_duplicate_values_preserved(self):
        self.assertEqual(deserialize_metrics("[1,1,1]"), [1, 1, 1])
        self.assertEqual(deserialize_metrics('["a","a",2,2]'),
                         ["a", "a", 2, 2])

    def test_member_names_stay_text_and_keep_text_order(self):
        # 成员名一律为 str, 保持文本中的先后次序; 不按数值解释。
        value = deserialize_metrics('{"2":"a","10":"b","名":"c"}')
        self.assertEqual(list(value), ["2", "10", "名"])
        self.assertTrue(all(isinstance(k, str) for k in value))

    # ------------------------------------------------------------------
    # 数字: 完全绕开浮点
    # ------------------------------------------------------------------
    def test_plain_numbers_become_arbitrary_precision_int(self):
        for text in ("0", "-0", "7", "-13", "9007199254740993"):
            value = deserialize_metrics(text)
            self.assertIs(type(value), int)
            self.assertEqual(value, int(text))
        # 没有小数点/指数标记: 即使文本形如 -0 也按整数规则还原。
        self.assertEqual(deserialize_metrics("-0"), 0)

    def test_marked_numbers_become_decimal_preserving_form(self):
        # 带小数点或指数标记: Decimal, 保留正负号、刻度、指数与负零。
        for text in ("1.50", "-0.0", "-0.00", "0.0", "0E3", "-0E-3",
                     "1E+2", "1e2", "2.500e-3", "1.5E4", "10.0", "-1E-100"):
            with self.subTest(text=text):
                value = deserialize_metrics(text)
                self.assertIs(type(value), Decimal)
                self.assertEqual(str(value), str(Decimal(text)))

    def test_decimal_negative_zero_and_integral_values(self):
        value = deserialize_metrics("-0.00")
        self.assertIsInstance(value, Decimal)
        self.assertTrue(value.is_signed())
        self.assertEqual(value, 0)
        # 数值恰为整数但带标记: 仍是 Decimal 且保留刻度/指数形式。
        self.assertEqual(str(deserialize_metrics("1E+2")), "1E+2")
        self.assertEqual(str(deserialize_metrics("2.0")), "2.0")

    def test_decimal_extreme_exponents_exact(self):
        for text in ("1E100000", "1E-100000", "-9.99E+9999"):
            value = deserialize_metrics(text)
            self.assertIsInstance(value, Decimal)
            self.assertEqual(str(value), str(Decimal(text)))
            # 再次序列化保持同一十进制内容。
            self.assertEqual(serialize_metrics(value), str(Decimal(text)))

    def test_huge_integers_exact_decimal(self):
        big = 10 ** 5000 - 1
        text = _unlimited_int_str(big)
        value = deserialize_metrics(text)
        self.assertIs(type(value), int)
        self.assertEqual(value, big)
        self.assertEqual(deserialize_metrics("-" + text), -big)
        # 嵌套在数组/对象中的超大整数同样精确。
        nested = deserialize_metrics('{"a":[%s,[-%s]]}' % (text, text))
        self.assertEqual(nested, {"a": [big, [-big]]})

    def test_huge_integers_when_digit_limit_lowered(self):
        import sys

        if not hasattr(sys, "set_int_max_str_digits"):
            self.skipTest("解释器没有可配置的整数转文本位数限制")
        old = sys.get_int_max_str_digits()
        self.addCleanup(sys.set_int_max_str_digits, old)
        sys.set_int_max_str_digits(640)

        big = 10 ** 5000 - 1
        reference = _unlimited_int_str(big)
        # 直接 int(reference) 会触发位数限制; 反序列化必须绕过且精确。
        value = deserialize_metrics(reference)
        self.assertEqual(value, big)
        self.assertEqual(deserialize_metrics("[-" + reference + "]"), [-big])
        # 序列化->反序列化->序列化全链路在低位数限制下逐字一致。
        self.assertEqual(serialize_metrics(value), reference)
        # 极大/极小指数不受整数位数限制影响。
        self.assertEqual(str(deserialize_metrics("1E100000")), "1E+100000")

    def test_fraction_two_element_array_is_plain_list(self):
        # serialize_metrics 对 Fraction 写出的二元素数组没有类型标签,
        # 还原时按普通 list, 不根据形状推断类型。
        text = serialize_metrics(Fraction(3, 4))
        self.assertEqual(text, "[3,4]")
        value = deserialize_metrics(text)
        self.assertIs(type(value), list)
        self.assertEqual(value, [3, 4])
        self.assertEqual(serialize_metrics(value), "[3,4]")
        nested = deserialize_metrics(serialize_metrics({"f": Fraction(-4, 2)}))
        self.assertEqual(nested, {"f": [-2, 1]})

    # ------------------------------------------------------------------
    # 错误分类: ValueError, 且不返回部分结果
    # ------------------------------------------------------------------
    def test_non_finite_constants_raise_value_error(self):
        for bad in ("NaN", "Infinity", "-Infinity", "[NaN]",
                    '{"x": Infinity}', '[-Infinity, 1]'):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    deserialize_metrics(bad)

    def test_syntax_errors_raise_value_error(self):
        for bad in ("", " ", "{", "[", "[1,]", "{1:2}", "01", "+1", ".5",
                    "1.", "{'a':1}", "1 2", "[1] [2]", '"\\x"', '"abc',
                    '["a": 1]', '{"a" 1}', "tru", "nul"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    deserialize_metrics(bad)

    def test_duplicate_member_names_raise_value_error(self):
        for bad in ('{"a":1,"a":2}', '{"a":1,"b":2,"a":3}',
                    '{"x":{"y":1,"y":2}}', '[{"k":0,"k":1}]',
                    '{"\\u0061":1,"a":2}'):  # 转义后与文本成员名重复
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    deserialize_metrics(bad)

    def test_unrepresentable_number_raises_value_error(self):
        # 指数超出 decimal 可表示范围: 无法保持精确十进制, 统一 ValueError,
        # 且 decimal.InvalidOperation 不会泄漏。
        import decimal

        for bad in ("1E999999999999999999999999",
                    "-1E999999999999999999999999",
                    "[1E1000000000000000000]"):
            with self.subTest(bad=bad):
                try:
                    deserialize_metrics(bad)
                except ValueError:
                    pass
                except decimal.DecimalException:
                    self.fail("decimal exception leaked for %r" % bad)
                else:
                    self.fail("no ValueError for %r" % bad)

    def test_no_partial_result_on_error(self):
        # 解析要么完整成功要么整体失败: 错误深处嵌在合法前缀之后也不例外。
        for bad in ('{"ok": 1, "bad": {"x": NaN}}',
                    '[1, 2, {"a": 1, "a": 2}]',
                    '{"deep": [[[[Infinity]]]]}'):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    deserialize_metrics(bad)

    # ------------------------------------------------------------------
    # 与 serialize_metrics 的往返
    # ------------------------------------------------------------------
    def test_roundtrip_nested_metrics_exact(self):
        tree = {
            "名": [1, Decimal("1.50"), Fraction(3, 4), None, True, "值"],
            "big": 10 ** 100,
            "neg": -(10 ** 80 + 7),
            "nested": {"z": [Decimal("-0.00")], "a": {}, "e": []},
            "exp": Decimal("1E+100000"),
        }
        text = serialize_metrics(tree)
        restored = deserialize_metrics(text)
        # Fraction 按二元素 list 还原, 其余逐点相等。
        self.assertEqual(
            restored,
            {"名": [1, Decimal("1.50"), [3, 4], None, True, "值"],
             "big": 10 ** 100, "neg": -(10 ** 80 + 7),
             "nested": {"z": [Decimal("-0.00")], "a": {}, "e": []},
             "exp": Decimal("1E+100000")},
        )
        # 再次序列化: 整数与 Decimal 的十进制内容精确, 文本逐字一致。
        self.assertEqual(serialize_metrics(restored), text)

    def test_roundtrip_preserves_decimal_form_character_by_character(self):
        # 带小数点或指数标记的 Decimal(含负零)往返逐字保持; 不带标记的
        # "-0" 按规则还原为 int 0, 由整数用例覆盖。
        for literal in ("1.50", "-0.0", "-0.00", "0E3", "-0E-3", "1E+2",
                        "1E-100", "1E+100000", "123.4500"):
            with self.subTest(literal=literal):
                text = serialize_metrics(deserialize_metrics(
                    serialize_metrics(Decimal(literal))))
                self.assertEqual(text, str(Decimal(literal)))

    def test_reserialized_output_keeps_format_and_collision_rules(self):
        # 键排序、紧凑分隔符、Unicode 输出对还原后的数据继续生效。
        restored = deserialize_metrics('{"b": 1, "名": "值", "a": [2, 1.5]}')
        self.assertEqual(
            serialize_metrics(restored),
            '{"a":[2,1.5],"b":1,"名":"值"}',
        )
        # 既有成员名冲突检测对还原后的 dict 继续生效。
        restored = deserialize_metrics('{"1": "x"}')
        restored[1] = "y"  # int 键 1 与既有成员名 "1" 冲突
        with self.assertRaises(ValueError):
            serialize_metrics(restored)

    def test_deserialize_does_not_mutate_or_share_input(self):
        text = '{"a": [1, 2]}'
        first = deserialize_metrics(text)
        first["a"].append(3)
        self.assertEqual(deserialize_metrics(text), {"a": [1, 2]})
        self.assertEqual(text, '{"a": [1, 2]}')

    # ------------------------------------------------------------------
    # checkpoint 状态文本互操作
    # ------------------------------------------------------------------
    def test_checkpoint_state_roundtrip_through_deserialize(self):
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        for seed in (0, 42, 1.5, -0.0, 1e300, "s", b"s", True):
            with self.subTest(seed=seed):
                state = weighted_sample_checkpoint(items, weights, k, seed,
                                                   start=2)
                restored = deserialize_metrics(serialize_metrics(state))
                rounds, next_state = weighted_sample_resume_indices(
                    items, weights, k, restored, 3
                )
                self.assertEqual(
                    rounds,
                    weighted_sample_many_indices(items, weights, k, 3, seed,
                                                 start=2),
                )
                # 链式: 下一状态再次序列化/还原后仍可继续推进。
                more, _ = weighted_sample_resume_indices(
                    items, weights, k,
                    deserialize_metrics(serialize_metrics(next_state)), 2,
                )
                self.assertEqual(
                    more,
                    weighted_sample_many_indices(items, weights, k, 2, seed,
                                                 start=5),
                )
                # 按值恢复入口同样接受还原后的状态。
                vrounds, _ = weighted_sample_resume(
                    items, weights, k,
                    deserialize_metrics(serialize_metrics(state)), 3,
                )
                self.assertEqual(
                    vrounds, [[items[i] for i in rd] for rd in rounds]
                )

    def test_checkpoint_restored_state_matches_json_native_path(self):
        # 同一状态文本经 json.loads 与 deserialize_metrics 还原后,
        # 恢复结果与下一状态完全一致(可互换)。
        import json as _json

        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        for seed in (0, 1.5, 1e300):
            with self.subTest(seed=seed):
                state = weighted_sample_checkpoint(items, weights, k, seed,
                                                   start=1)
                text = serialize_metrics(state)
                rounds_j, next_j = weighted_sample_resume_indices(
                    items, weights, k, _json.loads(text), 2
                )
                rounds_d, next_d = weighted_sample_resume_indices(
                    items, weights, k, deserialize_metrics(text), 2
                )
                self.assertEqual(rounds_j, rounds_d)
                self.assertEqual(next_j, next_d)

    def test_checkpoint_state_none_seed_snapshot_is_deterministic(self):
        # seed=None 的断点快照经还原后, 从同一文本恢复多次结果一致。
        items, weights, k = list("abcd"), [1, 3, 2, 0], 3
        state = weighted_sample_checkpoint(items, weights, k, None, start=2)
        text = serialize_metrics(state)
        first, _ = weighted_sample_resume_indices(
            items, weights, k, deserialize_metrics(text), 3
        )
        second, _ = weighted_sample_resume_indices(
            items, weights, k, deserialize_metrics(text), 3
        )
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)

    # ------------------------------------------------------------------
    # 既有入口行为不受新入口影响
    # ------------------------------------------------------------------
    def test_existing_entries_unchanged(self):
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            serialize_metrics({"名": "值", "x": [1, 2]}),
            '{"x":[1,2],"名":"值"}',
        )
        self.assertEqual(serialize_metrics({"n": 10 ** 100}),
                         '{"n":1' + "0" * 100 + "}")
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a", "b"], [1, True], 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a", "b"], [1, -1], 1, 0)


class WeightedSampleExcludingTest(unittest.TestCase):
    """按原始位置排除的单轮入口 weighted_sample_excluding(_indices)。"""

    def test_empty_excluded_matches_single_entries_exactly(self):
        # excluded 为空(默认)时必须与现有单轮入口逐项相同。
        cases = [
            (["red", "green", "blue"], [1, 3, 2], 2),
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
            (["p", "q"], [0.5, 1.5], 2),
            (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
            (["a", "b"], [10 ** 400, 10 ** 400], 2),
            (["p", "q", "r"], [2, Fraction(1), 0.5], 3),
            (["a", "b", "c"], [Decimal("1.5"), Decimal("0.5"), Decimal("2")], 3),
            (["a", "b", "c"], [1e308, 1e308, 1.0], 3),
            ([], [], 0),
            (["a", "b"], [0, 0], 0),
        ]
        for items, weights, k in cases:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                with self.subTest(items=items, k=k, seed=seed):
                    self.assertEqual(
                        weighted_sample_excluding_indices(items, weights, k, (), seed),
                        weighted_sample_indices(items, weights, k, seed),
                    )
                    self.assertEqual(
                        weighted_sample_excluding_indices(items, weights, k, seed=seed),
                        weighted_sample_indices(items, weights, k, seed),
                    )
                    self.assertEqual(
                        weighted_sample_excluding(items, weights, k, (), seed),
                        weighted_sample(items, weights, k, seed),
                    )

    def test_excluded_positions_never_appear(self):
        # 排除位置即使权重为正(甚至独占几乎全部权重)也绝不出现。
        items = list("abcdef")
        weights = [10 ** 100, 1, 10 ** 99, 3, 5, 7]
        for seed in range(100):
            idx = weighted_sample_excluding_indices(
                items, weights, 3, (0, 2), seed
            )
            self.assertEqual(len(idx), 3)
            self.assertEqual(len(set(idx)), 3)
            self.assertTrue(all(0 <= i < 6 for i in idx))
            self.assertNotIn(0, idx)
            self.assertNotIn(2, idx)

    def test_only_remaining_positive_position_is_chosen(self):
        for seed in range(50):
            self.assertEqual(
                weighted_sample_excluding_indices(
                    ["x", "y", "z"], [5, 1, 5], 1, (0, 2), seed
                ),
                [1],
            )

    def test_zero_weight_still_never_chosen(self):
        # 未排除的零权重位置仍永不入选(含带符号 Decimal 零)。
        for seed in range(60):
            self.assertEqual(
                weighted_sample_excluding_indices(
                    ["x", "y", "z"], [0, 5, 0], 1, (2,), seed
                ),
                [1],
            )
            self.assertEqual(
                weighted_sample_excluding_indices(
                    ["x", "y"], [Decimal("-0"), Decimal("5")], 1, (), seed
                ),
                [1],
            )

    def test_excluded_set_semantics_duplicates_and_order(self):
        # 重复成员与排列顺序不影响结果(集合语义)。
        items = list("abcdef")
        weights = [1, 2, 3, 4, 5, 6]
        base = weighted_sample_excluding_indices(items, weights, 3, (1, 3), 7)
        for excluded in ((1, 3), (3, 1), (1, 1, 3), (3, 1, 3, 1), [1, 3],
                         [3, 1, 1, 3]):
            with self.subTest(excluded=excluded):
                self.assertEqual(
                    weighted_sample_excluding_indices(
                        items, weights, 3, excluded, 7
                    ),
                    base,
                )
                self.assertEqual(
                    weighted_sample_excluding(items, weights, 3, excluded, 7),
                    [items[i] for i in base],
                )

    def test_values_entry_corresponds_to_indices_entry(self):
        cases = [
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4, (0, 4)),
            ([1, 1, 1, 1], [1, 1, 1, 1], 3, (2,)),
            (["p", "q", "r"], [2, Fraction(1), 0.5], 2, (0,)),
            (["a", "b", "c"], [Decimal("1.5"), Decimal("0.5"), 2], 2, (2,)),
            (list("xyz"), [10 ** 100, 1, 10 ** 50], 2, (0,)),
        ]
        for items, weights, k, excluded in cases:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", True):
                with self.subTest(items=items, excluded=excluded, seed=seed):
                    idx = weighted_sample_excluding_indices(
                        items, weights, k, excluded, seed
                    )
                    self.assertEqual(
                        weighted_sample_excluding(
                            items, weights, k, excluded, seed
                        ),
                        [items[i] for i in idx],
                    )

    def test_duplicate_values_distinct_positions(self):
        # 相同值仍按位置独立; 排除一个位置后其余位置各自独立。
        idx = weighted_sample_excluding_indices([1, 1, 1, 1], [1, 1, 1, 1], 3, (1,), 5)
        self.assertEqual(sorted(idx), [0, 2, 3])
        self.assertEqual(
            weighted_sample_excluding([1, 1, 1, 1], [1, 1, 1, 1], 3, (1,), 5),
            [1, 1, 1],
        )

    def test_same_seed_same_result(self):
        args = (["a", "b", "c", "d"], [1, 2, 3, 4], 2, (0, 3))
        first = weighted_sample_excluding_indices(*args, seed=99)
        first_v = weighted_sample_excluding(*args, seed=99)
        for _ in range(5):
            self.assertEqual(
                weighted_sample_excluding_indices(*args, seed=99), first
            )
            self.assertEqual(weighted_sample_excluding(*args, seed=99), first_v)

    def test_seed_none_keeps_random_semantics(self):
        idx = weighted_sample_excluding_indices(
            list(range(20)), list(range(1, 21)), 8, (0, 1, 2, 3), None
        )
        self.assertEqual(len(idx), 8)
        self.assertEqual(len(set(idx)), 8)
        self.assertTrue(all(4 <= i < 20 for i in idx))
        vals = weighted_sample_excluding(
            list(range(20)), list(range(1, 21)), 8, (0, 1, 2, 3), None
        )
        self.assertEqual(len(vals), 8)

    def test_k_zero_returns_empty_after_full_validation(self):
        self.assertEqual(
            weighted_sample_excluding_indices(["a", "b"], [1, 2], 0, (0, 1), 0),
            [],
        )
        self.assertEqual(
            weighted_sample_excluding(["a", "b"], [1, 2], 0, (0, 1), 0), []
        )
        self.assertEqual(
            weighted_sample_excluding_indices([], [], 0, (), 0), []
        )
        # k=0 仍完成 items/weights/k/seed 与 excluded 的全部校验。
        with self.assertRaises(ValueError):
            weighted_sample_excluding_indices(["a"], [float("nan")], 0, (), 0)
        with self.assertRaises(TypeError):
            weighted_sample_excluding_indices(["a"], [True], 0, (), 0)
        with self.assertRaises(TypeError):
            weighted_sample_excluding_indices("ab", [1, 2], 0, (), 0)
        with self.assertRaises(TypeError):
            weighted_sample_excluding_indices(["a"], [1], 0, (True,), 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_indices(["a"], [1], 0, (1,), 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding(["a"], [1], 0, (-1,), 0)

    def test_excluded_structure_validation(self):
        # excluded 必须是非文本且长度可确定的序列, 否则 TypeError。
        for bad in ("01", b"01", bytearray(b"01"), {0, 1}, {0: "a"},
                    iter([0]), 3, None, object()):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_excluding_indices(
                        ["a", "b"], [1, 2], 1, bad, 0
                    )
                with self.assertRaises(TypeError):
                    weighted_sample_excluding(["a", "b"], [1, 2], 1, bad, 0)

    def test_excluded_member_type_validation(self):
        # 成员必须是非布尔整数, 否则 TypeError。
        for bad_member in (True, False, 1.0, 0.0, "1", None, [0],
                           Fraction(1, 2), Decimal("1"), 1 + 0j):
            with self.subTest(bad_member=bad_member):
                with self.assertRaises(TypeError):
                    weighted_sample_excluding_indices(
                        ["a", "b"], [1, 2], 1, (0, bad_member), 0
                    )
                with self.assertRaises(TypeError):
                    weighted_sample_excluding(
                        ["a", "b"], [1, 2], 1, (bad_member,), 0
                    )

    def test_excluded_out_of_range_raises_value_error(self):
        for bad_excluded in ((2,), (-1,), (0, 5), (10 ** 100,), (-(10 ** 100),)):
            with self.subTest(bad_excluded=bad_excluded):
                with self.assertRaises(ValueError):
                    weighted_sample_excluding_indices(
                        ["a", "b"], [1, 2], 1, bad_excluded, 0
                    )
                with self.assertRaises(ValueError):
                    weighted_sample_excluding(
                        ["a", "b"], [1, 2], 1, bad_excluded, 0
                    )
        # 空 items 不接受任何排除位置。
        with self.assertRaises(ValueError):
            weighted_sample_excluding_indices([], [], 0, (0,), 0)

    def test_sample_input_validation_runs_before_excluded(self):
        # 先完成与现有采样入口一致的校验, 再校验 excluded: 两类错误同时
        # 存在时, 采样入口的异常类别优先出现。
        with self.assertRaises(TypeError):  # items 非序列先于 excluded 越界
            weighted_sample_excluding_indices("ab", [1, 2], 1, (9,), 0)
        with self.assertRaises(TypeError):  # k 类型错误先于 excluded 类型错误
            weighted_sample_excluding_indices(["a"], [1], True, (True,), 0)
        with self.assertRaises(TypeError):  # seed 类型错误
            weighted_sample_excluding_indices(["a"], [1], 1, (), object())
        with self.assertRaises(ValueError):  # 权重取值错误先于 excluded 越界
            weighted_sample_excluding_indices(["a", "b"], [1, -1], 1, (9,), 0)
        with self.assertRaises(ValueError):  # k 越界先于 excluded 越界
            weighted_sample_excluding_indices(["a"], [1], 2, (9,), 0)
        with self.assertRaises(ValueError):  # 长度不一致
            weighted_sample_excluding_indices(["a", "b"], [1], 1, (), 0)
        with self.assertRaises(TypeError):  # 布尔权重
            weighted_sample_excluding_indices(["a", "b"], [1, True], 1, (), 0)
        with self.assertRaises(ValueError):  # 无穷权重
            weighted_sample_excluding_indices(
                ["a", "b"], [1, float("inf")], 1, (), 0
            )
        with self.assertRaises(ValueError):  # Decimal NaN
            weighted_sample_excluding_indices(["a"], [Decimal("NaN")], 0, (), 0)

    def test_insufficient_remaining_positions_raises_before_result(self):
        # 请求正数但未排除位置中的有效正权重不足: 在产生结果前抛 ValueError。
        with self.assertRaises(ValueError):  # 全部正权重位置被排除
            weighted_sample_excluding_indices(["a", "b"], [1, 0], 1, (0,), 0)
        with self.assertRaises(ValueError):  # 剩余正权重个数小于 k
            weighted_sample_excluding_indices(
                ["a", "b", "c"], [1, 1, 0], 2, (0,), 0
            )
        with self.assertRaises(ValueError):  # 全部位置被排除
            weighted_sample_excluding_indices(["a", "b"], [1, 2], 1, (0, 1), 0)
        with self.assertRaises(ValueError):  # 权重全零且未排除
            weighted_sample_excluding_indices(["a", "b"], [0, 0], 1, (), 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding(["a", "b"], [1, 0], 1, (0,), 0)
        with self.assertRaises(ValueError):  # 精确路径同样前置失败
            weighted_sample_excluding_indices(
                ["a", "b", "c"], [10 ** 100, 0, 1], 2, (0, 2), 0
            )
        # 排除零权重位置不影响可行性。
        self.assertEqual(
            weighted_sample_excluding_indices(["a", "b"], [1, 0], 1, (1,), 0),
            [0],
        )

    def test_inputs_not_mutated(self):
        items = ["a", "b", "c", "d"]
        weights = [1, 2, 3, 4]
        excluded = [0, 2]
        snapshots = (list(items), list(weights), list(excluded))
        weighted_sample_excluding_indices(items, weights, 2, excluded, 5)
        weighted_sample_excluding(items, weights, 2, excluded, 5)
        self.assertEqual((items, weights, excluded), snapshots)

    def test_exact_paths_supported(self):
        # 超大整数 / Fraction / Decimal / 浮点溢出路径在排除入口下仍确定。
        cases = [
            (["a", "b", "c"], [10 ** 400, 10 ** 400, 1], 2, (2,)),
            (["H", "t", "z"], [10 ** 100, Decimal("1E-100"), Decimal("-0")],
             1, (0,)),
            (["a", "b", "c"], [1e308, 1e308, 1.0], 2, (2,)),
            (["a", "b", "c"], [9, Fraction(1, 100), 3], 1, (2,)),
            (["p", "q", "r", "s"], [2, Fraction(1), 0.5, Decimal("0.25")],
             3, (1,)),
        ]
        for items, weights, k, excluded in cases:
            for seed in (0, 7, 2316):
                with self.subTest(items=items, excluded=excluded, seed=seed):
                    idx = weighted_sample_excluding_indices(
                        items, weights, k, excluded, seed
                    )
                    self.assertEqual(
                        idx,
                        weighted_sample_excluding_indices(
                            items, weights, k, excluded, seed
                        ),
                    )
                    self.assertEqual(len(idx), k)
                    self.assertEqual(len(set(idx)), k)
                    self.assertTrue(all(0 <= i < len(items) for i in idx))
                    self.assertTrue(all(i not in excluded for i in idx))
                    self.assertEqual(
                        weighted_sample_excluding(
                            items, weights, k, excluded, seed
                        ),
                        [items[i] for i in idx],
                    )

    def test_proportions_follow_remaining_weights(self):
        # 排除最大权重位置后, 剩余位置仍按权重比例被选中。
        weights = [10 ** 100, 1, 3]
        counts = [0, 0]
        trials = 4000
        for seed in range(trials):
            idx = weighted_sample_excluding_indices(
                ["a", "b", "c"], weights, 1, (0,), seed
            )
            self.assertNotIn(0, idx)
            counts[idx[0] - 1] += 1
        self.assertAlmostEqual(counts[0] / trials, 1 / 4, delta=0.04)
        self.assertAlmostEqual(counts[1] / trials, 3 / 4, delta=0.04)

    def test_results_feed_serialize_metrics_without_float(self):
        # 新入口的索引与元素值可直接交给 serialize_metrics, 不经过浮点。
        idx = weighted_sample_excluding_indices(
            list(range(6)), [10 ** 100, 1, 2, 3, 4, 5], 3, (0,), 42
        )
        text = serialize_metrics({"indices": idx})
        self.assertEqual(deserialize_metrics(text), {"indices": idx})
        items = [Decimal("1.5"), Fraction(1, 3), 10 ** 100, "x"]
        vals = weighted_sample_excluding(items, [1, 1, 1, 1], 3, (3,), 7)
        text = serialize_metrics({"values": vals})
        self.assertEqual(
            deserialize_metrics(text)["values"],
            [Decimal("1.5"), [1, 3], 10 ** 100],
        )

    def test_both_entries_share_validation_and_error_classes(self):
        # 两个入口对同一批非法输入给出完全一致的异常类别。
        bad_calls = [
            ("ab", [1, 2], 1, (), 0),
            (["a", "b"], [1, "x"], 1, (), 0),
            (["a", "b"], [1, True], 1, (), 0),
            (["a"], [1], True, (), 0),
            (["a"], [1], 1, (), object()),
            (["a", "b"], [1, -1], 1, (), 0),
            (["a", "b"], [1, float("nan")], 1, (), 0),
            (["a", "b"], [1, float("inf")], 1, (), 0),
            (["a", "b"], [1], 1, (), 0),
            (["a"], [1], 2, (), 0),
            (["a"], [1], -1, (), 0),
            (["a", "b"], [1, 2], 1, "01", 0),
            (["a", "b"], [1, 2], 1, {0}, 0),
            (["a", "b"], [1, 2], 1, (True,), 0),
            (["a", "b"], [1, 2], 1, (1.0,), 0),
            (["a", "b"], [1, 2], 1, (2,), 0),
            (["a", "b"], [1, 2], 1, (-1,), 0),
            (["a", "b"], [1, 0], 1, (0,), 0),
            (["a", "b"], [0, 0], 1, (), 0),
        ]
        for args in bad_calls:
            with self.subTest(args=args):
                categories = []
                for entry in (weighted_sample_excluding_indices,
                              weighted_sample_excluding):
                    try:
                        entry(*args)
                    except (TypeError, ValueError) as exc:
                        categories.append(type(exc))
                    else:
                        self.fail("no exception for %r" % (args,))
                self.assertEqual(categories[0], categories[1])

    def test_existing_entries_unchanged(self):
        # 既有入口行为不受新入口影响。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample_indices(["a", "b", "c"], [1, 3, 2], 3, 7),
            [1, 0, 2],
        )
        self.assertEqual(
            weighted_sample_many_indices(
                ["p", "q", "r"], [2, Fraction(1), 0.5], 3, 4, 42
            ),
            [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]],
        )


class WeightedSampleManyExcludingTest(unittest.TestCase):
    """批量/流式排除入口:
    weighted_sample_many_excluding(_indices) 与
    weighted_sample_stream_excluding(_indices)。"""

    CASES = [
        (list("abcdef"), [1, 3, 2, 5, 0, 2], 4, (0, 4)),
        (list(range(20)), [10 ** 80 + i for i in range(20)], 10, (2, 5, 9)),
        (["p", "q", "r"], [0.5, 1.5, 2.5], 2, (2,)),
        (list("xyz"), [10 ** 100, 1, 10 ** 50], 2, (0,)),
        (["a", "b"], [10 ** 400, 10 ** 400], 2, ()),
        (["p", "q", "r"], [2, Fraction(1), 0.5], 2, (1,)),
        (["a", "b", "c"], [Decimal("1.5"), Decimal("0.5"), Decimal("2")],
         2, (2,)),
        (["a", "b", "c"], [1e308, 1e308, 1.0], 2, (2,)),
        ([], [], 0, ()),
        (["a", "b"], [0, 0], 0, (0, 1)),
    ]
    SEEDS = (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True)

    def test_outer_shape_and_round_lengths(self):
        items, weights, k, excluded = list("abcdef"), [1, 2, 3, 4, 5, 6], 3, (1, 4)
        idx = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 5, 42)
        self.assertEqual(len(idx), 5)
        self.assertIsInstance(idx, list)
        self.assertTrue(all(isinstance(rd, list) and len(rd) == 3 for rd in idx))
        vals = weighted_sample_many_excluding(
            items, weights, k, excluded, 5, 42)
        self.assertEqual(len(vals), 5)
        self.assertTrue(all(len(rd) == 3 for rd in vals))

    def test_first_round_matches_single_excluding_entry(self):
        # start=0 时第一轮必须逐项等于 weighted_sample_excluding(_indices)。
        for items, weights, k, excluded in self.CASES:
            for seed in self.SEEDS:
                with self.subTest(k=k, excluded=excluded, seed=seed):
                    many_i = weighted_sample_many_excluding_indices(
                        items, weights, k, excluded, 3, seed)
                    self.assertEqual(
                        many_i[0],
                        weighted_sample_excluding_indices(
                            items, weights, k, excluded, seed),
                    )
                    many_v = weighted_sample_many_excluding(
                        items, weights, k, excluded, 3, seed)
                    self.assertEqual(
                        many_v[0],
                        weighted_sample_excluding(
                            items, weights, k, excluded, seed),
                    )
                    # 流式入口首轮同样一致。
                    self.assertEqual(
                        next(iter(weighted_sample_stream_excluding_indices(
                            items, weights, k, excluded, 3, seed))),
                        weighted_sample_excluding_indices(
                            items, weights, k, excluded, seed),
                    )
                    self.assertEqual(
                        next(iter(weighted_sample_stream_excluding(
                            items, weights, k, excluded, 3, seed))),
                        weighted_sample_excluding(
                            items, weights, k, excluded, seed),
                    )

    def test_empty_excluded_matches_many_and_stream_round_by_round(self):
        # excluded 为空时必须与既有 many/stream 入口逐轮一致。
        for items, weights, k, _ in self.CASES:
            for seed in self.SEEDS:
                with self.subTest(k=k, seed=seed):
                    self.assertEqual(
                        weighted_sample_many_excluding_indices(
                            items, weights, k, (), 4, seed),
                        weighted_sample_many_indices(
                            items, weights, k, 4, seed),
                    )
                    self.assertEqual(
                        weighted_sample_many_excluding(
                            items, weights, k, (), 4, seed),
                        weighted_sample_many(items, weights, k, 4, seed),
                    )
                    self.assertEqual(
                        list(weighted_sample_stream_excluding_indices(
                            items, weights, k, (), 4, seed)),
                        list(weighted_sample_stream_indices(
                            items, weights, k, 4, seed)),
                    )
                    self.assertEqual(
                        list(weighted_sample_stream_excluding(
                            items, weights, k, (), 4, seed)),
                        list(weighted_sample_stream(
                            items, weights, k, 4, seed)),
                    )

    def test_stream_matches_many_round_by_round(self):
        for items, weights, k, excluded in self.CASES:
            for seed in self.SEEDS:
                with self.subTest(k=k, excluded=excluded, seed=seed):
                    self.assertEqual(
                        list(weighted_sample_stream_excluding_indices(
                            items, weights, k, excluded, 4, seed)),
                        weighted_sample_many_excluding_indices(
                            items, weights, k, excluded, 4, seed),
                    )
                    self.assertEqual(
                        list(weighted_sample_stream_excluding(
                            items, weights, k, excluded, 4, seed)),
                        weighted_sample_many_excluding(
                            items, weights, k, excluded, 4, seed),
                    )

    def test_values_and_indices_entries_correspond_round_by_round(self):
        for items, weights, k, excluded in self.CASES:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", True):
                with self.subTest(excluded=excluded, seed=seed):
                    mi = weighted_sample_many_excluding_indices(
                        items, weights, k, excluded, 4, seed)
                    self.assertEqual(
                        weighted_sample_many_excluding(
                            items, weights, k, excluded, 4, seed),
                        [[items[i] for i in rd] for rd in mi],
                    )
                    si = list(weighted_sample_stream_excluding_indices(
                        items, weights, k, excluded, 4, seed))
                    self.assertEqual(
                        list(weighted_sample_stream_excluding(
                            items, weights, k, excluded, 4, seed)),
                        [[items[i] for i in rd] for rd in si],
                    )

    def test_rounds_share_one_seed_stream(self):
        # 用与实现相同的共享 rng 手工连跑 draws 轮必须得到相同嵌套序列;
        # 不同 draws 的前缀逐轮相同。
        items, weights, k, excluded = (
            list("abcdef"), [10 ** 100, 1, 10 ** 90, 7, 0, 3], 3, (0, 4),
        )
        pool = [i for i in range(len(items)) if i not in set(excluded)]
        pool_weights = [weights[i] for i in pool]
        planned, use_exact = app._select_sampling_plan(list(pool_weights), k)
        self.assertTrue(use_exact)
        import random as _random

        for draws in (1, 2, 6):
            rng = _random.Random(99)
            manual = [
                app._sample_indices_exact_integer(
                    list(pool), list(planned), k, rng)
                for _ in range(draws)
            ]
            self.assertEqual(
                weighted_sample_many_excluding_indices(
                    items, weights, k, excluded, draws, 99),
                manual,
            )
        full = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 8, 123)
        head = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 3, 123)
        self.assertEqual(full[:3], head)

    def test_deterministic_nested_sequence(self):
        args = (list("abcdef"), [10 ** 100, 1, 10 ** 90, 7, 0, 3], 3, (0, 4))
        first = weighted_sample_many_excluding_indices(*args, draws=8, seed=123)
        for _ in range(4):
            self.assertEqual(
                weighted_sample_many_excluding_indices(*args, draws=8, seed=123),
                first,
            )

    def test_each_round_restarts_and_excluded_never_appear(self):
        items = list(range(6))
        weights = [10 ** 100, 1, 10 ** 99, 3, 0, 5]
        for seed in range(100):
            rounds = weighted_sample_many_excluding_indices(
                items, weights, 3, (0, 2), 7, seed)
            for rd in rounds:
                self.assertEqual(len(rd), 3)
                self.assertEqual(len(set(rd)), 3)
                self.assertTrue(all(0 <= i < 6 for i in rd))
                self.assertNotIn(0, rd)
                self.assertNotIn(2, rd)
                self.assertNotIn(4, rd)  # 未排除的零权重位置也永不出现
        # k=1 连抽多轮: 未排除位置之间允许(且高概率会)重复。
        repeats = weighted_sample_many_excluding_indices(
            ["a", "b", "c"], [1, 1, 1], 1, (2,), 20, 0)
        self.assertTrue(all(rd == [0] or rd == [1] for rd in repeats))

    def test_excluded_set_semantics_duplicates_and_order(self):
        items = list("abcdef")
        weights = [1, 2, 3, 4, 5, 6]
        base = weighted_sample_many_excluding_indices(
            items, weights, 3, (1, 3), 4, 7)
        for excluded in ((3, 1), (1, 1, 3), (3, 1, 3, 1), [1, 3],
                         [3, 1, 1, 3]):
            self.assertEqual(
                weighted_sample_many_excluding_indices(
                    items, weights, 3, excluded, 4, 7),
                base,
            )
            self.assertEqual(
                list(weighted_sample_stream_excluding_indices(
                    items, weights, 3, excluded, 4, 7)),
                base,
            )

    def test_duplicate_values_distinct_positions(self):
        idx = weighted_sample_many_excluding_indices(
            [1, 1, 1, 1], [1, 1, 1, 1], 3, (1,), 2, 123)
        vals = weighted_sample_many_excluding(
            [1, 1, 1, 1], [1, 1, 1, 1], 3, (1,), 2, 123)
        self.assertTrue(all(sorted(rd) == [0, 2, 3] for rd in idx))
        self.assertEqual(vals, [[1, 1, 1], [1, 1, 1]])

    def test_start_window_matches_slice_of_full_sequence(self):
        items, weights, k, excluded = (
            list("abcdef"), [1, 3, 2, 5, 0, 2], 3, (1, 4))
        full = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 12, 99)
        for start in (0, 1, 3, 8, 11):
            draws = 12 - start
            window = weighted_sample_many_excluding_indices(
                items, weights, k, excluded, draws, 99, start=start)
            self.assertEqual(window, full[start:start + draws])
            self.assertEqual(
                list(weighted_sample_stream_excluding_indices(
                    items, weights, k, excluded, draws, 99, start=start)),
                full[start:start + draws],
            )

    def test_start_skips_only_share_one_stream(self):
        # start 跳过只消耗同一条确定性随机流: 从 start 续抽的后续轮次与
        # 一次性生成的完整序列逐轮一致。
        items, weights, k, excluded = (
            list("abcd"), [10 ** 100, 1, 10 ** 50, 7], 3, (2,))
        first = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 5, 42)
        second = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 5, 42, start=5)
        self.assertEqual(
            first + second,
            weighted_sample_many_excluding_indices(
                items, weights, k, excluded, 10, 42),
        )

    def test_draws_zero_returns_empty_after_full_validation(self):
        self.assertEqual(
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, (0,), 0, 0),
            [],
        )
        self.assertEqual(
            weighted_sample_many_excluding(["a", "b"], [1, 2], 1, (0,), 0, 0),
            [],
        )
        self.assertEqual(
            list(weighted_sample_stream_excluding_indices(
                ["a", "b"], [1, 2], 1, (0,), 0, 0)),
            [],
        )
        # draws=0 仍须先完成全部校验。
        with self.assertRaises(TypeError):
            weighted_sample_many_excluding_indices("ab", [1, 2], 1, (), 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1], 0, (), 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a"], [float("nan")], 0, (), 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, (9,), 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, "01", 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, (True,), 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 0], 2, (1,), 0, 0)

    def test_k_zero_empty_rounds_skip_consumes_no_stream(self):
        # k=0 时每轮为空列表; start 跳过不消耗随机流, 任意 start 的输出都
        # 与 start=0 一致(也与既有入口一致)。
        for entry in (weighted_sample_many_excluding_indices,
                      weighted_sample_many_excluding):
            self.assertEqual(
                entry(["a", "b"], [0, 0], 0, (0,), 4, 0),
                [[], [], [], []],
            )
            self.assertEqual(
                entry(["a", "b"], [0, 0], 0, (0,), 2, 7, start=10 ** 6),
                [[], []],
            )
            # k=0 仍完成 excluded 校验。
            with self.assertRaises(ValueError):
                entry(["a", "b"], [0, 0], 0, (9,), 4, 0)
        self.assertEqual(
            list(weighted_sample_stream_excluding_indices(
                ["a", "b"], [0, 0], 0, (0,), 4, 0, start=10 ** 6)),
            [[], [], [], []],
        )
        # 与既有 many/stream 入口逐轮一致。
        self.assertEqual(
            weighted_sample_many_excluding_indices(
                ["a", "b"], [0, 0], 0, (), 3, 0),
            weighted_sample_many_indices(["a", "b"], [0, 0], 0, 3, 0),
        )

    def test_insufficient_remaining_positive_raises_before_any_round(self):
        # 未排除位置中的正权重不足: 在产生任何一轮前抛 ValueError, 绝不
        # 返回部分外层结果 —— 即使 draws=0 或 start 很大也不例外。
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 0], 1, (0,), 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b", "c"], [1, 1, 0], 2, (0,), 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, (0, 1), 5, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding(
                ["a", "b"], [1, 0], 1, (0,), 1000, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b", "c"], [10 ** 100, 0, 1], 2, (0, 2), 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 0], 1, (0,), 3, 0, start=10 ** 9)
        # 排除零权重位置不影响可行性。
        self.assertEqual(
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 0], 1, (1,), 2, 0),
            [[0], [0]],
        )

    def test_validation_order_sample_inputs_then_excluded_then_rounds(self):
        # items/weights/k/seed 的错误先于 excluded; excluded 的错误先于
        # draws/start。
        with self.assertRaises(TypeError):  # items 非序列先于 excluded 越界
            weighted_sample_many_excluding_indices(
                "ab", [1, 2], 1, (9,), 1, 0)
        with self.assertRaises(TypeError):  # k 类型先于 excluded 成员类型
            weighted_sample_many_excluding_indices(
                ["a"], [1], True, (True,), 1, 0)
        with self.assertRaises(TypeError):  # seed 类型先于 excluded 越界
            weighted_sample_many_excluding_indices(
                ["a"], [1], 1, (9,), 1, object())
        with self.assertRaises(ValueError):  # 权重取值先于 excluded 越界
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, -1], 1, (9,), 1, 0)
        with self.assertRaises(ValueError):  # k 越界先于 excluded 越界
            weighted_sample_many_excluding_indices(
                ["a"], [1], 2, (9,), 1, 0)
        with self.assertRaises(ValueError):  # 长度不一致先于 excluded 越界
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1], 1, (9,), 1, 0)
        with self.assertRaises(TypeError):  # 布尔权重先于 excluded 类型
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, True], 1, "01", 1, 0)
        with self.assertRaises(ValueError):  # 无穷权重先于 excluded 越界
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, float("inf")], 1, (9,), 1, 0)
        with self.assertRaises(ValueError):  # Decimal NaN 先于 excluded 越界
            weighted_sample_many_excluding_indices(
                ["a"], [Decimal("NaN")], 0, (9,), 1, 0)
        # excluded 结构/成员/范围错误先于 draws/start 错误(seed 取合法
        # 值 0, 位置参数依次为 excluded、draws, 再以关键字传非法 start)。
        with self.assertRaises(TypeError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, "01", object(), 0, start=object())
        with self.assertRaises(TypeError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, (True,), object(), 0, start=object())
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a", "b"], [1, 2], 1, (9,), object(), 0, start=object())

    def test_excluded_structure_and_member_validation(self):
        for bad in ("01", b"01", bytearray(b"01"), {0, 1}, {0: "a"},
                    iter([0]), 3, None, object()):
            with self.subTest(bad=bad):
                for entry in (weighted_sample_many_excluding_indices,
                              weighted_sample_many_excluding,
                              weighted_sample_stream_excluding_indices,
                              weighted_sample_stream_excluding):
                    with self.assertRaises(TypeError):
                        entry(["a", "b"], [1, 2], 1, bad, 1, 0)
        for bad_member in (True, False, 1.0, 0.0, "1", None, [0],
                           Fraction(1, 2), Decimal("1"), 1 + 0j):
            with self.subTest(bad_member=bad_member):
                for entry in (weighted_sample_many_excluding_indices,
                              weighted_sample_stream_excluding_indices):
                    with self.assertRaises(TypeError):
                        entry(["a", "b"], [1, 2], 1, (0, bad_member), 1, 0)

    def test_excluded_out_of_range_raises_value_error(self):
        for bad_excluded in ((2,), (-1,), (0, 5), (10 ** 100,),
                             (-(10 ** 100),)):
            with self.subTest(bad_excluded=bad_excluded):
                for entry in (weighted_sample_many_excluding_indices,
                              weighted_sample_many_excluding,
                              weighted_sample_stream_excluding_indices,
                              weighted_sample_stream_excluding):
                    with self.assertRaises(ValueError):
                        entry(["a", "b"], [1, 2], 1, bad_excluded, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices([], [], 0, (0,), 1, 0)

    def test_draws_and_start_type_and_range(self):
        for bad in (True, False, 1.0, "2", None, [2], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_many_excluding_indices(
                        ["a"], [1], 0, (), bad, 0)
                with self.assertRaises(TypeError):
                    weighted_sample_stream_excluding_indices(
                        ["a"], [1], 0, (), bad, 0)
                with self.assertRaises(TypeError):
                    weighted_sample_many_excluding_indices(
                        ["a"], [1], 0, (), 0, start=bad)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a"], [1], 0, (), -1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_many_excluding_indices(
                ["a"], [1], 0, (), 0, start=-1)

    def test_stream_returns_iterable_consumed_on_demand(self):
        items, weights, k, excluded = (
            list("abcdef"), [1, 3, 2, 5, 0, 2], 3, (0, 4))
        stream = weighted_sample_stream_excluding_indices(
            items, weights, k, excluded, 100, 7)
        self.assertFalse(isinstance(stream, list))
        iterator = iter(stream)
        full = weighted_sample_many_excluding_indices(
            items, weights, k, excluded, 100, 7)
        for expected in full[:5]:
            self.assertEqual(next(iterator), expected)
        for expected in full[5:10]:
            self.assertEqual(next(iterator), expected)

    def test_stream_validation_fails_at_creation_not_mid_iteration(self):
        # 全部参数与可行性错误必须在创建时抛出: 调用本身失败, 调用方拿不
        # 到任何可迭代的部分结果。
        def expect(exc, fn, *args, **kwargs):
            with self.assertRaises(exc):
                fn(*args, **kwargs)

        args_index = weighted_sample_stream_excluding_indices
        args_values = weighted_sample_stream_excluding
        expect(ValueError, args_index,
               ["a", "b"], [1, 0], 1, (0,), 3, 0)
        expect(ValueError, args_index,
               ["a"], [0], 1, (), 5, 0)
        expect(ValueError, args_values,
               ["a", "b", "c"], [10 ** 100, 0, 1], 2, (0, 2), 2, 0)
        expect(TypeError, args_index,
               ["a", "b"], [1, "x"], 1, (), 1, 0)
        expect(TypeError, args_index,
               ["a", "b"], [1, True], 1, (), 1, 0)
        expect(TypeError, args_index,
               ["a"], [1], True, (), 1, 0)
        expect(TypeError, args_index,
               ["a"], [1], 1, (), 1, object())
        expect(TypeError, args_index,
               ["a"], [1], 0, (), True, 0)
        expect(TypeError, args_index,
               ["a"], [1], 0, (), 1.0, 0)
        expect(ValueError, args_index,
               ["a"], [1], 0, (), -1, 0)
        expect(ValueError, args_index,
               ["a"], [1], 0, (), 0, start=-1)
        expect(ValueError, args_index,
               ["a", "b"], [1, -1], 1, (), 1, 0)
        expect(ValueError, args_index,
               ["a", "b"], [1, float("inf")], 1, (), 1, 0)
        expect(ValueError, args_index,
               ["a", "b"], [1], 1, (), 1, 0)
        expect(ValueError, args_index,
               ["a"], [1], 2, (), 1, 0)
        expect(TypeError, args_index,
               iter(["a"]), [1], 0, (), 1, 0)
        expect(TypeError, args_index,
               ["a"], iter([1]), 0, (), 1, 0)
        expect(ValueError, args_index,
               ["a"], [Decimal("NaN")], 0, (), 0, 0)
        expect(ValueError, args_values,
               ["a"], [Decimal("Infinity")], 1, (), 0, 0)
        # excluded 的错误同样在创建时抛出。
        expect(TypeError, args_index,
               ["a", "b"], [1, 2], 1, "01", 1, 0)
        expect(TypeError, args_index,
               ["a", "b"], [1, 2], 1, (True,), 1, 0)
        expect(ValueError, args_index,
               ["a", "b"], [1, 2], 1, (9,), 1, 0)

    def test_inputs_not_mutated(self):
        items = ["a", "b", "c", "d"]
        weights = [Decimal("1.5"), 2, Fraction(1, 3), 0.5]
        excluded = [2, 2, 0]
        snapshots = (list(items), list(weights), list(excluded))
        weighted_sample_many_excluding_indices(items, weights, 2, excluded, 4, 99)
        weighted_sample_many_excluding(items, weights, 2, excluded, 4, 99)
        stream_i = weighted_sample_stream_excluding_indices(
            items, weights, 2, excluded, 4, -3)
        stream_v = weighted_sample_stream_excluding(
            items, weights, 1, excluded, 4, -3)
        next(iter(stream_i))
        list(stream_v)
        self.assertEqual((items, weights, excluded), snapshots)

    def test_seed_none_keeps_random_semantics(self):
        rounds = weighted_sample_many_excluding_indices(
            list(range(50)), list(range(1, 51)), 10, (0, 1, 2, 3), 4, None)
        self.assertEqual(len(rounds), 4)
        for rd in rounds:
            self.assertEqual(len(rd), 10)
            self.assertEqual(len(set(rd)), 10)
            self.assertTrue(all(4 <= i < 50 for i in rd))

    def test_exact_paths_supported(self):
        cases = [
            (["a", "b"], [10 ** 400, 10 ** 400], 2, ()),
            (["H", "t", "z"],
             [10 ** 100, Decimal("1E-100"), Decimal("-0")], 1, (0,)),
            (["a", "b", "c"], [1e308, 1e308, 1.0], 2, (2,)),
            (["a", "b", "c"], [9, Fraction(1, 100), 3], 2, (2,)),
            (["a", "b"], [1, Fraction(1, 10 ** 100)], 1, ()),
            (["p", "q", "r", "s"],
             [2, Fraction(1), 0.5, Decimal("0.25")], 3, (1,)),
        ]
        for items, weights, k, excluded in cases:
            for seed in (0, 7, 2316):
                with self.subTest(k=k, excluded=excluded, seed=seed):
                    many = weighted_sample_many_excluding_indices(
                        items, weights, k, excluded, 3, seed)
                    self.assertEqual(
                        list(weighted_sample_stream_excluding_indices(
                            items, weights, k, excluded, 3, seed)),
                        many,
                    )
                    self.assertEqual(
                        many[0],
                        weighted_sample_excluding_indices(
                            items, weights, k, excluded, seed),
                    )
                    for rd in many:
                        self.assertEqual(len(rd), k)
                        self.assertEqual(len(set(rd)), k)
                        self.assertTrue(all(i not in excluded for i in rd))

    def test_results_are_directly_serializable(self):
        # 索引轮次可直接交给 serialize_metrics 并精确往返。
        rounds = weighted_sample_many_excluding_indices(
            list(range(6)), [10 ** 100, 1, 2, 3, 4, 5], 3, (0,), 4, 42)
        text = serialize_metrics({"rounds": rounds})
        self.assertEqual(deserialize_metrics(text), {"rounds": rounds})
        # 流式轮次同样可直接序列化。
        stream_rounds = list(weighted_sample_stream_excluding_indices(
            list(range(6)), [10 ** 100, 1, 2, 3, 4, 5], 3, (0,), 4, 42))
        self.assertEqual(
            deserialize_metrics(serialize_metrics(stream_rounds)),
            stream_rounds,
        )
        # 值入口的 Decimal / Fraction / 超大整数元素保持精确十进制行为。
        items = [Decimal("1.5"), Fraction(1, 3), 10 ** 100, "x", 7]
        vals = weighted_sample_many_excluding(
            items, [1, 1, 1, 1, 1], 3, (3,), 2, 7)
        restored = deserialize_metrics(serialize_metrics({"values": vals}))
        for rd in restored["values"]:
            for value in rd:
                self.assertNotIsInstance(value, float)
        self.assertTrue(any(
            value == Decimal("1.5")
            for rd in restored["values"] for value in rd))

    def test_four_entries_share_validation_and_error_classes(self):
        # 四个入口对同一批非法输入给出完全一致的异常类别。
        entries = (
            weighted_sample_many_excluding_indices,
            weighted_sample_many_excluding,
            weighted_sample_stream_excluding_indices,
            weighted_sample_stream_excluding,
        )
        bad_calls = [
            ("ab", [1, 2], 1, (), 1, 0),
            (["a", "b"], [1, "x"], 1, (), 1, 0),
            (["a", "b"], [1, True], 1, (), 1, 0),
            (["a"], [1], True, (), 1, 0),
            (["a"], [1], 1, (), 1, object()),
            (["a", "b"], [1, -1], 1, (), 1, 0),
            (["a", "b"], [1, float("nan")], 1, (), 1, 0),
            (["a", "b"], [1, float("inf")], 1, (), 1, 0),
            (["a", "b"], [1], 1, (), 1, 0),
            (["a"], [1], 2, (), 1, 0),
            (["a"], [1], -1, (), 1, 0),
            (["a", "b"], [1, 2], 1, "01", 1, 0),
            (["a", "b"], [1, 2], 1, {0}, 1, 0),
            (["a", "b"], [1, 2], 1, (True,), 1, 0),
            (["a", "b"], [1, 2], 1, (1.0,), 1, 0),
            (["a", "b"], [1, 2], 1, (2,), 1, 0),
            (["a", "b"], [1, 2], 1, (-1,), 1, 0),
            (["a", "b"], [1, 0], 1, (0,), 1, 0),
            (["a", "b"], [0, 0], 1, (), 1, 0),
            (["a", "b"], [1, 2], 1, (), True, 0),
            (["a", "b"], [1, 2], 1, (), -1, 0),
            (["a", "b"], [1, 2], 1, (), 1, 0, 1.0),
            (["a", "b"], [1, 2], 1, (), 1, 0, -1),
        ]
        for call in bad_calls:
            categories = []
            for entry in entries:
                try:
                    entry(*call)
                except (TypeError, ValueError) as exc:
                    categories.append(type(exc))
                else:
                    self.fail("no exception for %r" % (call,))
            self.assertEqual(len(set(categories)), 1, call)

    def test_existing_entries_unchanged(self):
        # 新增入口不改变既有入口的序列、返回类型与校验。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample_excluding_indices(
                ["a", "b", "c"], [1, 3, 2], 2, (2,), 7),
            [1, 0],
        )
        self.assertEqual(
            weighted_sample_many_indices(
                ["p", "q", "r"], [2, Fraction(1), 0.5], 3, 4, 42),
            [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]],
        )
        text = serialize_metrics({"n": 10 ** 100})
        self.assertEqual(text, '{"n":1' + "0" * 100 + "}")


class WeightedSampleCountsTest(unittest.TestCase):
    """批量频次入口 weighted_sample_counts /
    weighted_sample_excluding_counts。"""

    CASES = [
        (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
        (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
        (["p", "q"], [0.5, 1.5], 2),
        (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
        ([], [], 0),
        (["p", "q", "r"], [2, Fraction(1), 0.5], 3),
        (["a", "b", "c"],
         [Decimal("1.5"), Decimal("0.5"), Decimal("2")], 3),
        (["a", "b"], [10 ** 400, 10 ** 400], 2),
        (["a", "b", "c"], [1e308, 1e308, 1.0], 3),
        (["a", "b"], [1, Fraction(1, 10 ** 100)], 1),
    ]
    EXCLUDED_CASES = [
        (list("abcdef"), [1, 3, 2, 5, 0, 2], 4, (0, 4)),
        (list(range(20)), [10 ** 80 + i for i in range(20)], 10, (2, 5, 9)),
        (["p", "q", "r"], [0.5, 1.5, 2.5], 2, (2,)),
        (list("xyz"), [10 ** 100, 1, 10 ** 50], 2, (0,)),
        (["a", "b"], [10 ** 400, 10 ** 400], 2, ()),
        (["p", "q", "r"], [2, Fraction(1), 0.5], 2, (1,)),
        (["a", "b", "c"],
         [Decimal("1.5"), Decimal("0.5"), Decimal("2")], 2, (2,)),
        (["a", "b", "c"], [1e308, 1e308, 1.0], 2, (2,)),
        ([], [], 0, ()),
        (["a", "b"], [0, 0], 0, (0, 1)),
    ]
    SEEDS = (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True)

    @staticmethod
    def _flatten(rounds, n):
        counts = [0] * n
        for rd in rounds:
            for position in rd:
                counts[position] += 1
        return counts

    def test_shape_is_length_n_int_list(self):
        items, weights, k = list("abcdef"), [1, 2, 3, 4, 5, 6], 3
        counts = weighted_sample_counts(items, weights, k, 9, 42)
        self.assertIsInstance(counts, list)
        self.assertEqual(len(counts), len(items))
        self.assertTrue(all(type(c) is int for c in counts))
        excluded = weighted_sample_excluding_counts(
            items, weights, k, (1, 4), 9, 42)
        self.assertIsInstance(excluded, list)
        self.assertEqual(len(excluded), len(items))
        self.assertTrue(all(type(c) is int for c in excluded))

    def test_counts_equal_flattened_many_rounds(self):
        # 与 weighted_sample_many_indices 对应窗口逐位置摊平计数一致。
        for items, weights, k in self.CASES:
            n = len(items)
            for seed in self.SEEDS:
                full = weighted_sample_many_indices(
                    items, weights, k, 12, seed)
                for start, draws in ((0, 12), (0, 5), (2, 6), (11, 1),
                                     (0, 0), (3, 0)):
                    with self.subTest(k=k, seed=seed, start=start,
                                      draws=draws):
                        self.assertEqual(
                            weighted_sample_counts(
                                items, weights, k, draws, seed, start),
                            self._flatten(full[start:start + draws], n),
                        )

    def test_excluding_counts_equal_flattened_many_rounds(self):
        for items, weights, k, ex in self.EXCLUDED_CASES:
            n = len(items)
            for seed in self.SEEDS:
                full = weighted_sample_many_excluding_indices(
                    items, weights, k, ex, 12, seed)
                for start, draws in ((0, 12), (0, 5), (2, 6), (11, 1),
                                     (0, 0), (3, 0)):
                    with self.subTest(k=k, ex=ex, seed=seed, start=start,
                                      draws=draws):
                        self.assertEqual(
                            weighted_sample_excluding_counts(
                                items, weights, k, ex, draws, seed, start),
                            self._flatten(full[start:start + draws], n),
                        )

    def test_total_count_is_draws_times_k(self):
        for seed in range(60):
            counts = weighted_sample_counts(
                list(range(6)), [1, 2, 3, 0, 5, 6], 4, 13, seed)
            self.assertEqual(sum(counts), 13 * 4)
            excluded = weighted_sample_excluding_counts(
                list(range(6)), [1, 2, 3, 0, 5, 6], 3, (0, 4), 11, seed)
            self.assertEqual(sum(excluded), 11 * 3)

    def test_excluded_positions_always_zero(self):
        items = list(range(6))
        weights = [10 ** 100, 1, 10 ** 99, 3, 0, 5]
        for excluded in ((0,), (2, 4), (0, 2, 4), (5, 3, 1)):
            for seed in self.SEEDS:
                counts = weighted_sample_excluding_counts(
                    items, weights, 2, excluded, 9, seed)
                for position in excluded:
                    self.assertEqual(counts[position], 0)
                # 未排除的零权重位置 (4) 也永不累计。
                if 4 not in excluded:
                    self.assertEqual(counts[4], 0)
                self.assertEqual(
                    len(counts), len(items)
                )

    def test_empty_excluded_matches_plain_counts(self):
        for items, weights, k, _ in self.EXCLUDED_CASES:
            for seed in self.SEEDS:
                self.assertEqual(
                    weighted_sample_excluding_counts(
                        items, weights, k, (), 8, seed),
                    weighted_sample_counts(items, weights, k, 8, seed),
                )

    def test_excluded_set_semantics_duplicates_and_order(self):
        items, weights = list("abcdef"), [1, 2, 3, 4, 5, 6]
        base = weighted_sample_excluding_counts(
            items, weights, 3, (1, 3), 7, 7)
        for excluded in ((3, 1), (1, 1, 3), (3, 1, 3, 1), [1, 3],
                         [3, 1, 1, 3]):
            self.assertEqual(
                weighted_sample_excluding_counts(
                    items, weights, 3, excluded, 7, 7),
                base,
            )

    def test_duplicate_values_distinct_positions(self):
        # 相等元素值按不同位置独立累计。
        counts = weighted_sample_counts(
            [1, 1, 1], [1, 1, 1], 3, 4, 123)
        self.assertEqual(len(counts), 3)
        self.assertEqual(sum(counts), 12)
        excluded = weighted_sample_excluding_counts(
            [1, 1, 1, 1], [1, 1, 1, 1], 3, (1,), 5, 123)
        self.assertEqual(excluded[1], 0)
        self.assertEqual(sum(excluded), 15)

    def test_draws_zero_returns_zeros_after_full_validation(self):
        self.assertEqual(
            weighted_sample_counts(["a", "b"], [1, 2], 2, 0, 0), [0, 0])
        self.assertEqual(
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 2], 1, (0,), 0, 0), [0, 0])
        # draws=0 仍完成结构/范围/权重/excluded/可行性全部校验。
        with self.assertRaises(TypeError):
            weighted_sample_counts("ab", [1, 2], 1, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_counts(["a", "b"], [1], 1, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_counts(["a"], [float("nan")], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_counts(["a", "b"], [1, 0], 2, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 2], 1, (9,), 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 2], 1, "01", 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 2], 1, (True,), 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 0], 2, (1,), 0, 0)

    def test_k_zero_zeros_without_consuming_stream(self):
        self.assertEqual(
            weighted_sample_counts(["a", "b"], [1, 2], 0, 4, 0), [0, 0])
        # k=0 任意 start 都不消耗随机流, 结果仍是全零。
        self.assertEqual(
            weighted_sample_counts(
                ["a", "b"], [1, 2], 0, 4, 0, start=10 ** 9), [0, 0])
        self.assertEqual(
            weighted_sample_excluding_counts(
                ["a", "b"], [0, 0], 0, (0, 1), 3, 7, start=10 ** 6),
            [0, 0],
        )
        # k=0 仍完成权重与 excluded 校验。
        with self.assertRaises(ValueError):
            weighted_sample_counts(["a"], [float("nan")], 0, 4, 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_counts(
                ["a", "b"], [0, 0], 0, (9,), 4, 0)

    def test_validation_parity_with_index_entries(self):
        # 新入口与对应索引入口对同一批非法输入给出完全一致的异常类别。
        plain_bad = [
            ("ab", [1, 2], 1, 1, 0),
            (["a", "b"], [1, "x"], 1, 1, 0),
            (["a", "b"], [1, True], 1, 1, 0),
            (["a"], [1], True, 1, 0),
            (["a"], [1], 1, 1, object()),
            (["a", "b"], [1, -1], 1, 1, 0),
            (["a", "b"], [1, float("nan")], 1, 1, 0),
            (["a", "b"], [1, float("inf")], 1, 1, 0),
            (["a", "b"], [1], 1, 1, 0),
            (["a"], [1], 2, 1, 0),
            (["a"], [1], -1, 1, 0),
            (["a"], [Decimal("NaN")], 0, 1, 0),
            (["a"], [1], 0, True, 0),
            (["a"], [1], 0, 1.0, 0),
            (["a"], [1], 0, -1, 0),
            (["a"], [1], 0, 1, 0, 1.0),
            (["a"], [1], 0, 1, 0, -1),
            (["a", "b"], [1, 0], 2, 3, 0),
        ]
        for call in plain_bad:
            with self.subTest(call=call):
                with self.assertRaises((TypeError, ValueError)) as e1:
                    weighted_sample_counts(*call)
                with self.assertRaises((TypeError, ValueError)) as e2:
                    weighted_sample_many_indices(*call)
                self.assertEqual(type(e1.exception), type(e2.exception))

        excluding_bad = [
            ("ab", [1, 2], 1, (9,), 1, 0),
            (["a"], [1], True, (True,), 1, 0),
            (["a"], [1], 1, (9,), 1, object()),
            (["a", "b"], [1, -1], 1, (9,), 1, 0),
            (["a"], [1], 2, (9,), 1, 0),
            (["a", "b"], [1], 1, (9,), 1, 0),
            (["a", "b"], [1, True], 1, "01", 1, 0),
            (["a", "b"], [1, float("inf")], 1, (9,), 1, 0),
            (["a"], [Decimal("NaN")], 0, (9,), 1, 0),
            (["a", "b"], [1, 2], 1, "01", 1, 0),
            (["a", "b"], [1, 2], 1, {0}, 1, 0),
            (["a", "b"], [1, 2], 1, (True,), 1, 0),
            (["a", "b"], [1, 2], 1, (1.0,), 1, 0),
            (["a", "b"], [1, 2], 1, (2,), 1, 0),
            (["a", "b"], [1, 2], 1, (-1,), 1, 0),
            (["a", "b"], [1, 0], 1, (0,), 3, 0),
            (["a", "b"], [0, 0], 1, (), 1, 0),
            (["a", "b"], [1, 2], 1, (), True, 0),
            (["a", "b"], [1, 2], 1, (), -1, 0),
            (["a", "b"], [1, 2], 1, (), 1, 0, 1.0),
            (["a", "b"], [1, 2], 1, (), 1, 0, -1),
        ]
        for call in excluding_bad:
            with self.subTest(call=call):
                with self.assertRaises((TypeError, ValueError)) as e1:
                    weighted_sample_excluding_counts(*call)
                with self.assertRaises((TypeError, ValueError)) as e2:
                    weighted_sample_many_excluding_indices(*call)
                self.assertEqual(type(e1.exception), type(e2.exception))

    def test_insufficient_positive_raises_before_any_counts(self):
        # 正权重不足必须在返回列表前抛 ValueError(无部分计数)。
        with self.assertRaises(ValueError):
            weighted_sample_counts(["a", "b"], [1, 0], 2, 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_counts(
                ["a", "b", "c"], [10 ** 100, 0, 1], 3, 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 0], 1, (0,), 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 2], 1, (0, 1), 5, 0)
        # start 很大也不例外: 可行性先于跳轮判定。
        with self.assertRaises(ValueError):
            weighted_sample_counts(["a"], [0], 1, 3, 0, start=10 ** 9)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_counts(
                ["a", "b"], [1, 0], 1, (0,), 3, 0, start=10 ** 9)

    def test_inputs_not_mutated(self):
        items = ["a", "b", "c", "d"]
        weights = [Decimal("1.5"), 2, Fraction(1, 3), 0.5]
        excluded = [2, 2, 0]
        snapshots = (list(items), list(weights), list(excluded))
        weighted_sample_counts(items, weights, 3, 5, 99)
        weighted_sample_excluding_counts(items, weights, 2, excluded, 5, 99)
        self.assertEqual((items, weights, excluded), snapshots)

    def test_deterministic_for_same_seed(self):
        args = (list(range(10)), list(range(1, 11)), 5)
        first = weighted_sample_counts(*args, 30, seed=123)
        for _ in range(4):
            self.assertEqual(
                weighted_sample_counts(*args, 30, seed=123), first)
        ex_first = weighted_sample_excluding_counts(
            list(range(10)), list(range(1, 11)), 5, (0, 2), 30, seed=123)
        for _ in range(4):
            self.assertEqual(
                weighted_sample_excluding_counts(
                    list(range(10)), list(range(1, 11)), 5, (0, 2),
                    30, seed=123),
                ex_first,
            )

    def test_exact_paths_counts_align(self):
        cases = [
            (["a", "b"], [10 ** 400, 10 ** 400], 2, ()),
            (["H", "t", "z"],
             [10 ** 100, Decimal("1E-100"), Decimal("-0")], 1, (0,)),
            (["a", "b", "c"], [1e308, 1e308, 1.0], 2, (2,)),
            (["a", "b"], [9, Fraction(1, 100)], 1, ()),
            (["a", "b"], [1, Fraction(1, 10 ** 100)], 1, ()),
            (["p", "q", "r", "s"],
             [2, Fraction(1), 0.5, Decimal("0.25")], 3, (1,)),
        ]
        for items, weights, k, excluded in cases:
            n = len(items)
            for seed in (0, 7, 2316):
                with self.subTest(k=k, seed=seed):
                    plain = weighted_sample_counts(
                        items, weights, k, 6, seed)
                    self.assertEqual(
                        plain,
                        self._flatten(
                            weighted_sample_many_indices(
                                items, weights, k, 6, seed), n),
                    )
                    excluding = weighted_sample_excluding_counts(
                        items, weights, k, excluded, 6, seed)
                    self.assertEqual(
                        excluding,
                        self._flatten(
                            weighted_sample_many_excluding_indices(
                                items, weights, k, excluded, 6, seed), n),
                    )

    def test_counts_serialize_exact_roundtrip(self):
        # 计数为任意精度整数, 直接交给 serialize_metrics 精确往返, 不出
        # 现浮点或科学计数文本。
        counts = weighted_sample_counts(
            list(range(6)), [10 ** 100, 1, 2, 3, 4, 5], 3, 17, 42)
        text = serialize_metrics(counts)
        self.assertNotIn(".", text)
        self.assertNotIn("e", text)
        self.assertNotIn("E", text)
        restored = deserialize_metrics(text)
        self.assertEqual(restored, counts)
        self.assertTrue(all(type(c) is int for c in restored))

        excluding = weighted_sample_excluding_counts(
            list(range(6)), [10 ** 100, 1, 2, 3, 4, 5], 3, (0,), 17, 42)
        text = serialize_metrics({"counts": excluding})
        self.assertEqual(
            deserialize_metrics(text)["counts"], excluding)

        # 计数列表本身也能容纳 5000 位整数并保持精确十进制往返(不经浮点)。
        giant = [0, 10 ** 5000 + 7]
        giant_text = serialize_metrics(giant)
        self.assertNotIn("e", giant_text.lower())
        self.assertEqual(deserialize_metrics(giant_text), giant)
        self.assertTrue(
            all(type(c) is int for c in deserialize_metrics(giant_text)))

    def test_existing_entries_unchanged(self):
        # 新增频次入口不改变既有入口的序列、返回类型与序列化格式。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample_many_indices(
                ["p", "q", "r"], [2, Fraction(1), 0.5], 3, 4, 42),
            [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]],
        )
        self.assertEqual(
            serialize_metrics({"n": 10 ** 100}),
            '{"n":1' + "0" * 100 + "}",
        )


class WeightedSampleScheduleTest(unittest.TestCase):
    """按轮次变化权重的批量入口
    weighted_sample_schedule / weighted_sample_schedule_indices。"""

    ITEMS = list("abcd")
    SCHEDULE = [
        [1, 2, 3, 4],
        [4, 3, 2, 1],
        [0, 1, 3, 5],
        [10 ** 100, 1, 1, 1],
        [Fraction(1, 3), 2, 0, 1],
        [Decimal("1E-50"), 1, 1, 1],
    ]

    def test_outer_shape_and_round_lengths(self):
        idx = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 3, 6, 42)
        self.assertEqual(len(idx), 6)
        self.assertTrue(all(len(rd) == 3 for rd in idx))
        vals = weighted_sample_schedule(self.ITEMS, self.SCHEDULE, 3, 6, 42)
        self.assertEqual(len(vals), 6)
        self.assertTrue(all(len(rd) == 3 for rd in vals))

    def test_first_round_matches_single_entry(self):
        # start=0 的首轮必须与 weighted_sample_indices 对应行逐项一致。
        cases = [
            (list("abcdef"), [[1, 3, 2, 5, 0, 2]] * 3, 4),
            (list(range(20)), [[10 ** 80 + i for i in range(20)]] * 2, 10),
            (["p", "q"], [[0.5, 1.5], [2, 1]], 2),
            ([], [[]], 0),
            (list("xyz"), [[10 ** 100, 1, 10 ** 50], [1, 1, 1]], 2),
            (list("ab"), [[Fraction(1, 3), 2], [Decimal("0.5"), 1]], 1),
        ]
        for items, schedule, k in cases:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                with self.subTest(items=items, k=k, seed=seed):
                    sched_i = weighted_sample_schedule_indices(
                        items, schedule, k, len(schedule), seed)
                    self.assertEqual(
                        sched_i[0],
                        weighted_sample_indices(
                            items, schedule[0], k, seed))
                    sched_v = weighted_sample_schedule(
                        items, schedule, k, len(schedule), seed)
                    self.assertEqual(
                        sched_v[0],
                        weighted_sample(items, schedule[0], k, seed))

    def test_identical_rows_match_many_indices(self):
        # 权重各行完全相同时与 weighted_sample_many_indices 同参完全一致。
        cases = [
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
            (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
            (["p", "q"], [0.5, 1.5], 2),
            (list("xyz"), [Fraction(1, 3), 2, Decimal("0.5")], 2),
            (list("ab"), [10 ** 400, 1], 1),
        ]
        for items, weights, k in cases:
            for seed in (0, 7, 123):
                for draws, start in ((5, 0), (3, 2), (1, 4), (0, 0)):
                    schedule = [list(weights) for _ in range(start + draws)]
                    with self.subTest(k=k, seed=seed, draws=draws, start=start):
                        self.assertEqual(
                            weighted_sample_schedule_indices(
                                items, schedule, k, draws, seed, start),
                            weighted_sample_many_indices(
                                items, weights, k, draws, seed, start),
                        )
                        self.assertEqual(
                            weighted_sample_schedule(
                                items, schedule, k, draws, seed, start),
                            weighted_sample_many(
                                items, weights, k, draws, seed, start),
                        )

    def test_each_round_uses_its_own_row(self):
        # 第 j 轮使用 schedule 第 j 行: 零权重行只在该轮生效。
        items = list("ab")
        # 行 0 只允许位置 0, 行 1 只允许位置 1。
        schedule = [[1, 0], [0, 1]]
        for seed in range(20):
            self.assertEqual(
                weighted_sample_schedule_indices(items, schedule, 1, 2, seed),
                [[0], [1]],
            )

    def test_start_window_matches_slice_of_full_run(self):
        # start 只跳过完整轮次: 结果与 start=0 完整调用按
        # [start, start+draws) 切片逐项一致, 含各行抽样计划不同的情形。
        full = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 2, 6, 99)
        for start in range(6):
            for draws in range(0, 6 - start + 1):
                with self.subTest(start=start, draws=draws):
                    self.assertEqual(
                        weighted_sample_schedule_indices(
                            self.ITEMS, self.SCHEDULE, 2, draws, 99, start),
                        full[start:start + draws],
                    )

    def test_rounds_share_one_seed_stream(self):
        # 所有轮共享同一条由 seed 初始化的随机流: 不同 draws 的前缀逐轮
        # 相同; 重复调用完全确定。
        full = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 3, 6, 123)
        head = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 3, 3, 123)
        self.assertEqual(full[:3], head)
        for _ in range(4):
            self.assertEqual(
                weighted_sample_schedule_indices(
                    self.ITEMS, self.SCHEDULE, 3, 6, 123),
                full,
            )

    def test_values_and_indices_entries_correspond_round_by_round(self):
        idx = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 3, 6, 7)
        vals = weighted_sample_schedule(self.ITEMS, self.SCHEDULE, 3, 6, 7)
        self.assertEqual(
            [[self.ITEMS[i] for i in rd] for rd in idx], vals)

    def test_each_round_restarts_from_all_positions(self):
        # 轮内索引在原始范围内且不重复; 轮间允许再选同一位置。
        for seed in range(50):
            rounds = weighted_sample_schedule_indices(
                list(range(6)),
                [[10 ** 100, 1, 10 ** 99, 3, 0, 5],
                 [1, 1, 1, 1, 1, 1],
                 [5, 0, 3, 1, 10 ** 99, 1]],
                5, 3, seed)
            for rd in rounds:
                self.assertEqual(len(rd), 5)
                self.assertEqual(len(set(rd)), 5)
                self.assertTrue(all(0 <= i < 6 for i in rd))
        # k=1 连抽多轮: 每轮独立, 允许(且高概率会)重复同一位置。
        repeats = weighted_sample_schedule_indices(
            ["a", "b"], [[1, 1]] * 12, 1, 12, 0)
        self.assertTrue(all(rd == [0] or rd == [1] for rd in repeats))

    def test_zero_weight_never_chosen_in_any_round(self):
        schedule = [[0, 5, 0], [1, 0, 0], [0, 0, 7]]
        for seed in range(50):
            rounds = weighted_sample_schedule_indices(
                list("abc"), schedule, 1, 3, seed)
            self.assertEqual(rounds[0], [1])
            self.assertEqual(rounds[1], [0])
            self.assertEqual(rounds[2], [2])

    def test_duplicate_values_distinct_positions(self):
        idx = weighted_sample_schedule_indices(
            [1, 1, 1], [[1, 1, 1], [3, 2, 1]], 3, 2, 123)
        vals = weighted_sample_schedule(
            [1, 1, 1], [[1, 1, 1], [3, 2, 1]], 3, 2, 123)
        self.assertTrue(all(sorted(rd) == [0, 1, 2] for rd in idx))
        self.assertEqual(vals, [[1, 1, 1], [1, 1, 1]])

    def test_k_zero_returns_empty_rounds_without_stream_consumption(self):
        # k=0 的轮次返回空列表且不消耗随机流: start 不影响结果。
        schedule = [[0, 0], [1, 2], [0, 0]]
        self.assertEqual(
            weighted_sample_schedule_indices(["a", "b"], schedule, 0, 3, 5),
            [[], [], []],
        )
        self.assertEqual(
            weighted_sample_schedule_indices(
                ["a", "b"], schedule, 0, 2, 5, start=1),
            [[], []],
        )
        self.assertEqual(
            weighted_sample_schedule(["a", "b"], schedule, 0, 3, 5),
            [[], [], []],
        )
        # k=0 时即使某行权重全为零也合法。
        self.assertEqual(
            weighted_sample_schedule_indices([], [[]], 0, 1, 0), [[]])

    def test_draws_zero_returns_empty_after_full_validation(self):
        self.assertEqual(
            weighted_sample_schedule_indices(
                ["a", "b"], [[1, 2], [3, 4]], 2, 0, 0), [])
        self.assertEqual(
            weighted_sample_schedule(["a", "b"], [[1, 2]], 2, 0, 0), [])
        # draws=0 仍完成全部结构、权重与可行性校验。
        with self.assertRaises(TypeError):
            weighted_sample_schedule_indices("ab", [[1, 2]], 1, 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_indices(["a", "b"], "xx", 1, 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_indices(["a", "b"], [[1, "x"]], 1, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a", "b"], [[1]], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(
                ["a"], [[float("nan")]], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a", "b"], [[1, 0]], 2, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a", "b"], [[1, 2]], 1, 0, 0,
                                             start=2)

    def test_empty_schedule_with_zero_draws(self):
        self.assertEqual(
            weighted_sample_schedule_indices(["a"], [], 0, 0, 0), [])
        self.assertEqual(weighted_sample_schedule([], [], 0, 0, 0), [])
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a"], [], 0, 1, 0)

    def test_schedule_structure_type_errors(self):
        def te(schedule):
            with self.assertRaises(TypeError):
                weighted_sample_schedule_indices(["a", "b"], schedule, 1, 1, 0)
            with self.assertRaises(TypeError):
                weighted_sample_schedule(["a", "b"], schedule, 1, 1, 0)

        te("not a schedule")          # 文本
        te(b"bytes")                  # 字节序列
        te({0: [1, 2]})               # 映射不是序列
        te({(1, 2)})                  # 集合不是序列
        te((w for w in [[1, 2]]))     # 生成器长度不可确定
        te([[1, 2], "row"])           # 某一行是文本
        te([[1, 2], None])            # 某一行不是序列
        te([[1, 2], {0: 1}])          # 某一行是映射

    def test_draws_and_start_validation(self):
        schedule = [[1, 2], [2, 1]]
        for bad in (True, False, 1.0, "2", None, [2], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_schedule_indices(
                        ["a", "b"], schedule, 1, bad, 0)
                with self.assertRaises(TypeError):
                    weighted_sample_schedule(
                        ["a", "b"], schedule, 1, 1, 0, start=bad)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a", "b"], schedule, 1, -1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule(["a", "b"], schedule, 1, 1, 0, start=-1)

    def test_window_out_of_range_raises_value_error(self):
        schedule = [[1, 2], [2, 1]]
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a", "b"], schedule, 1, 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(
                ["a", "b"], schedule, 1, 1, 0, start=2)
        with self.assertRaises(ValueError):
            weighted_sample_schedule(
                ["a", "b"], schedule, 1, 2, 0, start=1)
        # 恰好覆盖整个 schedule 合法。
        self.assertEqual(
            len(weighted_sample_schedule_indices(
                ["a", "b"], schedule, 1, 1, 0, start=1)), 1)

    def test_row_length_must_match_items(self):
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(
                ["a", "b"], [[1, 2], [1, 2, 3]], 1, 2, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule(["a", "b"], [[1]], 1, 1, 0)

    def test_weight_value_errors_in_any_row(self):
        def ve(schedule):
            with self.assertRaises(ValueError):
                weighted_sample_schedule_indices(["a", "b"], schedule, 1, 1, 0)
            with self.assertRaises(ValueError):
                weighted_sample_schedule(["a", "b"], schedule, 1, 1, 0)

        ve([[1, -1], [1, 1]])                    # 负权重(窗口内行)
        ve([[1, 1], [1, -1]])                    # 负权重(窗口外行同样校验)
        ve([[1, float("nan")], [1, 1]])          # NaN
        ve([[1, 1], [float("inf"), 1]])          # 无穷
        ve([[Decimal("NaN"), 1], [1, 1]])        # Decimal NaN
        ve([[1, 1], [Decimal("-Infinity"), 1]])  # Decimal 负无穷
        ve([[Fraction(-1, 2), 1], [1, 1]])       # 负 Fraction

    def test_weight_element_type_errors(self):
        def te(schedule):
            with self.assertRaises(TypeError):
                weighted_sample_schedule_indices(["a", "b"], schedule, 1, 1, 0)

        te([[1, True], [1, 1]])     # 布尔权重
        te([[1, 1], [1, "x"]])      # 非实数权重(窗口外行同样校验)
        te([[1, None], [1, 1]])
        te([[1, 1], [1, 1 + 0j]])

    def test_insufficient_positive_weights_in_any_row(self):
        # k>0 时任一行(含窗口外行)正权重不足 k 个都在返回前抛 ValueError。
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(
                ["a", "b"], [[1, 0], [1, 1]], 2, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(
                ["a", "b"], [[1, 1], [1, 0]], 2, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule(
                ["a", "b"], [[1, 1], [0, 0]], 1, 1, 0)
        # k=0 时权重全为零的行合法。
        self.assertEqual(
            weighted_sample_schedule_indices(
                ["a", "b"], [[0, 0], [1, 1]], 0, 2, 0),
            [[], []],
        )

    def test_k_and_seed_follow_existing_rules(self):
        schedule = [[1, 2], [2, 1]]
        with self.assertRaises(TypeError):
            weighted_sample_schedule_indices(["a", "b"], schedule, True, 1, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_indices(["a", "b"], schedule, 1.0, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a", "b"], schedule, -1, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_indices(["a", "b"], schedule, 3, 1, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_indices(
                ["a", "b"], schedule, 1, 1, object())

    def test_inputs_and_schedule_not_mutated(self):
        items = list("abc")
        schedule = [[10 ** 100, 2, 3], [Fraction(1, 2), 0, 1],
                    [Decimal("0.5"), 1, 1]]
        items_snap = list(items)
        schedule_snap = [list(row) for row in schedule]
        weighted_sample_schedule(items, schedule, 2, 3, 99)
        weighted_sample_schedule_indices(items, schedule, 2, 2, -3, start=1)
        self.assertEqual(items, items_snap)
        self.assertEqual(schedule, schedule_snap)

    def test_mixed_exact_types_across_rows_deterministic(self):
        # 各行混合 int / float / Fraction / Decimal 与超大整数, 全程不经过
        # 浮点转换, 重复调用完全确定。
        items = list("abcd")
        schedule = [
            [1, 0.5, 2, 1],
            [Fraction(1, 3), 2, 0, 1],
            [Decimal("1E-50"), 1, 1, 1],
            [10 ** 400, 1, 1, 1],
            [Decimal("1E1000"), 1, 0, 2],
        ]
        first = weighted_sample_schedule_indices(items, schedule, 2, 5, 5)
        for _ in range(4):
            self.assertEqual(
                weighted_sample_schedule_indices(items, schedule, 2, 5, 5),
                first)
        # 窗口切片与完整序列一致(不同行走不同抽样路径时随机流消耗仍对齐)。
        self.assertEqual(
            weighted_sample_schedule_indices(items, schedule, 2, 3, 5, start=2),
            first[2:],
        )

    def test_tiny_positive_weights_not_swallowed(self):
        # 极小正权重(Fraction / Decimal)保持候选资格, 不被浮点吞成零:
        # 若被吞成零, 则正权重不足 k=2 个, 会在返回前抛 ValueError; 这里
        # 每轮都必须把两个位置全部选出。
        schedule = [
            [Fraction(1, 10 ** 100), 1],
            [Decimal("1E-100"), 1],
        ]
        for seed in range(50):
            rounds = weighted_sample_schedule_indices(
                ["x", "y"], schedule, 2, 2, seed)
            self.assertTrue(all(sorted(rd) == [0, 1] for rd in rounds))

    def test_seed_none_keeps_random_semantics(self):
        schedule = [list(range(1, 51))] * 4
        rounds = weighted_sample_schedule_indices(
            list(range(50)), schedule, 10, 4, None)
        self.assertEqual(len(rounds), 4)
        for rd in rounds:
            self.assertEqual(len(set(rd)), 10)
            self.assertTrue(all(0 <= i < 50 for i in rd))

    def test_results_serialize_exactly(self):
        # 结果是普通索引/值列表, 可直接交给 serialize_metrics 精确往返。
        idx = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 2, 6, 42)
        text = serialize_metrics(idx)
        self.assertNotIn("e", text.lower())
        self.assertEqual(deserialize_metrics(text), idx)
        vals = weighted_sample_schedule(self.ITEMS, self.SCHEDULE, 2, 6, 42)
        self.assertEqual(
            deserialize_metrics(serialize_metrics({"rounds": vals})),
            {"rounds": vals},
        )

    def test_existing_entries_unchanged(self):
        # 新增 schedule 入口不改变既有入口的序列与序列化格式。
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample_many_indices(
                ["p", "q", "r"], [2, Fraction(1), 0.5], 3, 4, 42),
            [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]],
        )
        self.assertEqual(
            weighted_sample_indices(["a", "b", "c"], [1, 3, 2], 3, 7),
            [1, 0, 2],
        )
        self.assertEqual(
            serialize_metrics({"n": 10 ** 100}),
            '{"n":1' + "0" * 100 + "}",
        )


class WeightedSampleScheduleStreamTest(unittest.TestCase):
    """按轮次变化权重的按需逐轮入口
    weighted_sample_schedule_stream /
    weighted_sample_schedule_stream_indices。"""

    ITEMS = list("abcd")
    SCHEDULE = [
        [1, 2, 3, 4],
        [4, 3, 2, 1],
        [0, 1, 3, 5],
        [10 ** 100, 1, 1, 1],
        [Fraction(1, 3), 2, 0, 1],
        [Decimal("1E-50"), 1, 1, 1],
    ]

    def test_stream_matches_batch_round_by_round(self):
        # 相同输入、种子、start、draws 下, 流式物化后与批量入口逐项一致。
        cases = [
            (list("abcdef"),
             [[1, 3, 2, 5, 0, 2], [2, 0, 5, 1, 3, 1], [1, 1, 1, 1, 1, 1]],
             4),
            (list(range(20)),
             [[10 ** 80 + i for i in range(20)]] * 4, 10),
            (["p", "q"], [[0.5, 1.5], [1.5, 0.5], [1, 1]], 2),
            ([], [[]], 0),
            (list("xyz"),
             [[10 ** 100, 1, 10 ** 50], [1, 1, 1], [3, 0, 2]], 2),
            (["a", "b", "c"],
             [[2, Fraction(1), 0.5], [Decimal("1.5"), 0.5, 2], [1, 2, 3]],
             3),
        ]
        for items, schedule, k in cases:
            for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
                d = len(schedule)
                with self.subTest(items=items, k=k, seed=seed):
                    self.assertEqual(
                        list(weighted_sample_schedule_stream_indices(
                            items, schedule, k, d, seed)),
                        weighted_sample_schedule_indices(
                            items, schedule, k, d, seed),
                    )
                    self.assertEqual(
                        list(weighted_sample_schedule_stream(
                            items, schedule, k, d, seed)),
                        weighted_sample_schedule(
                            items, schedule, k, d, seed),
                    )

    def test_start_window_matches_slice_of_full_run(self):
        # start 只跳过完整轮次: 流式窗口与 start=0 完整批量结果按
        # [start, start+draws) 切片逐项一致。
        full = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 2, 6, 99)
        for start in range(6):
            for draws in range(0, 6 - start + 1):
                with self.subTest(start=start, draws=draws):
                    self.assertEqual(
                        list(weighted_sample_schedule_stream_indices(
                            self.ITEMS, self.SCHEDULE, 2, draws, 99, start)),
                        full[start:start + draws],
                    )
                    self.assertEqual(
                        list(weighted_sample_schedule_stream(
                            self.ITEMS, self.SCHEDULE, 2, draws, 99, start)),
                        [[self.ITEMS[i] for i in rd]
                         for rd in full[start:start + draws]],
                    )

    def test_first_round_matches_single_entry(self):
        schedule = [
            [1, 3, 2, 5, 0, 2],
            [2, 0, 5, 1, 3, 1],
            [1, 1, 1, 1, 1, 1],
        ]
        items = list("abcdef")
        for seed in (0, 7, 42, "s", 1.5, True):
            with self.subTest(seed=seed):
                first_i = next(iter(weighted_sample_schedule_stream_indices(
                    items, schedule, 4, 3, seed)))
                self.assertEqual(
                    first_i,
                    weighted_sample_indices(items, schedule[0], 4, seed))
                first_v = next(iter(weighted_sample_schedule_stream(
                    items, schedule, 4, 3, seed)))
                self.assertEqual(
                    first_v, weighted_sample(items, schedule[0], 4, seed))

    def test_returns_iterable_consumed_on_demand(self):
        # 返回可迭代对象而非已物化外层序列; 逐轮消费, 前缀与批量一致。
        stream = weighted_sample_schedule_stream_indices(
            self.ITEMS, self.SCHEDULE, 2, 6, 7)
        self.assertFalse(isinstance(stream, list))
        iterator = iter(stream)
        full = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 2, 6, 7)
        for expected in full[:2]:
            self.assertEqual(next(iterator), expected)
        for expected in full[2:]:
            self.assertEqual(next(iterator), expected)

    def test_values_and_indices_streams_correspond(self):
        idx = list(weighted_sample_schedule_stream_indices(
            self.ITEMS, self.SCHEDULE, 3, 6, 7))
        vals = list(weighted_sample_schedule_stream(
            self.ITEMS, self.SCHEDULE, 3, 6, 7))
        self.assertEqual(vals, [[self.ITEMS[i] for i in rd] for rd in idx])

    def test_each_round_restarts_and_zero_weight_excluded(self):
        schedule = [
            [10 ** 100, 1, 10 ** 99, 3, 0, 5],
            [1, 1, 1, 1, 1, 1],
            [5, 0, 3, 1, 10 ** 99, 1],
        ]
        # 每轮权重为零的位置绝不出现: 第 0、2 轮位置 4 权重为零,
        # 第 1 轮位置 2 之外的零权重视各行而定(第 2 轮位置 1 权重为零)。
        forbidden = [{4}, set(), {1}]
        for seed in range(40):
            rounds = list(weighted_sample_schedule_stream_indices(
                list(range(6)), schedule, 5, 3, seed))
            for rd, banned in zip(rounds, forbidden):
                self.assertEqual(len(rd), 5)
                self.assertEqual(len(set(rd)), 5)
                self.assertTrue(all(0 <= i < 6 for i in rd))
                self.assertTrue(not (set(rd) & banned))
        # 某轮只有一个正权重位置: 该轮必选它, 轮间可重复同位置。
        only_one = [[0, 5, 0], [1, 0, 0], [0, 0, 7]]
        for seed in range(20):
            self.assertEqual(
                list(weighted_sample_schedule_stream_indices(
                    list("abc"), only_one, 1, 3, seed)),
                [[1], [0], [2]],
            )

    def test_duplicate_values_distinct_positions(self):
        idx = list(weighted_sample_schedule_stream_indices(
            [1, 1, 1], [[1, 1, 1], [3, 2, 1]], 3, 2, 123))
        vals = list(weighted_sample_schedule_stream(
            [1, 1, 1], [[1, 1, 1], [3, 2, 1]], 3, 2, 123))
        self.assertTrue(all(sorted(rd) == [0, 1, 2] for rd in idx))
        self.assertEqual(vals, [[1, 1, 1], [1, 1, 1]])

    def test_draws_zero_validates_then_yields_nothing(self):
        self.assertEqual(
            list(weighted_sample_schedule_stream_indices(
                ["a", "b"], [[1, 2], [3, 4]], 2, 0, 0)),
            [],
        )
        self.assertEqual(
            list(weighted_sample_schedule_stream(
                ["a", "b"], [[1, 2]], 2, 0, 0)),
            [],
        )
        # draws=0 仍须完成全部校验, 且在调用当场抛出(不等到迭代)。
        with self.assertRaises(TypeError):
            weighted_sample_schedule_stream_indices(
                "ab", [[1, 2]], 1, 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_stream_indices(
                ["a", "b"], "xx", 1, 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_stream_indices(
                ["a", "b"], [[1, "x"]], 1, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_stream_indices(
                ["a", "b"], [[1]], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_stream_indices(
                ["a"], [[float("nan")]], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_stream_indices(
                ["a", "b"], [[1, 0]], 2, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_stream_indices(
                ["a", "b"], [[1, 2]], 1, 0, 0, start=2)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_stream(
                ["a"], [True], 0, 0, 0)

    def test_k_zero_yields_empty_lists_without_rng_consumption(self):
        schedule = [[0, 0], [1, 2], [0, 0]]
        self.assertEqual(
            list(weighted_sample_schedule_stream_indices(
                ["a", "b"], schedule, 0, 3, 5)),
            [[], [], []],
        )
        self.assertEqual(
            list(weighted_sample_schedule_stream(
                ["a", "b"], schedule, 0, 2, 5, start=1)),
            [[], []],
        )
        # k=0 时即使某行权重全为零也合法; 空 items / 空行同样合法。
        self.assertEqual(
            list(weighted_sample_schedule_stream_indices(
                [], [[]], 0, 1, 0)),
            [[]],
        )

    def test_validation_fails_at_call_time_not_mid_iteration(self):
        def expect_raises(exc, fn, *args):
            with self.assertRaises(exc):
                fn(*args)  # 调用本身就必须抛出

        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, 0], [1, 1]], 2, 1, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, 1], [0, 0]], 1, 2, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream,
            ["a", "b"], [[1, 1], [0, 0]], 1, 1, 0)
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, "x"]], 1, 1, 0)
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, True]], 1, 1, 0)
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, 1]], True, 1, 0)
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, 1]], 1, 1, object())
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, 1]], 0, True, 0)
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, 1]], 0, 1.0, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, 1]], 0, -1, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, -1]], 1, 1, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1, float("inf")]], 1, 1, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a", "b"], [[1]], 1, 1, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a"], [[1]], 2, 1, 0)
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            iter(["a"]), [[1]], 0, 1, 0)
        expect_raises(
            TypeError, weighted_sample_schedule_stream_indices,
            ["a"], [iter([1])], 0, 1, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream_indices,
            ["a"], [[Decimal("NaN")]], 0, 0, 0)
        expect_raises(
            ValueError, weighted_sample_schedule_stream,
            ["a"], [[Decimal("Infinity")]], 1, 1, 0)

    def test_window_out_of_range_at_call_time(self):
        schedule = [[1, 2], [2, 1]]
        with self.assertRaises(ValueError):
            weighted_sample_schedule_stream_indices(
                ["a", "b"], schedule, 1, 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_stream_indices(
                ["a", "b"], schedule, 1, 1, 0, start=2)
        # 恰好覆盖整个 schedule 合法, 且流式结果与批量一致。
        self.assertEqual(
            list(weighted_sample_schedule_stream_indices(
                ["a", "b"], schedule, 1, 1, 0, start=1)),
            weighted_sample_schedule_indices(
                ["a", "b"], schedule, 1, 1, 0, start=1),
        )

    def test_inputs_and_schedule_not_mutated(self):
        items = list("abc")
        schedule = [[10 ** 100, 2, 3], [Fraction(1, 2), 0, 1],
                    [Decimal("0.5"), 1, 1]]
        items_snap = list(items)
        schedule_snap = [list(row) for row in schedule]
        stream_i = weighted_sample_schedule_stream_indices(
            items, schedule, 2, 3, 99)
        stream_v = weighted_sample_schedule_stream(
            items, schedule, 2, 2, -3, start=1)
        next(iter(stream_i))  # 只消费部分轮次
        list(stream_v)
        self.assertEqual(items, items_snap)
        self.assertEqual(schedule, schedule_snap)

    def test_exact_paths_match_batch(self):
        # 超大整数 / Fraction / Decimal / 浮点溢出场景与批量入口逐项一致。
        cases = [
            (["a", "b"], [[10 ** 400, 10 ** 400], [1, 1]], 2),
            (["H", "t", "z"],
             [[10 ** 100, Decimal("1E-100"), Decimal("-0")], [1, 1, 1]],
             2),
            (["a", "b", "c"],
             [[1e308, 1e308, 1.0], [1.0, 1.0, 1e308]], 3),
            (["a", "b"], [[9, Fraction(1, 100)], [1, 1]], 1),
            (["a", "b"], [[1, Fraction(1, 10 ** 100)]], 1),
        ]
        for items, schedule, k in cases:
            for seed in (0, 7, 2316):
                with self.subTest(k=k, seed=seed):
                    self.assertEqual(
                        list(weighted_sample_schedule_stream_indices(
                            items, schedule, k, len(schedule), seed)),
                        weighted_sample_schedule_indices(
                            items, schedule, k, len(schedule), seed),
                    )

    def test_identical_rows_match_fixed_weight_stream(self):
        # 各行权重完全相同时, 与固定权重流式入口逐轮一致。
        items, weights = list("abcdef"), [1, 3, 2, 5, 0, 2]
        schedule = [list(weights) for _ in range(5)]
        for seed in (0, 42, -7):
            with self.subTest(seed=seed):
                self.assertEqual(
                    list(weighted_sample_schedule_stream_indices(
                        items, schedule, 4, 5, seed)),
                    list(weighted_sample_stream_indices(
                        items, weights, 4, 5, seed)),
                )
                self.assertEqual(
                    list(weighted_sample_schedule_stream(
                        items, schedule, 4, 3, seed, start=2)),
                    list(weighted_sample_stream(
                        items, weights, 4, 3, seed, start=2)),
                )

    def test_seed_none_keeps_random_semantics(self):
        schedule = [list(range(1, 51))] * 4
        rounds = list(weighted_sample_schedule_stream_indices(
            list(range(50)), schedule, 10, 4, None))
        self.assertEqual(len(rounds), 4)
        for rd in rounds:
            self.assertEqual(len(rd), 10)
            self.assertEqual(len(set(rd)), 10)
            self.assertTrue(all(0 <= i < 50 for i in rd))

    def test_results_serialize_exactly(self):
        # 逐轮结果是普通索引/值列表, 可直接交给 serialize_metrics 并无损还原。
        idx = list(weighted_sample_schedule_stream_indices(
            self.ITEMS, self.SCHEDULE, 2, 6, 42))
        self.assertEqual(
            deserialize_metrics(serialize_metrics(idx)), idx)
        vals = list(weighted_sample_schedule_stream(
            self.ITEMS, self.SCHEDULE, 2, 6, 42))
        self.assertEqual(
            deserialize_metrics(serialize_metrics({"rounds": vals})),
            {"rounds": vals},
        )
        # 与批量入口的序列化结果逐字节一致。
        self.assertEqual(
            serialize_metrics(idx),
            serialize_metrics(weighted_sample_schedule_indices(
                self.ITEMS, self.SCHEDULE, 2, 6, 42)),
        )

    def test_existing_entries_unchanged(self):
        self.assertEqual(
            weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42),
            ["green", "red"],
        )
        self.assertEqual(
            weighted_sample_many_indices(
                ["p", "q", "r"], [2, Fraction(1), 0.5], 3, 4, 42),
            [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]],
        )


class WeightedSampleScheduleCountsTest(unittest.TestCase):
    """按轮次变化权重的批量频次入口
    weighted_sample_schedule_counts。"""

    ITEMS = list("abcd")
    SCHEDULE = [
        [1, 2, 3, 4],
        [4, 3, 2, 1],
        [0, 1, 3, 5],
        [10 ** 100, 1, 1, 1],
        [Fraction(1, 3), 2, 0, 1],
        [Decimal("1E-50"), 1, 1, 1],
    ]

    def _flat(self, k, draws, seed=0, start=0):
        rounds = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, k, draws, seed, start)
        flat = [0] * len(self.ITEMS)
        for rd in rounds:
            for pos in rd:
                flat[pos] += 1
        return flat

    def test_counts_equal_flattened_schedule_rounds(self):
        # seed=None 由系统熵播种, 不参与跨调用逐轮一致性比较。
        for seed in (0, 1, 42, -7, 1.5, "s", b"s", bytearray(b"s"), True):
            for k in (0, 1, 2, 3):
                for draws in range(0, 7):
                    with self.subTest(seed=seed, k=k, draws=draws):
                        self.assertEqual(
                            weighted_sample_schedule_counts(
                                self.ITEMS, self.SCHEDULE, k, draws, seed),
                            self._flat(k, draws, seed),
                        )

    def test_seed_none_keeps_random_semantics(self):
        counts = weighted_sample_schedule_counts(
            self.ITEMS, self.SCHEDULE, 3, 6, None)
        self.assertEqual(len(counts), len(self.ITEMS))
        self.assertEqual(sum(counts), 6 * 3)

    def test_counts_shape_and_total(self):
        counts = weighted_sample_schedule_counts(
            self.ITEMS, self.SCHEDULE, 3, 6, 42)
        self.assertIsInstance(counts, list)
        self.assertEqual(len(counts), len(self.ITEMS))
        self.assertTrue(all(isinstance(c, int) for c in counts))
        self.assertEqual(sum(counts), 6 * 3)

    def test_start_window_matches_slice_of_full_run(self):
        # start 只跳过前置完整轮次: 窗口计数与完整序列切片摊平一致。
        full_rounds = weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, 2, 6, 99)
        for start in range(6):
            for draws in range(0, 6 - start + 1):
                flat = [0] * len(self.ITEMS)
                for rd in full_rounds[start:start + draws]:
                    for pos in rd:
                        flat[pos] += 1
                with self.subTest(start=start, draws=draws):
                    self.assertEqual(
                        weighted_sample_schedule_counts(
                            self.ITEMS, self.SCHEDULE, 2, draws, 99, start),
                        flat,
                    )

    def test_identical_rows_match_plain_counts(self):
        # 各行权重相同时与 weighted_sample_counts 同参调用逐项一致。
        cases = [
            (list("abcdef"), [1, 3, 2, 5, 0, 2], 4),
            (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
            (["p", "q"], [0.5, 1.5], 2),
            (list("xyz"), [Fraction(1, 3), 2, Decimal("0.5")], 2),
            (list("ab"), [10 ** 400, 1], 1),
        ]
        for items, weights, k in cases:
            for seed in (0, 7, 123):
                for draws, start in ((5, 0), (3, 2), (1, 4), (0, 0)):
                    schedule = [list(weights) for _ in range(start + draws)]
                    with self.subTest(k=k, seed=seed, draws=draws, start=start):
                        self.assertEqual(
                            weighted_sample_schedule_counts(
                                items, schedule, k, draws, seed, start),
                            weighted_sample_counts(
                                items, weights, k, draws, seed, start),
                        )

    def test_zero_weight_positions_never_counted(self):
        schedule = [[0, 5, 0], [1, 0, 0], [0, 0, 7]]
        for seed in range(50):
            counts = weighted_sample_schedule_counts(
                list("abc"), schedule, 1, 3, seed)
            self.assertEqual(counts, [1, 1, 1])

    def test_duplicate_values_distinct_positions(self):
        items = [1, 1, 1]
        schedule = [[1, 1, 1], [3, 2, 1]]
        counts = weighted_sample_schedule_counts(
            items, schedule, 3, 2, 123)
        # 每轮三个位置全部入选, 每个位置恰好 2 次。
        self.assertEqual(counts, [2, 2, 2])

    def test_k_zero_and_draws_zero_return_zeros_after_validation(self):
        schedule = [[0, 0], [1, 2], [0, 0]]
        self.assertEqual(
            weighted_sample_schedule_counts(["a", "b"], schedule, 0, 3, 5),
            [0, 0],
        )
        self.assertEqual(
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, 0, 2, 5, start=1),
            [0, 0],
        )
        self.assertEqual(
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, 2], [3, 4]], 2, 0, 0),
            [0, 0],
        )
        # k=0 时权重全零的行也合法。
        self.assertEqual(
            weighted_sample_schedule_counts([], [[]], 0, 1, 0), [])
        # draws=0 / k=0 仍完成全部校验。
        with self.assertRaises(TypeError):
            weighted_sample_schedule_counts("ab", [[1, 2]], 1, 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_counts(["a", "b"], "xx", 1, 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, "x"]], 1, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(["a", "b"], [[1]], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a"], [[float("nan")]], 0, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, 0]], 2, 0, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, 2]], 1, 0, 0, start=2)

    def test_validation_matches_schedule_entry(self):
        schedule = [[1, 2], [2, 1]]
        # draws / start 必须是非布尔整数。
        for bad in (True, False, 1.0, "2", None, [2], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_schedule_counts(
                        ["a", "b"], schedule, 1, bad, 0)
                with self.assertRaises(TypeError):
                    weighted_sample_schedule_counts(
                        ["a", "b"], schedule, 1, 1, 0, start=bad)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, 1, -1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, 1, 1, 0, start=-1)
        # 窗口越界。
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, 1, 3, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, 1, 1, 0, start=2)
        # 结构错误。
        for bad_schedule in (
            "not a schedule",
            b"bytes",
            {0: [1, 2]},
            {(1, 2)},
            (w for w in [[1, 2]]),
            [[1, 2], "row"],
            [[1, 2], None],
        ):
            with self.assertRaises(TypeError):
                weighted_sample_schedule_counts(
                    ["a", "b"], bad_schedule, 1, 1, 0)
        # 行长不符。
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, 2], [1, 2, 3]], 1, 2, 0)
        # 权重成员类型错误。
        with self.assertRaises(TypeError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, True]], 1, 1, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, None]], 1, 1, 0)
        # 权重取值错误(窗口外的行同样校验)。
        for bad_schedule in (
            [[1, -1], [1, 1]],
            [[1, 1], [1, -1]],
            [[1, float("nan")], [1, 1]],
            [[1, 1], [float("inf"), 1]],
            [[Decimal("NaN"), 1], [1, 1]],
            [[Fraction(-1, 2), 1], [1, 1]],
        ):
            with self.assertRaises(ValueError):
                weighted_sample_schedule_counts(
                    ["a", "b"], bad_schedule, 1, 1, 0)
        # 任一行(含窗口外行)正权重不足 k 个。
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, 0], [1, 1]], 2, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], [[1, 1], [1, 0]], 2, 1, 0)
        # k / seed 沿用既有规则。
        with self.assertRaises(TypeError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, True, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, -1, 1, 0)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, 3, 1, 0)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_counts(
                ["a", "b"], schedule, 1, 1, object())

    def test_tiny_positive_weights_counted(self):
        # 极小正权重保持候选资格: k=2 时每轮两位置都入选。
        schedule = [
            [Fraction(1, 10 ** 100), 1],
            [Decimal("1E-100"), 1],
        ]
        counts = weighted_sample_schedule_counts(
            ["x", "y"], schedule, 2, 2, 321)
        self.assertEqual(counts, [2, 2])

    def test_exact_path_counts_align_across_rows(self):
        # 各行分别走浮点 / 纯整数路径时仍与摊平的索引入口逐项一致。
        items = list("abcde")
        schedule = [
            [1, 0.5, 2, 1, 3],
            [10 ** 400, 1, 1, 1, 1],
            [Fraction(1, 3), 2, 0, 1, 1],
            [Decimal("1E1000"), 1, 0, 2, 1],
            [1, 2, 3, 4, 5],
        ]
        for k in (1, 2, 4):
            for seed in (0, 42, -9):
                for start in (0, 2):
                    with self.subTest(k=k, seed=seed, start=start):
                        self.assertEqual(
                            weighted_sample_schedule_counts(
                                items, schedule, k, 3, seed, start),
                            self._flat_for(items, schedule, k, 3, seed, start),
                        )

    @staticmethod
    def _flat_for(items, schedule, k, draws, seed, start):
        rounds = weighted_sample_schedule_indices(
            items, schedule, k, draws, seed, start)
        flat = [0] * len(items)
        for rd in rounds:
            for pos in rd:
                flat[pos] += 1
        return flat

    def test_inputs_not_mutated(self):
        items = list("abc")
        schedule = [[10 ** 100, 2, 3], [Fraction(1, 2), 0, 1],
                    [Decimal("0.5"), 1, 1]]
        items_snap = list(items)
        schedule_snap = [list(row) for row in schedule]
        weighted_sample_schedule_counts(items, schedule, 2, 3, 99)
        weighted_sample_schedule_counts(items, schedule, 2, 2, -3, start=1)
        self.assertEqual(items, items_snap)
        self.assertEqual(schedule, schedule_snap)

    def test_counts_serialize_exact_roundtrip(self):
        # 计数是普通任意精度 int, 往返后数值与列表形状保持不变。
        items = ["only", "skip"]
        schedule = [[1, 0]] * 500
        draws = 500
        counts = weighted_sample_schedule_counts(
            items, schedule, 1, draws, 0)
        self.assertEqual(counts, [draws, 0])
        text = serialize_metrics({"counts": counts})
        self.assertNotIn("e", text.lower())
        restored = deserialize_metrics(text)
        self.assertEqual(restored, {"counts": [draws, 0]})
        self.assertIsInstance(restored["counts"][0], int)
        self.assertEqual(len(restored["counts"]), 2)

    def test_deterministic_repeat_calls(self):
        first = weighted_sample_schedule_counts(
            self.ITEMS, self.SCHEDULE, 3, 6, 5)
        for _ in range(4):
            self.assertEqual(
                weighted_sample_schedule_counts(
                    self.ITEMS, self.SCHEDULE, 3, 6, 5),
                first,
            )


class WeightedSampleScheduleCheckpointTest(unittest.TestCase):
    """按轮权重计划的可暂停 / 恢复会话:
    weighted_sample_schedule_checkpoint /
    weighted_sample_schedule_resume_indices /
    weighted_sample_schedule_resume。"""

    ITEMS = list("abcde")
    SCHEDULE = [
        [1, 2, 3, 0, 5],
        [Fraction(1, 3), 0, 2, 7, 1],
        [0.5, 1.5, 0, 2.0, 1.0],
        [10 ** 80, 1, 0, 2, 3],
        [Decimal("0.1"), Decimal("0.2"), 0, Decimal("1E-100"), 1],
        [3, 1, 4, 1, 5],
        [2, 2, 2, 2, 2],
    ]
    K = 3
    SEED = 42

    def _full(self):
        return weighted_sample_schedule_indices(
            self.ITEMS, self.SCHEDULE, self.K, len(self.SCHEDULE), self.SEED)

    def test_checkpoint_state_is_json_native(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=2)
        # 版本 / kind / 位置 / 计划长度 / 指纹 / seed / RNG / 摘要齐备。
        self.assertEqual(state["version"], 1)
        self.assertEqual(state["kind"], "schedule")
        self.assertEqual(state["position"], 2)
        self.assertEqual(state["k"], self.K)
        self.assertEqual(state["n"], len(self.ITEMS))
        self.assertEqual(state["schedule_length"], len(self.SCHEDULE))
        self.assertTrue(json.loads(json.dumps(state)) == state)

    def test_resume_window_equals_one_shot_slice(self):
        full = self._full()
        for start in range(len(self.SCHEDULE) + 1):
            state = weighted_sample_schedule_checkpoint(
                self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=start)
            for draws in range(0, len(self.SCHEDULE) - start + 1):
                with self.subTest(start=start, draws=draws):
                    rounds, next_state = (
                        weighted_sample_schedule_resume_indices(
                            self.ITEMS, self.SCHEDULE, self.K, state, draws)
                    )
                    self.assertEqual(rounds, full[start:start + draws])
                    self.assertEqual(next_state["position"], start + draws)

    def test_chained_resumes_equal_one_shot_run(self):
        full = self._full()
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED)
        chunks = []
        for draws in (1, 2, 1, 3, 0, 0):
            rounds, state = weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, self.K, state, draws)
            chunks.extend(rounds)
        self.assertEqual(chunks, full)
        # 链式结束时位置恰为计划末尾。
        self.assertEqual(state["position"], len(self.SCHEDULE))

    def test_first_round_matches_single_and_schedule_entry(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED)
        rounds, _ = weighted_sample_schedule_resume_indices(
            self.ITEMS, self.SCHEDULE, self.K, state, 1)
        self.assertEqual(
            rounds,
            weighted_sample_schedule_indices(
                self.ITEMS, self.SCHEDULE, self.K, 1, self.SEED),
        )
        self.assertEqual(
            rounds[0],
            weighted_sample_indices(
                self.ITEMS, self.SCHEDULE[0], self.K, self.SEED),
        )

    def test_uniform_rows_match_fixed_weight_resume(self):
        # 各行权重完全相同时, 计划恢复与固定权重批量入口逐轮一致。
        weights = [1, 2, 3, 0, 5]
        schedule = [list(weights) for _ in range(6)]
        full = weighted_sample_schedule_indices(
            self.ITEMS, schedule, 3, 6, seed=99)
        self.assertEqual(
            full,
            weighted_sample_many_indices(self.ITEMS, weights, 3, 6, seed=99),
        )
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, schedule, 3, seed=99, start=2)
        rounds, _ = weighted_sample_schedule_resume_indices(
            self.ITEMS, schedule, 3, state, 4)
        self.assertEqual(rounds, full[2:])

    def test_draws_zero_returns_empty_and_unchanged_state_copy(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=3)
        rounds, next_state = weighted_sample_schedule_resume_indices(
            self.ITEMS, self.SCHEDULE, self.K, state, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)

    def test_k_zero_only_advances_position_without_rng(self):
        items = ["a", "b"]
        schedule = [[1, 2], [3, 4], [5, 6]]
        import random as _random
        fresh = app._rng_state_to_jsonable(_random.Random(7).getstate())
        state = weighted_sample_schedule_checkpoint(
            items, schedule, 0, seed=7, start=1)
        self.assertEqual(state["rng"], fresh)
        rounds, next_state = weighted_sample_schedule_resume_indices(
            items, schedule, 0, state, 2)
        self.assertEqual(rounds, [[], []])
        self.assertEqual(next_state["position"], 3)
        # 随机流未被消耗。
        self.assertEqual(next_state["rng"], state["rng"])

    def test_checkpoint_at_end_of_schedule(self):
        # start == 计划长度允许, 表示整批已完成; 只能再以 draws=0 恢复。
        end = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED,
            start=len(self.SCHEDULE))
        self.assertEqual(end["position"], len(self.SCHEDULE))
        rounds, same = weighted_sample_schedule_resume_indices(
            self.ITEMS, self.SCHEDULE, self.K, end, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(same, end)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, self.K, end, 1)

    def test_value_resume_maps_positions_and_shares_next_state(self):
        items = ["x", "y", "x", "z", "y"]
        state = weighted_sample_schedule_checkpoint(
            items, self.SCHEDULE, self.K, self.SEED, start=1)
        value_rounds, value_next = weighted_sample_schedule_resume(
            items, self.SCHEDULE, self.K, state, 4)
        index_rounds, index_next = weighted_sample_schedule_resume_indices(
            items, self.SCHEDULE, self.K, state, 4)
        self.assertEqual(
            value_rounds,
            [[items[i] for i in rd] for rd in index_rounds],
        )
        # 下一状态逐字段一致, 可互换续接。
        self.assertEqual(value_next, index_next)
        full = weighted_sample_schedule(
            items, self.SCHEDULE, self.K, len(self.SCHEDULE), self.SEED)
        self.assertEqual(value_rounds, full[1:5])

    def test_state_roundtrips_serialize_metrics(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=2)
        restored = deserialize_metrics(serialize_metrics(state))
        full = self._full()
        rounds, next_state = weighted_sample_schedule_resume_indices(
            self.ITEMS, self.SCHEDULE, self.K, restored, 3)
        self.assertEqual(rounds, full[2:5])
        # 下一状态再做一次文本往返后仍可续接。
        again, _ = weighted_sample_schedule_resume_indices(
            self.ITEMS, self.SCHEDULE, self.K,
            deserialize_metrics(serialize_metrics(next_state)), 2)
        self.assertEqual(again, full[5:7])

    def test_rng_words_keep_exact_decimal_integers(self):
        big = [[10 ** 5000, 1, 2], [1, 1, 1]]
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS[:3], big, 2, seed=8, start=1)
        restored = deserialize_metrics(serialize_metrics(state))
        self.assertTrue(all(isinstance(x, int) for x in restored["rng"]["mt"]))
        rounds, _ = weighted_sample_schedule_resume_indices(
            self.ITEMS[:3], big, 2, restored, 1)
        self.assertEqual(
            rounds,
            weighted_sample_schedule_indices(
                self.ITEMS[:3], big, 2, 2, seed=8)[1:],
        )

    # ------------------------------------------------------------------
    # 创建入口: 沿用 schedule 的全部校验
    # ------------------------------------------------------------------
    def test_checkpoint_validation_matches_schedule_entry(self):
        te = lambda fn: self.assertRaises(TypeError, fn)
        ve = lambda fn: self.assertRaises(ValueError, fn)
        items, schedule, k = self.ITEMS, self.SCHEDULE, self.K
        te(lambda: weighted_sample_schedule_checkpoint("abcde", schedule, k, 0))
        te(lambda: weighted_sample_schedule_checkpoint(
            items, iter([list(r) for r in schedule]), k, 0))
        te(lambda: weighted_sample_schedule_checkpoint(
            items, [list(r) for r in schedule] + ["abcde"], k, 0))
        te(lambda: weighted_sample_schedule_checkpoint(
            items, [list(r) for r in schedule] + [iter([1, 2, 3, 4, 5])], k, 0))
        te(lambda: weighted_sample_schedule_checkpoint(items, schedule, True, 0))
        te(lambda: weighted_sample_schedule_checkpoint(items, schedule, 1.0, 0))
        te(lambda: weighted_sample_schedule_checkpoint(
            items, schedule, k, object()))
        te(lambda: weighted_sample_schedule_checkpoint(items, schedule, k, 0, True))
        te(lambda: weighted_sample_schedule_checkpoint(items, schedule, k, 0, 1.0))
        ve(lambda: weighted_sample_schedule_checkpoint(items, schedule, -1, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(items, schedule, 6, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, [[1, 2, 3, 4]], k, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, schedule, k, 0, len(schedule) + 1))
        te(lambda: weighted_sample_schedule_checkpoint(
            items, [[1, True, 3, 0, 5]], k, 0))
        te(lambda: weighted_sample_schedule_checkpoint(
            items, [[1, "x", 3, 0, 5]], k, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, [[1, -2, 3, 0, 5]], k, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, [[1, float("nan"), 3, 0, 5]], k, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, [[1, float("inf"), 3, 0, 5]], k, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, [[Decimal("NaN"), 1, 1, 1, 1]], k, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, [[0, 0, 0, 0, 0]], 1, 0))
        ve(lambda: weighted_sample_schedule_checkpoint(
            items, [[1, 0, 0, 0, 0], [0, 0, 0, 0, 0]], 1, 0))
        # k=0 时全零行合法。
        zero_state = weighted_sample_schedule_checkpoint(
            items, [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]], 0, seed=1)
        self.assertEqual(zero_state["position"], 0)

    def test_checkpoint_does_not_mutate_inputs(self):
        items = list(self.ITEMS)
        schedule = [list(r) for r in self.SCHEDULE]
        items_snap = list(items)
        schedule_snap = [list(r) for r in schedule]
        weighted_sample_schedule_checkpoint(
            items, schedule, self.K, self.SEED, start=4)
        self.assertEqual(items, items_snap)
        self.assertEqual(schedule, schedule_snap)

    # ------------------------------------------------------------------
    # 恢复: 状态类型 / 结构 / 摘要 / 输入绑定
    # ------------------------------------------------------------------
    def test_non_mapping_state_raises_type_error(self):
        for bad in (None, [], "{}", 1, True, (), {1, 2}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_schedule_resume_indices(
                        self.ITEMS, self.SCHEDULE, self.K, bad, 1)

    def test_draws_type_and_value_rules(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED)
        for bad in (True, False, 1.0, "1", None, [1], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_schedule_resume_indices(
                        self.ITEMS, self.SCHEDULE, self.K, state, bad)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, self.K, state, -1)

    def test_resume_window_out_of_range_raises_value_error(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=5)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, self.K, state, 3)

    def test_invalid_state_structure_raises_value_error(self):
        import copy as _copy
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=1)

        def ve(mutator):
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_schedule_resume_indices(
                    self.ITEMS, self.SCHEDULE, self.K, bad, 1)

        ve(lambda s: s.pop("version"))
        ve(lambda s: s.pop("kind"))
        ve(lambda s: s.pop("rng"))
        ve(lambda s: s.update(extra=1))
        ve(lambda s: s.update(position=-1))
        ve(lambda s: s.update(position=True))
        ve(lambda s: s.update(k=True))
        ve(lambda s: s.update(n=-1))
        ve(lambda s: s.update(schedule_length=-1))
        ve(lambda s: s.update(kind="fixed"))
        ve(lambda s: s.update(items_digest=1))
        ve(lambda s: s.update(seed=["z", 1]))
        ve(lambda s: s.update(rng={"v": 3}))
        ve(lambda s: s.update(digest=1))

    def test_unsupported_version_raises_value_error(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED)
        for bad_version in (0, 2, 99, True, "1", 1.0):
            bad = dict(state)
            bad["version"] = bad_version
            with self.subTest(bad_version=bad_version):
                with self.assertRaises(ValueError):
                    weighted_sample_schedule_resume_indices(
                        self.ITEMS, self.SCHEDULE, self.K, bad, 1)

    def test_state_mismatch_with_inputs_raises_value_error(self):
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=1)

        def ve(label, i2, s2, k2):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    weighted_sample_schedule_resume_indices(i2, s2, k2, state, 1)

        ve("k differs", self.ITEMS, self.SCHEDULE, 2)
        ve("items differ", list("abcdf"), self.SCHEDULE, self.K)
        ve("a row differs", self.ITEMS,
           [list(r) for r in self.SCHEDULE[:-1]] + [[9, 9, 9, 9, 9]], self.K)
        # 同值不同类型(1 -> 1.0)可能改变抽样计划, 必须视为不匹配。
        swapped = [list(r) for r in self.SCHEDULE]
        swapped[0][0] = 1.0
        ve("weight type swap", self.ITEMS, swapped, self.K)
        # 调换两行改变第 j 轮使用的权重。
        reordered = [list(r) for r in self.SCHEDULE]
        reordered[0], reordered[1] = reordered[1], reordered[0]
        ve("row order", self.ITEMS, reordered, self.K)
        # 追加一行改变计划长度。
        ve("extra row", self.ITEMS,
           [list(r) for r in self.SCHEDULE] + [[1, 1, 1, 1, 1]], self.K)
        # 少一行同样不匹配。
        ve("missing row", self.ITEMS, self.SCHEDULE[:-1], self.K)

    def test_tampered_fields_without_valid_digest_raise_value_error(self):
        import copy as _copy
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=1)

        def ve(mutator):
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_schedule_resume_indices(
                    self.ITEMS, self.SCHEDULE, self.K, bad, 1)

        ve(lambda s: s.update(position=s["position"] + 1))
        ve(lambda s: s.update(schedule_length=s["schedule_length"] + 1))
        ve(lambda s: s["rng"]["mt"].__setitem__(0, s["rng"]["mt"][0] ^ 1))
        ve(lambda s: s.update(digest="0" * 64))
        ve(lambda s: s.update(seed=["i", 123]))

    def test_out_of_range_rng_state_raises_value_error_even_with_digest(self):
        # 即使重算了绑定摘要, 越界 MT 状态字/索引也必须统一抛 ValueError。
        import copy as _copy
        from app import _schedule_checkpoint_binding_digest
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED)
        for pos, value in (
            (0, 10 ** 40), (1, -5), (623, 1 << 32), (624, 625), (624, -1),
        ):
            bad = _copy.deepcopy(state)
            bad["rng"]["mt"][pos] = value
            bad["digest"] = _schedule_checkpoint_binding_digest(
                bad["seed"], bad["position"], bad["k"], bad["n"],
                bad["schedule_length"], bad["items_digest"],
                bad["schedule_digest"], bad["rng"],
            )
            with self.subTest(pos=pos, value=value):
                with self.assertRaises(ValueError):
                    weighted_sample_schedule_resume_indices(
                        self.ITEMS, self.SCHEDULE, self.K, bad, 1)

    def test_other_kinds_of_checkpoint_state_rejected(self):
        # 固定权重 / 排除会话的状态不能用于按轮计划恢复, 反之亦然。
        schedule_state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=1)
        fixed_state = weighted_sample_checkpoint(
            self.ITEMS, self.SCHEDULE[0], self.K, self.SEED, start=1)
        excluding_state = weighted_sample_excluding_checkpoint(
            self.ITEMS, self.SCHEDULE[0], self.K, (), self.SEED, start=1)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, self.K, fixed_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, self.K, excluding_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_resume_indices(
                self.ITEMS, self.SCHEDULE[0], self.K, schedule_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_resume_indices(
                self.ITEMS, self.SCHEDULE[0], self.K, (), schedule_state, 1)

    def test_value_entry_validates_inputs_before_mapping(self):
        # 值入口先按 schedule 入口校验 items/schedule/k, 再要求 state 是
        # 映射并校验 draws —— 损坏的状态不能掩盖非法输入。
        with self.assertRaises(TypeError):
            weighted_sample_schedule_resume(
                "abcde", self.SCHEDULE, self.K, "not-a-mapping", 1)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume(
                self.ITEMS, [[0, 0, 0, 0, 0]], 1, "not-a-mapping", 1)
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_resume(
                self.ITEMS, self.SCHEDULE, self.K, [], 1)
        with self.assertRaises(TypeError):
            weighted_sample_schedule_resume(
                self.ITEMS, self.SCHEDULE, self.K, state, True)

    def test_no_rounds_partially_returned_on_failure(self):
        # 恢复窗口越界时即使能抽出前面的轮次, 也不返回部分结果。
        state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, self.K, self.SEED, start=5)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, self.K, state, 3)

    def test_float_str_and_none_seeds_resume_consistently(self):
        for seed in (1.5, "hello", -0.0, float("nan")):
            state = weighted_sample_schedule_checkpoint(
                self.ITEMS, self.SCHEDULE, 1, seed, start=1)
            rounds, _ = weighted_sample_schedule_resume_indices(
                self.ITEMS, self.SCHEDULE, 1, state, 2)
            self.assertEqual(
                rounds,
                weighted_sample_schedule_indices(
                    self.ITEMS, self.SCHEDULE, 1, 3, seed)[1:],
            )
        # None 种子来自系统熵: 同一份快照无论恢复多少次都给出同一序列。
        none_state = weighted_sample_schedule_checkpoint(
            self.ITEMS, self.SCHEDULE, 1, None, start=1)
        payload = json.loads(json.dumps(none_state))
        a, _ = weighted_sample_schedule_resume_indices(
            self.ITEMS, self.SCHEDULE, 1, payload, 2)
        b, _ = weighted_sample_schedule_resume_indices(
            self.ITEMS, self.SCHEDULE, 1,
            json.loads(json.dumps(none_state)), 2)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 2)


class WeightedSampleKScheduleCheckpointTest(unittest.TestCase):
    """按轮样本数计划的可暂停 / 恢复会话:
    weighted_sample_k_schedule_checkpoint /
    weighted_sample_k_schedule_resume_indices /
    weighted_sample_k_schedule_resume。"""

    ITEMS = list("abcde")
    WEIGHTS = [1, 2, 3, 0, 5]
    K_SCHEDULE = [3, 0, 2, 1, 3, 0, 2]
    SEED = 42

    def _full(self):
        return weighted_sample_k_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE,
            len(self.K_SCHEDULE), self.SEED)

    def test_checkpoint_state_is_json_native(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=2)
        # 版本 / kind / 位置 / 计划长度 / 指纹 / 抽样路径标记 / seed / RNG /
        # 摘要齐备。
        self.assertEqual(state["version"], 1)
        self.assertEqual(state["kind"], "k_schedule")
        self.assertEqual(state["position"], 2)
        self.assertEqual(state["n"], len(self.ITEMS))
        self.assertEqual(state["schedule_length"], len(self.K_SCHEDULE))
        self.assertIs(state["exact"], False)
        self.assertTrue(json.loads(json.dumps(state)) == state)

    def test_resume_window_equals_one_shot_slice(self):
        full = self._full()
        for start in range(len(self.K_SCHEDULE) + 1):
            state = weighted_sample_k_schedule_checkpoint(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED,
                start=start)
            for draws in range(0, len(self.K_SCHEDULE) - start + 1):
                with self.subTest(start=start, draws=draws):
                    rounds, next_state = (
                        weighted_sample_k_schedule_resume_indices(
                            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE,
                            state, draws)
                    )
                    self.assertEqual(rounds, full[start:start + draws])
                    self.assertEqual(next_state["position"], start + draws)

    def test_chained_resumes_equal_one_shot_run(self):
        full = self._full()
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED)
        chunks = []
        for draws in (1, 2, 1, 3, 0, 0):
            rounds, state = weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, draws)
            chunks.extend(rounds)
        self.assertEqual(chunks, full)
        # 链式结束时位置恰为计划末尾。
        self.assertEqual(state["position"], len(self.K_SCHEDULE))

    def test_first_round_matches_k_schedule_entry(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED)
        rounds, _ = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, 1)
        self.assertEqual(
            rounds,
            weighted_sample_k_schedule_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, 1, self.SEED),
        )
        self.assertEqual(
            rounds[0],
            weighted_sample_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE[0], self.SEED),
        )

    def test_uniform_plan_matches_fixed_k_entries(self):
        # 计划各项都等于 k 时, 与固定 k 的批量 / 流式 / 计数入口逐轮一致。
        k_schedule = [2] * 6
        full = weighted_sample_k_schedule_indices(
            self.ITEMS, self.WEIGHTS, k_schedule, 6, seed=99)
        self.assertEqual(
            full,
            weighted_sample_many_indices(
                self.ITEMS, self.WEIGHTS, 2, 6, seed=99),
        )
        self.assertEqual(
            full,
            list(weighted_sample_k_schedule_stream_indices(
                self.ITEMS, self.WEIGHTS, k_schedule, 6, seed=99)),
        )
        counts = weighted_sample_k_schedule_counts(
            self.ITEMS, self.WEIGHTS, k_schedule, 6, seed=99)
        flat = [0] * len(self.ITEMS)
        for rd in full:
            for pos in rd:
                flat[pos] += 1
        self.assertEqual(counts, flat)
        # 分段恢复同样落在同一窗口上。
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, k_schedule, seed=99, start=2)
        rounds, _ = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, k_schedule, state, 4)
        self.assertEqual(rounds, full[2:])

    def test_draws_zero_returns_empty_and_unchanged_state_copy(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=3)
        rounds, next_state = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)

    def test_zero_k_rounds_do_not_consume_rng(self):
        import random as _random
        fresh = app._rng_state_to_jsonable(_random.Random(7).getstate())
        # 全零计划: 跳轮与产轮都不消耗随机流。
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, [0, 0, 0], seed=7, start=2)
        self.assertEqual(state["rng"], fresh)
        rounds, next_state = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, [0, 0, 0], state, 1)
        self.assertEqual(rounds, [[]])
        self.assertEqual(next_state["position"], 3)
        self.assertEqual(next_state["rng"], state["rng"])
        # 混合计划中的零轮同样只推进位置。
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=1)
        rounds, next_state = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, 1)
        self.assertEqual(rounds, [[]])
        self.assertEqual(next_state["rng"], state["rng"])

    def test_checkpoint_at_end_of_schedule(self):
        # start == 计划长度允许, 表示整批已完成; 只能再以 draws=0 恢复。
        end = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED,
            start=len(self.K_SCHEDULE))
        self.assertEqual(end["position"], len(self.K_SCHEDULE))
        rounds, same = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, end, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(same, end)
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, end, 1)

    def test_value_resume_maps_positions_and_shares_next_state(self):
        items = ["x", "y", "x", "z", "y"]
        state = weighted_sample_k_schedule_checkpoint(
            items, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=1)
        value_rounds, value_next = weighted_sample_k_schedule_resume(
            items, self.WEIGHTS, self.K_SCHEDULE, state, 4)
        index_rounds, index_next = weighted_sample_k_schedule_resume_indices(
            items, self.WEIGHTS, self.K_SCHEDULE, state, 4)
        self.assertEqual(
            value_rounds,
            [[items[i] for i in rd] for rd in index_rounds],
        )
        # 下一状态逐字段一致, 可互换续接。
        self.assertEqual(value_next, index_next)
        full = weighted_sample_k_schedule(
            items, self.WEIGHTS, self.K_SCHEDULE,
            len(self.K_SCHEDULE), self.SEED)
        self.assertEqual(value_rounds, full[1:5])

    def test_state_roundtrips_serialize_metrics(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=2)
        restored = deserialize_metrics(serialize_metrics(state))
        full = self._full()
        rounds, next_state = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, restored, 3)
        self.assertEqual(rounds, full[2:5])
        # 下一状态再做一次文本往返后仍可续接。
        again, _ = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE,
            deserialize_metrics(serialize_metrics(next_state)), 2)
        self.assertEqual(again, full[5:7])

    def test_rng_words_keep_exact_decimal_integers(self):
        big_weights = [10 ** 5000, 1, 2, 0, 3]
        k_schedule = [2, 1, 0, 2]
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, big_weights, k_schedule, seed=8, start=1)
        self.assertIs(state["exact"], True)
        restored = deserialize_metrics(serialize_metrics(state))
        self.assertTrue(all(isinstance(x, int) for x in restored["rng"]["mt"]))
        rounds, _ = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, big_weights, k_schedule, restored, 3)
        self.assertEqual(
            rounds,
            weighted_sample_k_schedule_indices(
                self.ITEMS, big_weights, k_schedule, 4, seed=8)[1:],
        )

    def test_fraction_decimal_weights_resume_consistently(self):
        weights = [Decimal("0.1"), Fraction(1, 3), 0.5, 0, 2]
        k_schedule = [2, 0, 3, 1]
        full = weighted_sample_k_schedule_indices(
            self.ITEMS, weights, k_schedule, 4, seed=11)
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, weights, k_schedule, seed=11, start=1)
        self.assertIs(state["exact"], True)
        rounds, _ = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, weights, k_schedule, state, 3)
        self.assertEqual(rounds, full[1:])

    # ------------------------------------------------------------------
    # 创建入口: 沿用 k_schedule 批量入口的全部校验
    # ------------------------------------------------------------------
    def test_checkpoint_validation_matches_k_schedule_entry(self):
        te = lambda fn: self.assertRaises(TypeError, fn)
        ve = lambda fn: self.assertRaises(ValueError, fn)
        items, weights, ks = self.ITEMS, self.WEIGHTS, self.K_SCHEDULE
        te(lambda: weighted_sample_k_schedule_checkpoint(
            "abcde", weights, ks, 0))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, "12345", ks, 0))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, iter(ks), 0))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, "3021", 0))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, [1, True, 2], 0))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, [1, 1.0, 2], 0))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, ks, object()))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, ks, 0, True))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, ks, 0, 1.0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights[:-1], ks, 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, [-1, 1], 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, [len(items) + 1], 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, ks, 0, len(ks) + 1))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, [1, True, 3, 0, 5], ks, 0))
        te(lambda: weighted_sample_k_schedule_checkpoint(
            items, [1, "x", 3, 0, 5], ks, 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, [1, -2, 3, 0, 5], ks, 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, [1, float("nan"), 3, 0, 5], ks, 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, [1, float("inf"), 3, 0, 5], ks, 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, [Decimal("NaN"), 1, 1, 1, 1], ks, 0))
        # 任一轮样本数超过正权重位置数都拒绝(正权重共 4 个)。
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, weights, [5], 0))
        ve(lambda: weighted_sample_k_schedule_checkpoint(
            items, [1, 0, 0, 0, 0], [0, 2], 0))
        # 全零计划在零权重下也合法。
        zero_state = weighted_sample_k_schedule_checkpoint(
            items, [0, 0, 0, 0, 0], [0, 0], seed=1)
        self.assertEqual(zero_state["position"], 0)

    def test_checkpoint_does_not_mutate_inputs(self):
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        k_schedule = list(self.K_SCHEDULE)
        weighted_sample_k_schedule_checkpoint(
            items, weights, k_schedule, self.SEED, start=4)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(k_schedule, self.K_SCHEDULE)

    # ------------------------------------------------------------------
    # 恢复: 状态类型 / 结构 / 摘要 / 输入绑定
    # ------------------------------------------------------------------
    def test_non_mapping_state_raises_type_error(self):
        for bad in (None, [], "{}", 1, True, (), {1, 2}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_k_schedule_resume_indices(
                        self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, bad, 1)

    def test_draws_type_and_value_rules(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED)
        for bad in (True, False, 1.0, "1", None, [1], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_k_schedule_resume_indices(
                        self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, bad)
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, -1)

    def test_resume_window_out_of_range_raises_value_error(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=5)
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, 3)

    def test_invalid_state_structure_raises_value_error(self):
        import copy as _copy
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=1)

        def ve(mutator):
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_k_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, bad, 1)

        ve(lambda s: s.pop("version"))
        ve(lambda s: s.pop("kind"))
        ve(lambda s: s.pop("rng"))
        ve(lambda s: s.pop("k_schedule_digest"))
        ve(lambda s: s.update(extra=1))
        ve(lambda s: s.update(position=-1))
        ve(lambda s: s.update(position=True))
        ve(lambda s: s.update(n=-1))
        ve(lambda s: s.update(schedule_length=-1))
        ve(lambda s: s.update(kind="schedule"))
        ve(lambda s: s.update(exact=1))
        ve(lambda s: s.update(items_digest=1))
        ve(lambda s: s.update(k_schedule_digest=1))
        ve(lambda s: s.update(seed=["z", 1]))
        ve(lambda s: s.update(rng={"v": 3}))
        ve(lambda s: s.update(digest=1))

    def test_unsupported_version_raises_value_error(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED)
        for bad_version in (0, 2, 99, True, "1", 1.0):
            bad = dict(state)
            bad["version"] = bad_version
            with self.subTest(bad_version=bad_version):
                with self.assertRaises(ValueError):
                    weighted_sample_k_schedule_resume_indices(
                        self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, bad, 1)

    def test_state_mismatch_with_inputs_raises_value_error(self):
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=1)

        def ve(label, i2, w2, ks2):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    weighted_sample_k_schedule_resume_indices(
                        i2, w2, ks2, state, 1)

        ve("items differ", list("abcdf"), self.WEIGHTS, self.K_SCHEDULE)
        ve("weights differ", self.ITEMS, [1, 2, 3, 0, 6], self.K_SCHEDULE)
        # 同值不同类型(1 -> 1.0)可能改变抽样路径, 必须视为不匹配。
        ve("weight type swap", self.ITEMS, [1.0, 2, 3, 0, 5], self.K_SCHEDULE)
        # 调换、改动、增删计划项都改变计划指纹。
        reordered = list(self.K_SCHEDULE)
        reordered[0], reordered[2] = reordered[2], reordered[0]
        ve("plan order", self.ITEMS, self.WEIGHTS, reordered)
        changed = list(self.K_SCHEDULE)
        changed[0] += 1
        ve("plan member", self.ITEMS, self.WEIGHTS, changed)
        ve("extra member", self.ITEMS, self.WEIGHTS,
           list(self.K_SCHEDULE) + [1])
        ve("missing member", self.ITEMS, self.WEIGHTS, self.K_SCHEDULE[:-1])

    def test_tampered_fields_without_valid_digest_raise_value_error(self):
        import copy as _copy
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=1)

        def ve(mutator):
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_k_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, bad, 1)

        ve(lambda s: s.update(position=s["position"] + 1))
        ve(lambda s: s.update(schedule_length=s["schedule_length"] + 1))
        ve(lambda s: s.update(exact=not s["exact"]))
        ve(lambda s: s["rng"]["mt"].__setitem__(0, s["rng"]["mt"][0] ^ 1))
        ve(lambda s: s.update(digest="0" * 64))
        ve(lambda s: s.update(seed=["i", 123]))

    def test_sampling_plan_marker_mismatch_raises_value_error(self):
        # 抽样路径标记与权重推出的计划不一致时, 即使重算了摘要也拒绝。
        import copy as _copy
        from app import _k_schedule_checkpoint_binding_digest
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED)
        bad = _copy.deepcopy(state)
        bad["exact"] = not bad["exact"]
        bad["digest"] = _k_schedule_checkpoint_binding_digest(
            bad["seed"], bad["position"], bad["n"], bad["schedule_length"],
            bad["items_digest"], bad["weights_digest"],
            bad["k_schedule_digest"], bad["exact"], bad["rng"],
        )
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, bad, 1)

    def test_out_of_range_rng_state_raises_value_error_even_with_digest(self):
        # 即使重算了绑定摘要, 越界 MT 状态字/索引也必须统一抛 ValueError。
        import copy as _copy
        from app import _k_schedule_checkpoint_binding_digest
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED)
        for pos, value in (
            (0, 10 ** 40), (1, -5), (623, 1 << 32), (624, 625), (624, -1),
        ):
            bad = _copy.deepcopy(state)
            bad["rng"]["mt"][pos] = value
            bad["digest"] = _k_schedule_checkpoint_binding_digest(
                bad["seed"], bad["position"], bad["n"],
                bad["schedule_length"], bad["items_digest"],
                bad["weights_digest"], bad["k_schedule_digest"],
                bad["exact"], bad["rng"],
            )
            with self.subTest(pos=pos, value=value):
                with self.assertRaises(ValueError):
                    weighted_sample_k_schedule_resume_indices(
                        self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, bad, 1)

    def test_other_kinds_of_checkpoint_state_rejected(self):
        # 固定权重 / 按轮权重计划 / 排除会话的状态不能用于本计划恢复。
        k_schedule_state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=1)
        fixed_state = weighted_sample_checkpoint(
            self.ITEMS, self.WEIGHTS, 2, self.SEED, start=1)
        schedule_state = weighted_sample_schedule_checkpoint(
            self.ITEMS, [self.WEIGHTS] * 3, 2, self.SEED, start=1)
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, fixed_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, schedule_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_resume_indices(
                self.ITEMS, self.WEIGHTS, 2, k_schedule_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, [self.WEIGHTS] * 3, 2, k_schedule_state, 1)

    def test_value_entry_validates_inputs_before_mapping(self):
        # 值入口先按 k_schedule 入口校验 items/weights/k_schedule, 再要求
        # state 是映射并校验 draws —— 损坏的状态不能掩盖非法输入。
        with self.assertRaises(TypeError):
            weighted_sample_k_schedule_resume(
                "abcde", self.WEIGHTS, self.K_SCHEDULE, "not-a-mapping", 1)
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume(
                self.ITEMS, [0, 0, 0, 0, 0], [1], "not-a-mapping", 1)
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_k_schedule_resume(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, [], 1)
        with self.assertRaises(TypeError):
            weighted_sample_k_schedule_resume(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, True)

    def test_no_rounds_partially_returned_on_failure(self):
        # 恢复窗口越界时即使能抽出前面的轮次, 也不返回部分结果。
        state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, self.SEED, start=5)
        with self.assertRaises(ValueError):
            weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, 3)

    def test_resume_does_not_mutate_inputs_or_state(self):
        import copy as _copy
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        k_schedule = list(self.K_SCHEDULE)
        state = weighted_sample_k_schedule_checkpoint(
            items, weights, k_schedule, self.SEED, start=1)
        snapshot = _copy.deepcopy(state)
        weighted_sample_k_schedule_resume_indices(
            items, weights, k_schedule, state, 2)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(k_schedule, self.K_SCHEDULE)
        self.assertEqual(state, snapshot)

    def test_float_str_and_none_seeds_resume_consistently(self):
        for seed in (1.5, "hello", -0.0, float("nan")):
            state = weighted_sample_k_schedule_checkpoint(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, seed, start=1)
            rounds, _ = weighted_sample_k_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, state, 2)
            self.assertEqual(
                rounds,
                weighted_sample_k_schedule_indices(
                    self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, 3, seed)[1:],
            )
        # None 种子来自系统熵: 同一份快照无论恢复多少次都给出同一序列。
        none_state = weighted_sample_k_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, None, start=1)
        payload = json.loads(json.dumps(none_state))
        a, _ = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE, payload, 2)
        b, _ = weighted_sample_k_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.K_SCHEDULE,
            json.loads(json.dumps(none_state)), 2)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 2)


class WeightedSamplePartitionTest(unittest.TestCase):
    """分组采样与可暂停 / 恢复的分组会话:
    weighted_sample_partition_indices / weighted_sample_partition /
    weighted_sample_partition_checkpoint /
    weighted_sample_partition_resume_indices /
    weighted_sample_partition_resume。"""

    ITEMS = list("abcdef")
    WEIGHTS = [1, 3, 0, 2, 5, 0]
    GROUP_SIZES = [2, 1, 0, 1]
    SEED = 42

    def _flat_reference(self):
        return weighted_sample_indices(
            self.ITEMS, self.WEIGHTS, sum(self.GROUP_SIZES), self.SEED)

    def _full(self):
        return weighted_sample_partition_indices(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED)

    # ------------------------------------------------------------------
    # 一次性分组入口
    # ------------------------------------------------------------------
    def test_groups_split_the_single_without_replacement_sequence(self):
        groups = self._full()
        self.assertEqual([len(g) for g in groups], self.GROUP_SIZES)
        # 各组拼接逐项等于 weighted_sample_indices 的无放回序列。
        self.assertEqual(
            [position for group in groups for position in group],
            self._flat_reference(),
        )
        # 所有组互不重叠, 且零权重位置(2、5)永不出现。
        flattened = [position for group in groups for position in group]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertNotIn(2, flattened)
        self.assertNotIn(5, flattened)

    def test_values_entry_maps_positions(self):
        index_groups = self._full()
        value_groups = weighted_sample_partition(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED)
        self.assertEqual(
            value_groups,
            [[self.ITEMS[i] for i in group] for group in index_groups],
        )

    def test_duplicate_values_are_distinct_positions(self):
        items = ["x", "y", "x", "z", "y", "q"]
        index_groups = weighted_sample_partition_indices(
            items, self.WEIGHTS, [2, 2], seed=5)
        value_groups = weighted_sample_partition(
            items, self.WEIGHTS, [2, 2], seed=5)
        self.assertEqual(
            value_groups,
            [[items[i] for i in group] for group in index_groups],
        )

    def test_empty_plan_and_zero_sizes_after_validation(self):
        self.assertEqual(
            weighted_sample_partition_indices(
                self.ITEMS, self.WEIGHTS, [], self.SEED),
            [],
        )
        self.assertEqual(
            weighted_sample_partition_indices(
                self.ITEMS, self.WEIGHTS, [0, 0, 0], self.SEED),
            [[], [], []],
        )
        # 权重总量为零但总组大小也为零: 完成校验后返回对应数量的空组。
        self.assertEqual(
            weighted_sample_partition_indices(
                self.ITEMS, [0] * len(self.ITEMS), [0, 0], self.SEED),
            [[], []],
        )
        self.assertEqual(
            weighted_sample_partition(
                self.ITEMS, [0] * len(self.ITEMS), [0, 0], self.SEED),
            [[], []],
        )

    def test_tuple_inputs_accepted(self):
        self.assertEqual(
            weighted_sample_partition_indices(
                tuple(self.ITEMS), tuple(self.WEIGHTS),
                tuple(self.GROUP_SIZES), self.SEED),
            self._full(),
        )

    def test_fraction_decimal_exact_path(self):
        weights = [Fraction(1, 7), Decimal("0.2"), 0, 1, 10 ** 80, 0]
        groups = weighted_sample_partition_indices(
            self.ITEMS, weights, [1, 2, 1], seed=7)
        self.assertEqual(
            [p for g in groups for p in g],
            weighted_sample_indices(self.ITEMS, weights, 4, 7),
        )
        self.assertEqual(
            weighted_sample_partition(self.ITEMS, weights, [1, 2, 1], 7),
            [[self.ITEMS[i] for i in g] for g in groups],
        )

    def test_inputs_not_mutated(self):
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        group_sizes = list(self.GROUP_SIZES)
        weighted_sample_partition_indices(items, weights, group_sizes, self.SEED)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(group_sizes, self.GROUP_SIZES)

    def test_validation_type_errors(self):
        te = lambda fn: self.assertRaises(TypeError, fn)
        items, weights, groups = self.ITEMS, self.WEIGHTS, self.GROUP_SIZES
        te(lambda: weighted_sample_partition_indices("abcdef", weights, groups, 0))
        te(lambda: weighted_sample_partition_indices(items, iter(weights), groups, 0))
        te(lambda: weighted_sample_partition_indices(items, weights, "abc", 0))
        te(lambda: weighted_sample_partition_indices(items, weights, iter(groups), 0))
        te(lambda: weighted_sample_partition_indices(items, weights, [1, True], 0))
        te(lambda: weighted_sample_partition_indices(items, weights, [1, 1.0], 0))
        te(lambda: weighted_sample_partition_indices(
            items, [1, True, 0, 2, 5, 0], groups, 0))
        te(lambda: weighted_sample_partition_indices(
            items, [1, "x", 0, 2, 5, 0], groups, 0))
        te(lambda: weighted_sample_partition_indices(
            items, weights, groups, object()))

    def test_validation_value_errors(self):
        ve = lambda fn: self.assertRaises(ValueError, fn)
        items, weights, groups = self.ITEMS, self.WEIGHTS, self.GROUP_SIZES
        # 长度不一致(ValueError, tuple 是合法序列)。
        ve(lambda: weighted_sample_partition_indices(items, (1, 2), groups, 0))
        ve(lambda: weighted_sample_partition_indices(items, [1, 2, 0], groups, 0))
        # 负组大小。
        ve(lambda: weighted_sample_partition_indices(items, weights, [-1], 0))
        ve(lambda: weighted_sample_partition_indices(items, weights, [1, -1], 0))
        # 总组大小超过可用正权重位置数(正权重位置只有 4 个)。
        ve(lambda: weighted_sample_partition_indices(items, weights, [5], 0))
        ve(lambda: weighted_sample_partition_indices(items, weights, [3, 2], 0))
        # 全零权重下任何正组大小都失败。
        ve(lambda: weighted_sample_partition_indices(
            items, [0] * len(items), [1], 0))
        # 负权重、NaN、无穷。
        ve(lambda: weighted_sample_partition_indices(
            items, [1, -3, 0, 2, 5, 0], groups, 0))
        ve(lambda: weighted_sample_partition_indices(
            items, [1, float("nan"), 0, 2, 5, 0], groups, 0))
        ve(lambda: weighted_sample_partition_indices(
            items, [1, float("inf"), 0, 2, 5, 0], groups, 0))
        ve(lambda: weighted_sample_partition_indices(
            items, [Decimal("NaN"), 3, 0, 2, 5, 0], groups, 0))

    # ------------------------------------------------------------------
    # 断点创建
    # ------------------------------------------------------------------
    def test_checkpoint_state_is_json_native(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=2)
        self.assertEqual(state["version"], 1)
        self.assertEqual(state["kind"], "partition")
        self.assertEqual(state["start"], 2)
        self.assertEqual(state["n"], len(self.ITEMS))
        self.assertEqual(state["groups_count"], len(self.GROUP_SIZES))
        self.assertEqual(state["groups_total"], sum(self.GROUP_SIZES))
        # 整条无放回位置序列就是一次性序列, 零权重位置永不出现。
        self.assertEqual(state["sequence"], self._flat_reference())
        self.assertTrue(json.loads(json.dumps(state)) == state)

    def test_checkpoint_start_marks_group_boundaries_only(self):
        # 不同 start 只改边界, 不重抽: sequence 与随机结果相同。
        states = [
            weighted_sample_partition_checkpoint(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED,
                start=start)
            for start in range(len(self.GROUP_SIZES) + 1)
        ]
        for state in states:
            self.assertEqual(state["sequence"], self._flat_reference())

    def test_checkpoint_start_validation(self):
        te = lambda fn: self.assertRaises(TypeError, fn)
        ve = lambda fn: self.assertRaises(ValueError, fn)
        te(lambda: weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=True))
        te(lambda: weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=1.0))
        ve(lambda: weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=-1))
        ve(lambda: weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED,
            start=len(self.GROUP_SIZES) + 1))

    def test_checkpoint_at_end_of_plan(self):
        end = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED,
            start=len(self.GROUP_SIZES))
        self.assertEqual(end["start"], len(self.GROUP_SIZES))
        groups, same = weighted_sample_partition_resume_indices(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, end, 0)
        self.assertEqual(groups, [])
        self.assertEqual(same, end)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, end, 1)

    def test_checkpoint_zero_total_plan(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, [0] * len(self.ITEMS), [0, 0], seed=1)
        self.assertEqual(state["sequence"], [])
        self.assertEqual(state["groups_total"], 0)
        groups, next_state = weighted_sample_partition_resume_indices(
            self.ITEMS, [0] * len(self.ITEMS), [0, 0], state, 2)
        self.assertEqual(groups, [[], []])
        self.assertEqual(next_state["start"], 2)
        self.assertEqual(next_state["sequence"], [])

    def test_checkpoint_does_not_mutate_inputs(self):
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        group_sizes = list(self.GROUP_SIZES)
        weighted_sample_partition_checkpoint(
            items, weights, group_sizes, self.SEED, start=3)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(group_sizes, self.GROUP_SIZES)

    # ------------------------------------------------------------------
    # 恢复: 与一次性分组区间逐项一致
    # ------------------------------------------------------------------
    def test_resume_window_equals_one_shot_slice(self):
        full = self._full()
        for start in range(len(self.GROUP_SIZES) + 1):
            state = weighted_sample_partition_checkpoint(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED,
                start=start)
            for draws in range(0, len(self.GROUP_SIZES) - start + 1):
                with self.subTest(start=start, draws=draws):
                    groups, next_state = (
                        weighted_sample_partition_resume_indices(
                            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES,
                            state, draws)
                    )
                    self.assertEqual(groups, full[start:start + draws])
                    self.assertEqual(next_state["start"], start + draws)

    def test_chained_resumes_equal_one_shot_run(self):
        full = self._full()
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED)
        chunks = []
        for draws in (1, 2, 0, 1, 0):
            groups, state = weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, state, draws)
            chunks.extend(groups)
        self.assertEqual(chunks, full)
        self.assertEqual(state["start"], len(self.GROUP_SIZES))

    def test_draws_zero_returns_empty_and_unchanged_state_copy(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=2)
        groups, next_state = weighted_sample_partition_resume_indices(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, state, 0)
        self.assertEqual(groups, [])
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)

    def test_resume_window_out_of_range_raises_value_error(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=3)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, state, 2)

    def test_value_resume_maps_positions_and_shares_next_state(self):
        items = ["x", "y", "x", "z", "y", "q"]
        state = weighted_sample_partition_checkpoint(
            items, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=1)
        value_groups, value_next = weighted_sample_partition_resume(
            items, self.WEIGHTS, self.GROUP_SIZES, state, 3)
        index_groups, index_next = (
            weighted_sample_partition_resume_indices(
                items, self.WEIGHTS, self.GROUP_SIZES, state, 3)
        )
        self.assertEqual(
            value_groups,
            [[items[i] for i in group] for group in index_groups],
        )
        self.assertEqual(value_next, index_next)
        full = weighted_sample_partition(
            items, self.WEIGHTS, self.GROUP_SIZES, self.SEED)
        self.assertEqual(value_groups, full[1:])

    def test_state_roundtrips_serialize_metrics(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=1)
        restored = deserialize_metrics(serialize_metrics(state))
        full = self._full()
        groups, next_state = weighted_sample_partition_resume_indices(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, restored, 2)
        self.assertEqual(groups, full[1:3])
        # 下一状态再做一次文本往返后仍可续接。
        again, _ = weighted_sample_partition_resume_indices(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES,
            deserialize_metrics(serialize_metrics(next_state)), 1)
        self.assertEqual(again, full[3:])

    def test_rng_words_keep_exact_decimal_integers(self):
        big_weights = [10 ** 5000, 1, 2, 3, 0, 0]
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, big_weights, [2, 1], seed=8, start=1)
        restored = deserialize_metrics(serialize_metrics(state))
        self.assertTrue(all(isinstance(x, int) for x in restored["sequence"]))
        groups, _ = weighted_sample_partition_resume_indices(
            self.ITEMS, big_weights, [2, 1], restored, 1)
        self.assertEqual(
            groups,
            weighted_sample_partition_indices(
                self.ITEMS, big_weights, [2, 1], 8)[1:],
        )

    def test_seed_types_resume_consistently(self):
        for seed in (0, 1.5, -0.0, "s", b"b", bytearray([1]), True,
                     float("nan")):
            state = weighted_sample_partition_checkpoint(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, seed)
            groups, _ = weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES,
                deserialize_metrics(serialize_metrics(state)),
                len(self.GROUP_SIZES))
            self.assertEqual(
                groups,
                weighted_sample_partition_indices(
                    self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, seed),
            )
        # None 种子来自系统熵: 同一份快照无论恢复多少次都给出同一序列。
        none_state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, None)
        payload = json.loads(json.dumps(none_state))
        a, _ = weighted_sample_partition_resume_indices(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, payload, 4)
        b, _ = weighted_sample_partition_resume_indices(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES,
            json.loads(json.dumps(none_state)), 4)
        self.assertEqual(a, b)

    # ------------------------------------------------------------------
    # 恢复: 状态类型 / 结构 / 摘要 / 输入绑定
    # ------------------------------------------------------------------
    def test_non_mapping_state_raises_type_error(self):
        for bad in (None, [], "{}", 1, True, (), {1, 2}):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_partition_resume_indices(
                        self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, bad, 1)

    def test_draws_type_and_value_rules(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED)
        for bad in (True, False, 1.0, "1", None, [1], 1 + 0j):
            with self.subTest(bad=bad):
                with self.assertRaises(TypeError):
                    weighted_sample_partition_resume_indices(
                        self.ITEMS, self.WEIGHTS, self.GROUP_SIZES,
                        state, bad)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, state, -1)

    def test_invalid_state_structure_raises_value_error(self):
        import copy as _copy
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=1)

        def ve(mutator):
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_partition_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, bad, 1)

        ve(lambda s: s.pop("version"))
        ve(lambda s: s.pop("sequence"))
        ve(lambda s: s.update(extra=1))
        ve(lambda s: s.update(start=-1))
        ve(lambda s: s.update(start=True))
        ve(lambda s: s.update(n=-1))
        ve(lambda s: s.update(groups_count=-1))
        ve(lambda s: s.update(groups_total=-1))
        ve(lambda s: s.update(kind="schedule"))
        ve(lambda s: s.update(groups_digest=1))
        ve(lambda s: s.update(seed=["z", 1]))
        ve(lambda s: s.update(sequence="not-a-list"))
        ve(lambda s: s.update(digest=1))

    def test_unsupported_version_raises_value_error(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED)
        for bad_version in (0, 2, 99, True, "1", 1.0):
            bad = dict(state)
            bad["version"] = bad_version
            with self.subTest(bad_version=bad_version):
                with self.assertRaises(ValueError):
                    weighted_sample_partition_resume_indices(
                        self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, bad, 1)

    def test_state_mismatch_with_inputs_raises_value_error(self):
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=1)

        def ve(label, i2, w2, g2):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    weighted_sample_partition_resume_indices(
                        i2, w2, g2, state, 1)

        ve("group size differs", self.ITEMS, self.WEIGHTS, [2, 1, 0, 2])
        ve("group count differs", self.ITEMS, self.WEIGHTS, [2, 1, 1])
        ve("items differ", list("abcdeg"), self.WEIGHTS, self.GROUP_SIZES)
        ve("weights differ", self.ITEMS, [1, 3, 0, 2, 6, 0],
           self.GROUP_SIZES)
        # 同值不同类型(1 -> 1.0)可能改变抽样计划, 必须视为不匹配。
        ve("weight type swap", self.ITEMS, [1.0, 3, 0, 2, 5, 0],
           self.GROUP_SIZES)

    def test_tampered_fields_without_valid_digest_raise_value_error(self):
        import copy as _copy
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=1)

        def ve(mutator):
            bad = _copy.deepcopy(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                weighted_sample_partition_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, bad, 1)

        ve(lambda s: s.update(start=s["start"] + 1))
        ve(lambda s: s.update(groups_total=s["groups_total"] + 1))
        ve(lambda s: s["sequence"].pop())
        ve(lambda s: s.update(digest="0" * 64))
        ve(lambda s: s.update(seed=["i", 123]))

    def test_invalid_sequence_rejected_even_with_digest(self):
        # 即使重算了绑定摘要, 越界 / 重复 / 零权重位置也必须统一抛
        # ValueError —— 与其他断点对 RNG 快照的结构化范围校验同理。
        import copy as _copy
        from app import _partition_checkpoint_binding_digest
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED)

        def rehash(bad):
            bad["digest"] = _partition_checkpoint_binding_digest(
                bad["seed"], bad["start"], bad["n"], bad["groups_count"],
                bad["groups_total"], bad["groups_digest"],
                bad["items_digest"], bad["weights_digest"], bad["exact"],
                bad["sequence"])

        for mutator in (
            lambda s: s["sequence"].__setitem__(0, 99),   # 越界
            lambda s: s["sequence"].__setitem__(0, -1),   # 负位置
            lambda s: s["sequence"].__setitem__(0, True), # 布尔
            lambda s: s["sequence"].__setitem__(0, 2),    # 零权重位置
            lambda s: s["sequence"].__setitem__(
                1, s["sequence"][0]),                     # 重复位置
        ):
            bad = _copy.deepcopy(state)
            mutator(bad)
            rehash(bad)
            with self.assertRaises(ValueError):
                weighted_sample_partition_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, bad, 1)

    def test_other_kinds_of_checkpoint_state_rejected(self):
        # 其他会话的状态不能用于分组恢复, 反之亦然。
        partition_state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=1)
        fixed_state = weighted_sample_checkpoint(
            self.ITEMS, self.WEIGHTS, sum(self.GROUP_SIZES), self.SEED,
            start=1)
        excluding_state = weighted_sample_excluding_checkpoint(
            self.ITEMS, self.WEIGHTS, sum(self.GROUP_SIZES), (), self.SEED,
            start=1)
        schedule = [[1, 3, 0, 2, 5, 0]]
        schedule_state = weighted_sample_schedule_checkpoint(
            self.ITEMS, schedule, 2, self.SEED, start=0)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, fixed_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES,
                excluding_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES,
                schedule_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_resume_indices(
                self.ITEMS, self.WEIGHTS, sum(self.GROUP_SIZES),
                partition_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_excluding_resume_indices(
                self.ITEMS, self.WEIGHTS, sum(self.GROUP_SIZES), (),
                partition_state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_schedule_resume_indices(
                self.ITEMS, schedule, 2, partition_state, 1)

    def test_value_entry_validates_inputs_before_mapping(self):
        # 值入口先按分组入口校验 items/weights/group_sizes, 再要求 state
        # 是映射并校验 draws —— 损坏的状态不能掩盖非法输入。
        with self.assertRaises(TypeError):
            weighted_sample_partition_resume(
                "abcdef", self.WEIGHTS, self.GROUP_SIZES, "not-a-mapping", 1)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume(
                self.ITEMS, self.WEIGHTS, [-1], "not-a-mapping", 1)
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_partition_resume(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, [], 1)
        with self.assertRaises(TypeError):
            weighted_sample_partition_resume(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, state, True)

    def test_no_groups_partially_returned_on_failure(self):
        # 恢复窗口越界时即使能抽出前面的组, 也不返回部分结果。
        state = weighted_sample_partition_checkpoint(
            self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, self.SEED, start=3)
        with self.assertRaises(ValueError):
            weighted_sample_partition_resume_indices(
                self.ITEMS, self.WEIGHTS, self.GROUP_SIZES, state, 2)

    def test_resume_does_not_mutate_inputs_or_state(self):
        import copy as _copy
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        group_sizes = list(self.GROUP_SIZES)
        state = weighted_sample_partition_checkpoint(
            items, weights, group_sizes, self.SEED, start=1)
        state_snapshot = _copy.deepcopy(state)
        weighted_sample_partition_resume_indices(
            items, weights, group_sizes, state, 2)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(group_sizes, self.GROUP_SIZES)
        self.assertEqual(state, state_snapshot)


class WeightedSamplePlanTest(unittest.TestCase):
    """按轮权重与样本数联合计划的批量入口:
    weighted_sample_plan_indices / weighted_sample_plan /
    weighted_sample_plan_counts。"""

    ITEMS = list("aabbcc")
    WEIGHTS_SCHEDULE = [
        [1, 2, 3, 0, 1, 2],
        [2, 2, 2, 2, 2, 2],
        [Fraction(1, 2), 1, 0, 3, 2, 1],
        [1, 1, 1, 1, 1, 1],
        [Decimal("0.5"), 2, 1, 0, 1, 3],
    ]
    K_SCHEDULE = [2, 0, 3, 1, 2]
    SEED = 7

    def _full(self):
        return weighted_sample_plan_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            len(self.K_SCHEDULE), self.SEED)

    def test_outer_shape_and_round_lengths(self):
        rounds = self._full()
        self.assertEqual(len(rounds), len(self.K_SCHEDULE))
        for j, round_indices in enumerate(rounds):
            self.assertEqual(len(round_indices), self.K_SCHEDULE[j])
            self.assertEqual(len(set(round_indices)), len(round_indices))
            for position in round_indices:
                self.assertIn(position, range(len(self.ITEMS)))

    def test_zero_weight_never_chosen_and_zero_k_round_empty(self):
        rounds = self._full()
        # 第 0 行位置 3 权重为零, 永不入选; 第 1 轮样本数为零, 为空列表。
        for position in rounds[0]:
            self.assertNotEqual(position, 3)
        self.assertEqual(rounds[1], [])

    def test_values_entry_corresponds_round_by_round(self):
        index_rounds = self._full()
        value_rounds = weighted_sample_plan(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            len(self.K_SCHEDULE), self.SEED)
        self.assertEqual(
            value_rounds,
            [[self.ITEMS[i] for i in round_indices]
             for round_indices in index_rounds],
        )

    def test_duplicate_values_distinct_positions(self):
        rounds = weighted_sample_plan_indices(
            ["x", "x", "x"], [[1, 1, 1]] * 3, [3, 3, 3], 3, seed=5)
        for round_indices in rounds:
            self.assertEqual(sorted(round_indices), [0, 1, 2])

    def test_start_equals_slice_of_full_run(self):
        full = self._full()
        for start in range(len(self.K_SCHEDULE) + 1):
            for draws in range(0, len(self.K_SCHEDULE) - start + 1):
                with self.subTest(start=start, draws=draws):
                    self.assertEqual(
                        weighted_sample_plan_indices(
                            self.ITEMS, self.WEIGHTS_SCHEDULE,
                            self.K_SCHEDULE, draws, self.SEED, start),
                        full[start:start + draws],
                    )

    def test_same_seed_same_result(self):
        self.assertEqual(self._full(), self._full())

    def test_uniform_plan_matches_fixed_entries(self):
        # 权重各行相同且计划各项都等于 k 时, 与固定权重批量入口逐轮一致。
        uniform_rows = [[1, 2, 3, 0, 1, 2]] * 4
        uniform_ks = [2] * 4
        self.assertEqual(
            weighted_sample_plan_indices(
                self.ITEMS, uniform_rows, uniform_ks, 4, seed=3),
            weighted_sample_many_indices(
                self.ITEMS, uniform_rows[0], 2, 4, seed=3),
        )

    def test_constant_k_matches_weights_schedule_entry(self):
        uniform_ks = [2] * len(self.K_SCHEDULE)
        self.assertEqual(
            weighted_sample_plan_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, uniform_ks,
                len(uniform_ks), self.SEED),
            weighted_sample_schedule_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, 2,
                len(uniform_ks), self.SEED),
        )

    def test_constant_rows_matches_k_schedule_entry(self):
        uniform_rows = [[1, 2, 3, 0, 1, 2]] * len(self.K_SCHEDULE)
        self.assertEqual(
            weighted_sample_plan_indices(
                self.ITEMS, uniform_rows, self.K_SCHEDULE,
                len(self.K_SCHEDULE), self.SEED),
            weighted_sample_k_schedule_indices(
                self.ITEMS, uniform_rows[0], self.K_SCHEDULE,
                len(self.K_SCHEDULE), self.SEED),
        )

    def test_counts_match_flattened_index_rounds(self):
        full = self._full()
        for start in range(len(self.K_SCHEDULE) + 1):
            for draws in range(0, len(self.K_SCHEDULE) - start + 1):
                with self.subTest(start=start, draws=draws):
                    counts = weighted_sample_plan_counts(
                        self.ITEMS, self.WEIGHTS_SCHEDULE,
                        self.K_SCHEDULE, draws, self.SEED, start)
                    flat = [0] * len(self.ITEMS)
                    for round_indices in full[start:start + draws]:
                        for position in round_indices:
                            flat[position] += 1
                    self.assertEqual(counts, flat)

    def test_counts_are_exact_integers_and_serialize_roundtrip(self):
        counts = weighted_sample_plan_counts(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            len(self.K_SCHEDULE), self.SEED)
        self.assertTrue(all(isinstance(c, int) for c in counts))
        self.assertEqual(
            deserialize_metrics(serialize_metrics(counts)), counts)

    def test_draws_zero_returns_empty_after_full_validation(self):
        self.assertEqual(
            weighted_sample_plan_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                0, self.SEED), [])
        self.assertEqual(
            weighted_sample_plan(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                0, self.SEED), [])
        self.assertEqual(
            weighted_sample_plan_counts(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                0, self.SEED),
            [0] * len(self.ITEMS))
        # draws=0 仍完成全部校验。
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                0, self.SEED, len(self.K_SCHEDULE) + 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE,
                [True] * len(self.K_SCHEDULE), 0, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_plan_counts(
                self.ITEMS, [[0] * len(self.ITEMS)] * len(self.K_SCHEDULE),
                [1] * len(self.K_SCHEDULE), 0, self.SEED)

    def test_structure_errors_raise_type_error(self):
        ws = self.WEIGHTS_SCHEDULE
        ks = self.K_SCHEDULE
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices("aabbcc", ws, ks, 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, "not-seq", ks, 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, [1, 2], ks[:2], 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, ws, "ks", 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, ws, [1.5] * 5, 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, ws, [True] * 5, 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, 1.5)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, True)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, 1, 0, 1.5)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, 1, object())
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(
                self.ITEMS, [[True] * 6] * 5, ks, 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_indices(
                self.ITEMS, [["x"] * 6] * 5, ks, 1)

    def test_value_errors(self):
        ws = self.WEIGHTS_SCHEDULE
        ks = self.K_SCHEDULE
        n = len(self.ITEMS)
        # 负 draws / 负 start / 窗口越界。
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, -1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, 1, 0, -1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, len(ks) + 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks, 2, 0, len(ks) - 1)
        # 两个计划不等长。
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws, ks + [1], 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws + [ws[0]], ks, 1)
        # 行长度不等于 items。
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, [[1, 2]] * 5, ks, 1)
        # 计划成员为负或超过位置数。
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws, [-1] * 5, 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, ws, [n + 1] * 5, 1)
        # 负权重 / NaN / 无穷。
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(self.ITEMS, [[-1] * n] * 5, ks, 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(
                self.ITEMS, [[float("nan")] * n] * 5, ks, 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(
                self.ITEMS, [[float("inf")] * n] * 5, ks, 1)
        # 对应轮正权重不足。
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(
                self.ITEMS, [[0] * n] * 5, [1, 0, 0, 0, 0], 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_indices(
                self.ITEMS, [[1, 0, 0, 0, 0, 0]] * 5, [2, 0, 0, 0, 0], 1)

    def test_zero_k_rounds_do_not_consume_rng(self):
        import random as _random
        fresh = app._rng_state_to_jsonable(_random.Random(11).getstate())
        # 全零样本数计划: 跳轮不消耗随机流, 结果与从 0 生成的切片一致。
        zero_ks = [0] * 5
        full = weighted_sample_plan_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, zero_ks, 5, seed=11)
        self.assertEqual(full, [[]] * 5)
        shifted = weighted_sample_plan_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, zero_ks, 2, seed=11, start=3)
        self.assertEqual(shifted, [[]] * 2)
        # 对照: 全零计划下断点的 RNG 快照与全新随机流一致(见断点测试)。
        self.assertIsNotNone(fresh)

    def test_inputs_not_mutated(self):
        items = list(self.ITEMS)
        ws = [list(row) for row in self.WEIGHTS_SCHEDULE]
        ks = list(self.K_SCHEDULE)
        weighted_sample_plan_indices(items, ws, ks, len(ks), self.SEED)
        weighted_sample_plan(items, ws, ks, len(ks), self.SEED)
        weighted_sample_plan_counts(items, ws, ks, len(ks), self.SEED)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(ws, [list(row) for row in self.WEIGHTS_SCHEDULE])
        self.assertEqual(ks, self.K_SCHEDULE)

    def test_fraction_decimal_and_huge_integer_weights(self):
        items = list("abcd")
        ws = [
            [Fraction(1, 10**100), 1, 0, 2],
            [Decimal("1E-100"), 1, 1, 0],
            [10**400, 1, 1, 1],
        ]
        ks = [1, 2, 3]
        rounds = weighted_sample_plan_indices(items, ws, ks, 3, seed=9)
        self.assertEqual(rounds, weighted_sample_plan_indices(
            items, ws, ks, 3, seed=9))
        for j, round_indices in enumerate(rounds):
            self.assertEqual(len(round_indices), ks[j])
        # 微小正权重位置仍保留候选资格: 精确路径下零权重位置绝不出现。
        for position in rounds[0]:
            self.assertNotEqual(position, 2)


class WeightedSamplePlanCheckpointTest(unittest.TestCase):
    """按轮权重与样本数联合计划的可暂停 / 恢复会话:
    weighted_sample_plan_checkpoint /
    weighted_sample_plan_resume_indices /
    weighted_sample_plan_resume。"""

    ITEMS = list("aabbcc")
    WEIGHTS_SCHEDULE = [
        [1, 2, 3, 0, 1, 2],
        [2, 2, 2, 2, 2, 2],
        [Fraction(1, 2), 1, 0, 3, 2, 1],
        [1, 1, 1, 1, 1, 1],
        [Decimal("0.5"), 2, 1, 0, 1, 3],
    ]
    K_SCHEDULE = [2, 0, 3, 1, 2]
    SEED = 42

    def _full(self):
        return weighted_sample_plan_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            len(self.K_SCHEDULE), self.SEED)

    def test_checkpoint_state_is_json_native(self):
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            self.SEED, start=2)
        self.assertEqual(state["version"], 1)
        self.assertEqual(state["kind"], "plan")
        self.assertEqual(state["position"], 2)
        self.assertEqual(state["n"], len(self.ITEMS))
        self.assertEqual(
            state["schedule_length"], len(self.K_SCHEDULE))
        self.assertTrue(json.loads(json.dumps(state)) == state)

    def test_resume_window_equals_one_shot_slice(self):
        full = self._full()
        for start in range(len(self.K_SCHEDULE) + 1):
            state = weighted_sample_plan_checkpoint(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                self.SEED, start=start)
            for draws in range(0, len(self.K_SCHEDULE) - start + 1):
                with self.subTest(start=start, draws=draws):
                    rounds, next_state = weighted_sample_plan_resume_indices(
                        self.ITEMS, self.WEIGHTS_SCHEDULE,
                        self.K_SCHEDULE, state, draws)
                    self.assertEqual(rounds, full[start:start + draws])
                    self.assertEqual(next_state["position"], start + draws)

    def test_chained_resumes_equal_one_shot_run(self):
        full = self._full()
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, self.SEED)
        chunks = []
        for draws in (1, 2, 0, 1, 1, 0):
            rounds, state = weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                state, draws)
            chunks.extend(rounds)
        self.assertEqual(chunks, full)
        self.assertEqual(state["position"], len(self.K_SCHEDULE))

    def test_value_resume_matches_index_resume(self):
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            self.SEED, start=1)
        index_rounds, index_next = weighted_sample_plan_resume_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, state, 3)
        value_rounds, value_next = weighted_sample_plan_resume(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, state, 3)
        self.assertEqual(
            value_rounds,
            [[self.ITEMS[i] for i in round_indices]
             for round_indices in index_rounds])
        # 两个入口的下一状态逐字段一致, 可互换续接。
        self.assertEqual(index_next, value_next)
        tail_a, _ = weighted_sample_plan_resume_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            value_next, 1)
        tail_b, _ = weighted_sample_plan_resume(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            index_next, 1)
        self.assertEqual(
            tail_b, [[self.ITEMS[i] for i in r] for r in tail_a])

    def test_state_roundtrip_via_serialize_metrics(self):
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            self.SEED, start=2)
        restored = deserialize_metrics(serialize_metrics(state))
        expected, _ = weighted_sample_plan_resume_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, state, 2)
        actual, _ = weighted_sample_plan_resume_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, restored, 2)
        self.assertEqual(actual, expected)
        # json 文本路径同样可恢复。
        via_json = json.loads(json.dumps(state))
        actual_json, _ = weighted_sample_plan_resume_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, via_json, 2)
        self.assertEqual(actual_json, expected)

    def test_draws_zero_returns_empty_and_unchanged_state_copy(self):
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
            self.SEED, start=3)
        rounds, next_state = weighted_sample_plan_resume_indices(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, state, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)

    def test_zero_k_rounds_do_not_consume_rng(self):
        import random as _random
        fresh = app._rng_state_to_jsonable(_random.Random(7).getstate())
        zero_ks = [0, 0, 0]
        ws = self.WEIGHTS_SCHEDULE[:3]
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, ws, zero_ks, seed=7, start=2)
        self.assertEqual(state["rng"], fresh)
        rounds, next_state = weighted_sample_plan_resume_indices(
            self.ITEMS, ws, zero_ks, state, 1)
        self.assertEqual(rounds, [[]])
        self.assertEqual(next_state["rng"], fresh)
        self.assertEqual(next_state["position"], 3)

    def test_checkpoint_validates_like_batch_entry(self):
        ws = self.WEIGHTS_SCHEDULE
        ks = self.K_SCHEDULE
        n = len(self.ITEMS)
        with self.assertRaises(TypeError):
            weighted_sample_plan_checkpoint(self.ITEMS, ws, [True] * 5)
        with self.assertRaises(TypeError):
            weighted_sample_plan_checkpoint(self.ITEMS, "bad", ks)
        with self.assertRaises(ValueError):
            weighted_sample_plan_checkpoint(self.ITEMS, ws, ks + [1])
        with self.assertRaises(ValueError):
            weighted_sample_plan_checkpoint(
                self.ITEMS, [[0] * n] * 5, [1, 0, 0, 0, 0])
        with self.assertRaises(ValueError):
            weighted_sample_plan_checkpoint(
                self.ITEMS, ws, ks, self.SEED, len(ks) + 1)
        # start == 计划长度允许, 表示整批已完成。
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, ws, ks, self.SEED, len(ks))
        self.assertEqual(state["position"], len(ks))

    def test_resume_rejects_non_mapping_state(self):
        with self.assertRaises(TypeError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                "not-a-mapping", 1)
        with self.assertRaises(TypeError):
            weighted_sample_plan_resume(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, 42, 1)

    def test_resume_rejects_bad_draws(self):
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                state, 1.5)
        with self.assertRaises(TypeError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                state, True)
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                state, -1)

    def test_resume_rejects_structurally_invalid_state(self):
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, self.SEED)
        # 字段缺失。
        for key in state:
            broken = dict(state)
            del broken[key]
            with self.subTest(missing=key):
                with self.assertRaises(ValueError):
                    weighted_sample_plan_resume_indices(
                        self.ITEMS, self.WEIGHTS_SCHEDULE,
                        self.K_SCHEDULE, broken, 1)
        # 额外字段。
        broken = dict(state)
        broken["extra"] = 1
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                broken, 1)
        # 版本 / kind 不支持。
        for key, value in (("version", 99), ("kind", "k_schedule"),
                           ("kind", "schedule")):
            broken = dict(state)
            broken[key] = value
            with self.subTest(**{key: value}):
                with self.assertRaises(ValueError):
                    weighted_sample_plan_resume_indices(
                        self.ITEMS, self.WEIGHTS_SCHEDULE,
                        self.K_SCHEDULE, broken, 1)
        # 篡改字段但摘要未重算。
        broken = dict(state)
        broken["position"] = state["position"] + 1
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                broken, 1)

    def test_resume_rejects_mismatched_inputs(self):
        state = weighted_sample_plan_checkpoint(
            self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                list("abcdef"), self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, [[9] * len(self.ITEMS)] * 5, self.K_SCHEDULE,
                state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, [2, 0, 3, 1, 1],
                state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE,
                self.K_SCHEDULE + [1], state, 1)
        # 恢复窗口超出计划范围。
        with self.assertRaises(ValueError):
            weighted_sample_plan_resume_indices(
                self.ITEMS, self.WEIGHTS_SCHEDULE, self.K_SCHEDULE,
                state, len(self.K_SCHEDULE) + 1)

    def test_resume_does_not_mutate_inputs_or_state(self):
        import copy as _copy
        items = list(self.ITEMS)
        ws = [list(row) for row in self.WEIGHTS_SCHEDULE]
        ks = list(self.K_SCHEDULE)
        state = weighted_sample_plan_checkpoint(
            items, ws, ks, self.SEED, start=1)
        state_snapshot = _copy.deepcopy(state)
        weighted_sample_plan_resume_indices(items, ws, ks, state, 2)
        weighted_sample_plan_resume(items, ws, ks, state, 2)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(ws, [list(row) for row in self.WEIGHTS_SCHEDULE])
        self.assertEqual(ks, self.K_SCHEDULE)
        self.assertEqual(state, state_snapshot)


class WeightedSampleStratifiedTest(unittest.TestCase):
    ITEMS = ["a", "b", "c", "d", "e", "f", "g", "h"]
    WEIGHTS = [5, 1, 3, 2, 4, 1, 2, 6]
    STRATA = [0, 0, 1, 1, 2, 2, 2, 2]
    QUOTAS = [1, 1, 2]
    SEED = 20240521

    def test_deterministic_same_seed(self):
        first = weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        second = weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                seed=self.SEED))

    def test_strata_processed_in_ascending_number_order(self):
        indices = weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        # 总长度等于配额总和, 各层按编号升序拼接。
        self.assertEqual(len(indices), sum(self.QUOTAS))
        cursor = 0
        for number, quota in enumerate(self.QUOTAS):
            segment = indices[cursor:cursor + quota]
            cursor += quota
            self.assertEqual(len(segment), quota)
            for position in segment:
                self.assertEqual(self.STRATA[position], number)
        # 全部位置互不重复(每个位置只属于一个分层, 层内无放回)。
        self.assertEqual(len(set(indices)), len(indices))

    def test_single_zero_stratum_matches_weighted_sample_indices(self):
        for weights, k, seed in (
            ([3, 1, 4, 1, 5], 2, 7),
            ([1.5, 0.5, 2.0], 2, 99),
            ([10 ** 60, 1, 1], 2, 3),
            ([Fraction(1, 3), Fraction(2, 3), 1], 2, 11),
            ([0, 0, 4, 0, 2], 2, 5),
            ([1, 2, 3], 0, 1),
        ):
            items = list(range(len(weights)))
            strata = [0] * len(weights)
            self.assertEqual(
                weighted_sample_stratified_indices(
                    items, weights, strata, [k], seed),
                weighted_sample_indices(items, weights, k, seed))
            self.assertEqual(
                weighted_sample_stratified(items, weights, strata, [k], seed),
                weighted_sample(items, weights, k, seed))

    def test_zero_quota_stratum_does_not_consume_stream(self):
        # 中间的零配额分层不消耗随机流: 去掉该层并把后续编号前移后,
        # 各层抽样结果(按原始位置)逐项一致。
        items = ["a", "b", "c", "d", "e", "f"]
        weights = [3, 1, 2, 2, 4, 1]
        strata = [0, 0, 1, 1, 2, 2]
        with_gap = weighted_sample_stratified_indices(
            items, weights, strata, [1, 0, 1], self.SEED)
        # 等价调用: 仅保留配额非零的层, 编号相应前移。
        compact_items = [items[0], items[1], items[4], items[5]]
        compact_weights = [weights[0], weights[1], weights[4], weights[5]]
        compact_strata = [0, 0, 1, 1]
        compact = weighted_sample_stratified_indices(
            compact_items, compact_weights, compact_strata, [1, 1], self.SEED)
        remap = [0, 1, 4, 5]
        self.assertEqual(with_gap, [remap[i] for i in compact])

    def test_values_entry_corresponds_to_indices_entry(self):
        indices = weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        values = weighted_sample_stratified(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        self.assertEqual(values, [self.ITEMS[i] for i in indices])

    def test_duplicate_values_distinct_positions(self):
        items = ["x", "x", "x", "x"]
        weights = [1, 1, 1, 1]
        strata = [0, 0, 1, 1]
        indices = weighted_sample_stratified_indices(
            items, weights, strata, [1, 1], 5)
        self.assertEqual(len(set(indices)), 2)
        values = weighted_sample_stratified(items, weights, strata, [1, 1], 5)
        self.assertEqual(values, [items[i] for i in indices])

    def test_zero_weight_never_chosen(self):
        items = ["a", "b", "c", "d"]
        weights = [0, 3, 0, 2]
        strata = [0, 0, 1, 1]
        for seed in range(20):
            indices = weighted_sample_stratified_indices(
                items, weights, strata, [1, 1], seed)
            self.assertEqual(indices, [1, 3])

    def test_all_zero_quotas_returns_empty_after_validation(self):
        self.assertEqual(
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [0, 0, 0], self.SEED),
            [])
        self.assertEqual(
            weighted_sample_stratified(
                self.ITEMS, self.WEIGHTS, self.STRATA, [0, 0, 0], self.SEED),
            [])
        self.assertEqual(
            weighted_sample_stratified_counts(
                self.ITEMS, self.WEIGHTS, self.STRATA, [0, 0, 0], self.SEED),
            [0] * len(self.ITEMS))
        # 全部配额为零仍完成权重取值校验。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, [-1] + self.WEIGHTS[1:], self.STRATA,
                [0, 0, 0], self.SEED)

    def test_empty_items_requires_empty_strata_and_quotas(self):
        self.assertEqual(weighted_sample_stratified_indices([], [], [], []), [])
        self.assertEqual(weighted_sample_stratified([], [], [], []), [])
        self.assertEqual(
            weighted_sample_stratified_counts([], [], [], []), [])
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices([], [], [0], [])
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices([], [], [], [0])

    def test_counts_match_indices_entry(self):
        for seed in (0, 1, self.SEED, 987654):
            indices = weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, seed)
            counts = weighted_sample_stratified_counts(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, seed)
            self.assertEqual(len(counts), len(self.ITEMS))
            for position, count in enumerate(counts):
                self.assertIn(count, (0, 1))
                self.assertEqual(count, indices.count(position))
            self.assertEqual(sum(counts), sum(self.QUOTAS))

    def test_counts_serialize_roundtrip_exact(self):
        counts = weighted_sample_stratified_counts(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        text = serialize_metrics(counts)
        self.assertEqual(deserialize_metrics(text), counts)
        self.assertEqual(
            deserialize_metrics(serialize_metrics({"counts": counts})),
            {"counts": counts})

    def test_fraction_decimal_and_huge_integer_weights(self):
        items = ["a", "b", "c", "d"]
        weights = [Fraction(1, 10 ** 30), Decimal("1E-25"), 10 ** 80, 2]
        strata = [0, 0, 1, 1]
        first = weighted_sample_stratified_indices(
            items, weights, strata, [1, 1], 17)
        second = weighted_sample_stratified_indices(
            items, weights, strata, [1, 1], 17)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)
        # 超大整数权重在该层中必然被选中。
        self.assertIn(2, first)

    def test_validation_type_errors(self):
        good = (self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS)
        # items / weights / strata / quotas 结构错误。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                "abcdefgh", *good[1:], seed=self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, "12345678", self.STRATA, self.QUOTAS,
                seed=self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, "00012222", self.QUOTAS,
                seed=self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, "112", seed=self.SEED)
        # seed 类型错误。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                *good, seed=object())
        # strata / quotas 成员类型错误: 布尔与非整数。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS,
                [True] + self.STRATA[1:], self.QUOTAS, seed=self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS,
                [0.0] + self.STRATA[1:], self.QUOTAS, seed=self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, False, 2],
                seed=self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, "1", 2],
                seed=self.SEED)
        # 权重元素类型错误沿用既有规则。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, [True] + self.WEIGHTS[1:], self.STRATA,
                self.QUOTAS, seed=self.SEED)
        # 值入口与频次入口共用同一套校验。
        with self.assertRaises(TypeError):
            weighted_sample_stratified(
                self.ITEMS, self.WEIGHTS, self.STRATA, None, seed=self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_counts(
                self.ITEMS, self.WEIGHTS, None, self.QUOTAS, seed=self.SEED)

    def test_validation_value_errors(self):
        # weights / strata 长度与 items 不一致。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS[:-1], self.STRATA, self.QUOTAS,
                seed=self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA[:-1], self.QUOTAS,
                seed=self.SEED)
        # 负编号与编号越界(quotas 长度不等于最大编号加一)。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS,
                [-1] + self.STRATA[1:], self.QUOTAS, seed=self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS[:-1],
                seed=self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS + [0], seed=self.SEED)
        # 负配额。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, -1, 2],
                seed=self.SEED)
        # 配额超过该层正权重位置数(含该层权重全为零的情形)。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [3, 1, 2],
                seed=self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, [5, 1, 0, 0, 4, 1, 2, 6], self.STRATA,
                [1, 1, 2], seed=self.SEED)
        # 负权重、NaN、无穷权重沿用既有规则。
        for bad_weight in (-1, float("nan"), float("inf"), Decimal("NaN"),
                           Decimal("-Infinity")):
            with self.assertRaises(ValueError):
                weighted_sample_stratified_indices(
                    self.ITEMS, [bad_weight] + self.WEIGHTS[1:],
                    self.STRATA, self.QUOTAS, seed=self.SEED)

    def test_validation_order_fixed(self):
        # items 结构错误优先于 strata / quotas 的一切错误。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                123, self.WEIGHTS[:-1], None, None, seed=object())
        # strata 成员类型错误优先于 quotas 结构错误与长度错误。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, [None] * len(self.ITEMS),
                None, seed=self.SEED)
        # quotas 成员类型错误优先于长度与编号范围错误。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1.5], seed=self.SEED)
        # 长度/编号范围错误优先于权重取值错误。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, [float("nan")] * len(self.ITEMS),
                self.STRATA[:-1], self.QUOTAS, seed=self.SEED)
        # 权重取值错误优先于每层可行性检查。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, [-5] + self.WEIGHTS[1:], self.STRATA,
                [3, 1, 2], seed=self.SEED)

    def test_no_partial_output_on_error(self):
        # 最后一层配额不可行时, 前面各层也不产生任何结果。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, 1, 99],
                seed=self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_counts(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, 1, 99],
                seed=self.SEED)

    def test_inputs_not_mutated(self):
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        strata = list(self.STRATA)
        quotas = list(self.QUOTAS)
        weighted_sample_stratified_indices(
            items, weights, strata, quotas, self.SEED)
        weighted_sample_stratified(items, weights, strata, quotas, self.SEED)
        weighted_sample_stratified_counts(
            items, weights, strata, quotas, self.SEED)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(strata, self.STRATA)
        self.assertEqual(quotas, self.QUOTAS)

    def test_existing_entries_unchanged_by_stratified_addition(self):
        # 既有单轮入口的锁定序列不受新增入口影响。
        self.assertEqual(
            weighted_sample_indices(self.ITEMS, self.WEIGHTS, 3, self.SEED),
            weighted_sample_indices(self.ITEMS, self.WEIGHTS, 3, self.SEED))
        weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        self.assertEqual(
            weighted_sample(self.ITEMS, self.WEIGHTS, 3, self.SEED),
            weighted_sample(self.ITEMS, self.WEIGHTS, 3, self.SEED))


class WeightedSampleStratifiedCheckpointTest(unittest.TestCase):
    """分层配额采样的可暂停 / 恢复会话:
    weighted_sample_stratified_checkpoint /
    weighted_sample_stratified_resume_indices /
    weighted_sample_stratified_resume。"""

    ITEMS = ["a", "b", "c", "d", "e", "f", "g", "h"]
    WEIGHTS = [5, 1, 3, 2, 4, 1, 2, 6]
    STRATA = [0, 0, 1, 1, 2, 2, 2, 2]
    QUOTAS = [1, 0, 2]
    SEED = 20240521

    def _full(self, quotas=None, seed=None):
        return weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA,
            self.QUOTAS if quotas is None else quotas,
            self.SEED if seed is None else seed)

    @staticmethod
    def _strata_slice(full, quotas, begin, end):
        # 一次性结果按编号升序拼接, 分层区间 [begin, end) 对应连续切片。
        bounds = [0]
        for quota in quotas:
            bounds.append(bounds[-1] + quota)
        return full[bounds[begin]:bounds[end]]

    def test_checkpoint_state_is_json_native(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=2)
        # 版本 / kind / 位置 / 分层数 / 指纹 / 逐层抽样路径标记 / seed /
        # RNG / 摘要齐备。
        self.assertEqual(state["version"], 1)
        self.assertEqual(state["kind"], "stratified")
        self.assertEqual(state["position"], 2)
        self.assertEqual(state["n"], len(self.ITEMS))
        self.assertEqual(state["strata_count"], len(self.QUOTAS))
        self.assertEqual(state["exact"], [False, False, False])
        self.assertTrue(json.loads(json.dumps(state)) == state)

    def test_resume_window_equals_one_shot_slice(self):
        full = self._full()
        for start in range(len(self.QUOTAS) + 1):
            state = weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                self.SEED, start=start)
            for draws in range(0, len(self.QUOTAS) - start + 1):
                with self.subTest(start=start, draws=draws):
                    indices, next_state = (
                        weighted_sample_stratified_resume_indices(
                            self.ITEMS, self.WEIGHTS, self.STRATA,
                            self.QUOTAS, state, draws)
                    )
                    self.assertEqual(
                        indices,
                        self._strata_slice(
                            full, self.QUOTAS, start, start + draws))
                    self.assertEqual(next_state["position"], start + draws)

    def test_chained_resumes_equal_one_shot_run(self):
        full = self._full()
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED)
        chunks = []
        for draws in (1, 0, 2, 0):
            indices, state = weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                state, draws)
            chunks.extend(indices)
        self.assertEqual(chunks, full)
        # 链式结束时位置恰为计划末尾。
        self.assertEqual(state["position"], len(self.QUOTAS))

    def test_resume_values_match_indices(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        values, state_v = weighted_sample_stratified_resume(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, state, 2)
        indices, state_i = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, state, 2)
        self.assertEqual(values, [self.ITEMS[i] for i in indices])
        self.assertEqual(state_v, state_i)

    def test_resume_values_handle_duplicate_items_by_position(self):
        items = ["x", "x", "y", "y"]
        weights = [1, 1, 1, 1]
        strata = [0, 0, 1, 1]
        quotas = [1, 2]
        full = weighted_sample_stratified_indices(
            items, weights, strata, quotas, 9)
        state = weighted_sample_stratified_checkpoint(
            items, weights, strata, quotas, 9)
        values, _ = weighted_sample_stratified_resume(
            items, weights, strata, quotas, state, 2)
        self.assertEqual(values, [items[i] for i in full])

    def test_draws_zero_returns_empty_and_state_copy(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        indices, next_state = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, state, 0)
        self.assertEqual(indices, [])
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)
        values, next_state_v = weighted_sample_stratified_resume(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, state, 0)
        self.assertEqual(values, [])
        self.assertEqual(next_state_v, state)

    def test_zero_quota_strata_do_not_consume_rng(self):
        # 第 1 层配额为零: 跨过它的断点与恢复都不消耗随机流。
        before = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        after = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=2)
        self.assertEqual(before["rng"], after["rng"])
        indices, next_state = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, before, 1)
        self.assertEqual(indices, [])
        self.assertEqual(next_state["position"], 2)
        self.assertEqual(next_state["rng"], before["rng"])

    def test_memberless_stratum_only_advances_position(self):
        # 编号 1 没有成员(配额只能为零): 只推进位置, 不消耗随机流。
        strata = [0, 0, 2, 2, 2, 2, 2, 2]
        quotas = [1, 0, 2]
        full = weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, strata, quotas, self.SEED)
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, strata, quotas, self.SEED, start=1)
        indices, state = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, strata, quotas, state, 2)
        self.assertEqual(indices, full[1:])
        self.assertEqual(state["position"], 3)

    def test_end_of_plan_accepts_only_empty_window(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=len(self.QUOTAS))
        indices, next_state = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, state, 0)
        self.assertEqual(indices, [])
        self.assertEqual(next_state, state)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                state, 1)

    def test_resume_window_out_of_range(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                state, len(self.QUOTAS))

    def test_state_survives_serialize_metrics_round_trip(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        restored = deserialize_metrics(serialize_metrics(state))
        expected, next_expected = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, state, 2)
        indices, next_state = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
            restored, 2)
        self.assertEqual(indices, expected)
        self.assertEqual(next_state, next_expected)
        # 往返后的下一状态仍可继续恢复。
        again = deserialize_metrics(serialize_metrics(next_state))
        indices2, _ = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, again, 0)
        self.assertEqual(indices2, [])

    def test_state_survives_json_round_trip(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        restored = json.loads(json.dumps(state))
        indices, _ = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
            restored, 2)
        self.assertEqual(
            indices, self._strata_slice(self._full(), self.QUOTAS, 1, 3))

    def test_exact_weight_types_supported(self):
        weights = [Fraction(1, 3), Decimal("0.5"), 2, 0, 1, 1, 1, 2]
        quotas = [1, 0, 2]
        full = weighted_sample_stratified_indices(
            self.ITEMS, weights, self.STRATA, quotas, 7)
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, weights, self.STRATA, quotas, 7, start=1)
        # 第 0 层含 Fraction / Decimal 走精确路径; 第 1 层零配额; 第 2 层
        # 小整数权重保持浮点路径。
        self.assertEqual(state["exact"], [True, False, False])
        indices, state = weighted_sample_stratified_resume_indices(
            self.ITEMS, weights, self.STRATA, quotas, state, 2)
        self.assertEqual(indices, self._strata_slice(full, quotas, 1, 3))
        # 精确权重状态同样可经 serialize_metrics 往返。
        restored = deserialize_metrics(serialize_metrics(state))
        indices2, _ = weighted_sample_stratified_resume_indices(
            self.ITEMS, weights, self.STRATA, quotas, restored, 0)
        self.assertEqual(indices2, [])

    def test_checkpoint_validation_errors(self):
        # start 类型 / 取值与窗口规则。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                self.SEED, start=1.5)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                self.SEED, start=-1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                self.SEED, start=len(self.QUOTAS) + 1)
        # 与一次性入口一致的输入校验与异常类别。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, "strata", self.QUOTAS, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, 1], self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, -1, 2],
                self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, 0, 99],
                self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, [-1] + self.WEIGHTS[1:], self.STRATA,
                self.QUOTAS, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, [float("nan")] * 8, self.STRATA, self.QUOTAS,
                self.SEED)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_checkpoint(
                self.ITEMS, ["1"] * 8, self.STRATA, self.QUOTAS, self.SEED)

    def test_resume_state_type_and_structure_errors(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        # 非映射状态: TypeError。
        for bad_state in (None, 42, ["state"], "state"):
            with self.assertRaises(TypeError):
                weighted_sample_stratified_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                    bad_state, 1)
            with self.assertRaises(TypeError):
                weighted_sample_stratified_resume(
                    self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                    bad_state, 1)
        # 字段缺失 / 额外、版本、kind、摘要篡改: 统一 ValueError。
        missing = dict(state)
        del missing["digest"]
        extra = dict(state, unexpected=1)
        bad_version = dict(state, version=99)
        bad_kind = dict(state, kind="k_schedule")
        tampered = dict(state, position=2)
        tampered_rng = dict(state)
        tampered_rng["rng"] = dict(tampered_rng["rng"], mt=[0] * 625)
        for bad_state in (missing, extra, bad_version, bad_kind, tampered,
                          tampered_rng):
            with self.assertRaises(ValueError):
                weighted_sample_stratified_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                    bad_state, 1)

    def test_resume_input_mismatch_errors(self):
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS, self.SEED,
            start=1)
        # 与创建时不同的 items / weights / strata / quotas: ValueError。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                ["a", "b", "c", "d", "e", "f", "g", "z"], self.WEIGHTS,
                self.STRATA, self.QUOTAS, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, [1] * 8, self.STRATA, self.QUOTAS, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, [0, 0, 1, 1, 1, 2, 2, 2],
                self.QUOTAS, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, 1, 2], state, 1)
        # 非法输入沿用分层入口的异常类别。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, "strata", self.QUOTAS, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, 2], state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, [float("inf")] * 8, self.STRATA, self.QUOTAS,
                state, 1)
        # draws 规则与既有批量入口一致。
        with self.assertRaises(TypeError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                state, 1.5)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS,
                state, -1)

    def test_empty_plan_session(self):
        state = weighted_sample_stratified_checkpoint([], [], [], [], 3)
        self.assertEqual(state["position"], 0)
        self.assertEqual(state["strata_count"], 0)
        indices, next_state = weighted_sample_stratified_resume_indices(
            [], [], [], [], state, 0)
        self.assertEqual(indices, [])
        self.assertEqual(next_state, state)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                [], [], [], [], state, 1)

    def test_all_zero_quotas_session(self):
        quotas = [0, 0, 0]
        state = weighted_sample_stratified_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, quotas, self.SEED)
        indices, state = weighted_sample_stratified_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, quotas, state, 3)
        self.assertEqual(indices, [])
        self.assertEqual(state["position"], 3)

    def test_no_partial_output_and_no_mutation_on_error(self):
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        strata = list(self.STRATA)
        quotas = list(self.QUOTAS)
        state = weighted_sample_stratified_checkpoint(
            items, weights, strata, quotas, self.SEED, start=1)
        snapshot = dict(state)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume_indices(
                items, weights, strata, quotas, state, 99)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_resume(
                items, [float("nan")] * 8, strata, quotas, state, 1)
        self.assertEqual(state, snapshot)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(strata, self.STRATA)
        self.assertEqual(quotas, self.QUOTAS)


class WeightedSampleStratifiedScheduleTest(unittest.TestCase):
    ITEMS = ["a", "b", "c", "d", "e", "f", "g", "h"]
    WEIGHTS = [5, 1, 3, 2, 4, 1, 2, 6]
    STRATA = [0, 0, 1, 1, 2, 2, 2, 2]
    QUOTAS_SCHEDULE = [[1, 1, 2], [0, 2, 1], [2, 0, 1], [0, 0, 0], [1, 1, 1]]
    SEED = 20240613

    def test_deterministic_same_seed(self):
        first = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        second = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 5)

    def test_round_shape_and_layer_concatenation(self):
        rounds = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        for row, round_indices in zip(self.QUOTAS_SCHEDULE, rounds):
            # 每轮长度等于该行配额总和, 各层按编号升序拼接。
            self.assertEqual(len(round_indices), sum(row))
            cursor = 0
            for number, quota in enumerate(row):
                segment = round_indices[cursor:cursor + quota]
                cursor += quota
                for position in segment:
                    self.assertEqual(self.STRATA[position], number)
            # 轮内位置互不重复(每个位置只属于一个分层, 层内无放回)。
            self.assertEqual(len(set(round_indices)), len(round_indices))

    def test_single_row_matches_fixed_stratified_entry(self):
        quotas = [1, 1, 2]
        for seed in (0, 1, 7, 99):
            scheduled = weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [quotas], 1, seed)
            self.assertEqual(
                scheduled,
                [weighted_sample_stratified_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA, quotas, seed)])
            self.assertEqual(
                weighted_sample_stratified_schedule(
                    self.ITEMS, self.WEIGHTS, self.STRATA, [quotas], 1, seed),
                [weighted_sample_stratified(
                    self.ITEMS, self.WEIGHTS, self.STRATA, quotas, seed)])

    def test_single_stratum_matches_many_entry(self):
        # 全部位置同属编号零的单层且每行配额相同: 与 weighted_sample_many
        # 同参调用逐轮逐项一致。
        strata = [0] * len(self.ITEMS)
        schedule = [[2]] * 4
        self.assertEqual(
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, strata, schedule, 4, self.SEED),
            weighted_sample_many_indices(
                self.ITEMS, self.WEIGHTS, 2, 4, self.SEED))

    def test_start_window_matches_full_run_slice(self):
        full = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        for start in range(6):
            window = weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
                5 - start, self.SEED, start)
            self.assertEqual(window, full[start:])

    def test_skipped_rounds_consume_stream_by_their_row(self):
        # 被跳过的轮次按各自配额行消耗随机流: 改变被跳过行的配额会改变
        # 后续轮次, 但窗口切片语义保持不变(与完整调用对齐)。
        full = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        tail = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            2, self.SEED, 3)
        self.assertEqual(tail, full[3:])

    def test_zero_quota_layers_do_not_consume_stream(self):
        # 行内零配额分层不消耗随机流: 把中间层配额从零改为零不影响结果;
        # 与把该层从计划中移除(编号前移)的紧凑计划逐项一致。
        items = ["a", "b", "c", "d", "e", "f"]
        weights = [3, 1, 2, 2, 4, 1]
        strata = [0, 0, 1, 1, 2, 2]
        with_gap = weighted_sample_stratified_schedule_indices(
            items, weights, strata, [[1, 0, 1], [1, 0, 1]], 2, self.SEED)
        compact_items = [items[0], items[1], items[4], items[5]]
        compact_weights = [weights[0], weights[1], weights[4], weights[5]]
        compact_strata = [0, 0, 1, 1]
        compact = weighted_sample_stratified_schedule_indices(
            compact_items, compact_weights, compact_strata,
            [[1, 1], [1, 1]], 2, self.SEED)
        remap = [0, 1, 4, 5]
        self.assertEqual(
            with_gap, [[remap[i] for i in round_] for round_ in compact])

    def test_all_zero_quota_round_returns_empty_and_consumes_nothing(self):
        # 全零配额的轮次返回空列表且不消耗随机流: 移除该行后相邻轮次不变。
        schedule = self.QUOTAS_SCHEDULE
        full = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, schedule, 5, self.SEED)
        self.assertEqual(full[3], [])
        trimmed = [row for j, row in enumerate(schedule) if j != 3]
        expected = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, trimmed, 4, self.SEED)
        self.assertEqual(full[:3] + full[4:], expected)

    def test_values_entry_corresponds_to_indices_entry(self):
        rounds = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        values = weighted_sample_stratified_schedule(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        self.assertEqual(
            values, [[self.ITEMS[i] for i in r] for r in rounds])

    def test_duplicate_values_distinct_positions(self):
        items = ["x", "x", "x", "x"]
        weights = [1, 1, 1, 1]
        strata = [0, 0, 1, 1]
        rounds = weighted_sample_stratified_schedule_indices(
            items, weights, strata, [[1, 1], [2, 2]], 2, 5)
        self.assertEqual(len(set(rounds[0])), 2)
        self.assertEqual(len(set(rounds[1])), 4)
        values = weighted_sample_stratified_schedule(
            items, weights, strata, [[1, 1], [2, 2]], 2, 5)
        self.assertEqual(
            values, [[items[i] for i in r] for r in rounds])

    def test_zero_weight_never_chosen(self):
        items = ["a", "b", "c", "d"]
        weights = [0, 3, 0, 2]
        strata = [0, 0, 1, 1]
        for seed in range(20):
            rounds = weighted_sample_stratified_schedule_indices(
                items, weights, strata, [[1, 1]] * 3, 3, seed)
            self.assertEqual(rounds, [[1, 3]] * 3)

    def test_counts_match_flattened_index_rounds(self):
        rounds = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        counts = weighted_sample_stratified_schedule_counts(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        expected = [0] * len(self.ITEMS)
        for round_indices in rounds:
            for position in round_indices:
                expected[position] += 1
        self.assertEqual(counts, expected)
        self.assertEqual(len(counts), len(self.ITEMS))

    def test_counts_window_matches_index_window(self):
        counts = weighted_sample_stratified_schedule_counts(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            2, self.SEED, 2)
        rounds = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            2, self.SEED, 2)
        expected = [0] * len(self.ITEMS)
        for round_indices in rounds:
            for position in round_indices:
                expected[position] += 1
        self.assertEqual(counts, expected)

    def test_counts_are_exact_integers_and_serialize_roundtrip(self):
        counts = weighted_sample_stratified_schedule_counts(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        self.assertTrue(all(isinstance(c, int) for c in counts))
        self.assertEqual(
            deserialize_metrics(serialize_metrics(counts)), counts)

    def test_stream_matches_batch_round_by_round(self):
        batch = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        streamed = list(weighted_sample_stratified_schedule_stream_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED))
        self.assertEqual(streamed, batch)
        for start in range(6):
            draws = 5 - start
            streamed_window = list(
                weighted_sample_stratified_schedule_stream_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, draws, self.SEED, start))
            self.assertEqual(streamed_window, batch[start:])

    def test_stream_values_match_batch_values(self):
        values = weighted_sample_stratified_schedule(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        streamed = list(weighted_sample_stratified_schedule_stream(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED))
        self.assertEqual(streamed, values)

    def test_draws_zero_returns_empty_after_full_validation(self):
        self.assertEqual(
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, 0, self.SEED), [])
        self.assertEqual(
            weighted_sample_stratified_schedule(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, 0, self.SEED), [])
        self.assertEqual(
            weighted_sample_stratified_schedule_counts(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, 0, self.SEED),
            [0] * len(self.ITEMS))
        self.assertEqual(
            list(weighted_sample_stratified_schedule_stream_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, 0, self.SEED)), [])
        # draws=0 仍校验完整计划、每行可行性与窗口。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                [[1, 1, 9]], 0, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_counts(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, 0, self.SEED, 6)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                [[1, 1, True]], 0, self.SEED)

    def test_empty_items_requires_empty_strata_and_rows(self):
        self.assertEqual(
            weighted_sample_stratified_schedule_indices(
                [], [], [], [[], []], 2, self.SEED), [[], []])
        self.assertEqual(
            weighted_sample_stratified_schedule_counts(
                [], [], [], [[]], 1, self.SEED), [])
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                [], [], [0], [[]], 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                [], [], [], [[1]], 1, self.SEED)

    def test_structure_errors_raise_type_error(self):
        args = (self.ITEMS, self.WEIGHTS, self.STRATA)
        entries = (
            weighted_sample_stratified_schedule_indices,
            weighted_sample_stratified_schedule_counts,
        )
        for entry in entries:
            with self.assertRaises(TypeError):
                entry(*args, "not-a-sequence", 1, self.SEED)
            with self.assertRaises(TypeError):
                entry(*args, [[1, 1], 3], 1, self.SEED)
            with self.assertRaises(TypeError):
                entry(*args, [[1, 1, True]], 1, self.SEED)
            with self.assertRaises(TypeError):
                entry(*args, [[1, 1, 1.0]], 1, self.SEED)
            with self.assertRaises(TypeError):
                entry(*args, [[1, 1, "1"]], 1, self.SEED)
            with self.assertRaises(TypeError):
                entry(self.ITEMS, self.WEIGHTS, [0, 0, 1, 1, 2, 2, 2, "x"],
                      [[1, 1, 1]], 1, self.SEED)
            with self.assertRaises(TypeError):
                entry(self.ITEMS, self.WEIGHTS, [0, 0, 1, 1, 2, 2, 2, True],
                      [[1, 1, 1]], 1, self.SEED)
            with self.assertRaises(TypeError):
                entry(*args, self.QUOTAS_SCHEDULE, True, self.SEED)
            with self.assertRaises(TypeError):
                entry(*args, self.QUOTAS_SCHEDULE, 1.5, self.SEED)
            with self.assertRaises(TypeError):
                entry(*args, self.QUOTAS_SCHEDULE, 1, self.SEED, True)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_schedule_stream_indices(
                *args, self.QUOTAS_SCHEDULE, "x", self.SEED)

    def test_value_errors(self):
        args = (self.ITEMS, self.WEIGHTS, self.STRATA)
        # 行长度不等于最大编号加一。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                *args, [[1, 1]], 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                *args, [[1, 1, 1, 0]], 1, self.SEED)
        # 负配额。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                *args, [[1, -1, 1]], 1, self.SEED)
        # strata 长度与编号范围。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, [0, 0, 1], [[1]], 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, [0, 0, 1, 1, 2, 2, 2, -1],
                [[1, 1, 1]], 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, [0, 0, 1, 1, 2, 2, 2, 5],
                [[1, 1, 1]], 1, self.SEED)
        # 窗口越界。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                *args, self.QUOTAS_SCHEDULE, 6, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                *args, self.QUOTAS_SCHEDULE, 2, self.SEED, 4)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                *args, self.QUOTAS_SCHEDULE, -1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                *args, self.QUOTAS_SCHEDULE, 1, self.SEED, -1)
        # 权重取值。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, [-1] + self.WEIGHTS[1:], self.STRATA,
                self.QUOTAS_SCHEDULE, 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, [float("nan")] * 8, self.STRATA,
                self.QUOTAS_SCHEDULE, 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, [float("inf")] * 8, self.STRATA,
                self.QUOTAS_SCHEDULE, 1, self.SEED)
        # 某一行某层正权重不足配额(编号 2 的层只有 4 个正权重位置)。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                [[1, 1, 5]], 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, [0, 0, 3, 2, 4, 1, 2, 6], self.STRATA,
                [[1, 0, 0]], 1, self.SEED)
        # 错误同样出现在计数与流式入口(创建时)。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_counts(
                *args, [[1, 1, 9]], 1, self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_stream_indices(
                *args, [[1, 1, 9]], 1, self.SEED)

    def test_fraction_decimal_and_huge_integer_weights(self):
        weights = [Fraction(1, 3), Decimal("0.5"), 10 ** 60, 2,
                   Fraction(2, 5), Decimal("1.25"), 1, 10 ** 40 + 7]
        first = weighted_sample_stratified_schedule_indices(
            self.ITEMS, weights, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        second = weighted_sample_stratified_schedule_indices(
            self.ITEMS, weights, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        self.assertEqual(first, second)
        for row, round_indices in zip(self.QUOTAS_SCHEDULE, first):
            self.assertEqual(len(round_indices), sum(row))
        # 单行单层等价于对应精确权重入口。
        self.assertEqual(
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, weights, [0] * 8, [[3]], 1, self.SEED),
            [weighted_sample_indices(self.ITEMS, weights, 3, self.SEED)])
        # 超大整数权重(10**60 等)走纯整数精确路径, 不被浮点吞掉: 与把
        # 同一权重写成 Fraction 的等价调用逐项一致。
        as_fractions = [Fraction(w) for w in weights]
        self.assertEqual(
            first,
            weighted_sample_stratified_schedule_indices(
                self.ITEMS, as_fractions, self.STRATA,
                self.QUOTAS_SCHEDULE, 5, self.SEED))

    def test_inputs_not_mutated(self):
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        strata = list(self.STRATA)
        schedule = [list(row) for row in self.QUOTAS_SCHEDULE]
        weighted_sample_stratified_schedule_indices(
            items, weights, strata, schedule, 5, self.SEED)
        weighted_sample_stratified_schedule(
            items, weights, strata, schedule, 5, self.SEED)
        weighted_sample_stratified_schedule_counts(
            items, weights, strata, schedule, 5, self.SEED)
        list(weighted_sample_stratified_schedule_stream_indices(
            items, weights, strata, schedule, 5, self.SEED))
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(strata, self.STRATA)
        self.assertEqual(
            schedule, [list(row) for row in self.QUOTAS_SCHEDULE])

    def test_fixed_quota_entries_unchanged(self):
        # 固定配额入口行为不受新增入口影响。
        indices = weighted_sample_stratified_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, [1, 1, 2], self.SEED)
        self.assertEqual(
            indices,
            weighted_sample_stratified_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA, [1, 1, 2], self.SEED))
        counts = weighted_sample_stratified_counts(
            self.ITEMS, self.WEIGHTS, self.STRATA, [1, 1, 2], self.SEED)
        expected = [0] * len(self.ITEMS)
        for position in indices:
            expected[position] += 1
        self.assertEqual(counts, expected)


class WeightedSampleStratifiedScheduleCheckpointTest(unittest.TestCase):
    ITEMS = ["a", "b", "c", "d", "e", "f", "g", "h"]
    WEIGHTS = [5, 1, 3, 2, 4, 1, 2, 6]
    STRATA = [0, 0, 1, 1, 2, 2, 2, 2]
    QUOTAS_SCHEDULE = [[1, 1, 2], [0, 2, 1], [2, 0, 1], [0, 0, 0], [1, 1, 1]]
    SEED = 731

    def _one_shot(self):
        return weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            len(self.QUOTAS_SCHEDULE), self.SEED)

    def test_checkpoint_state_is_json_native(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=2)
        # json 默认序列化/还原往返不报错且内容不变(只含 JSON 原生值)。
        self.assertEqual(json.loads(json.dumps(state)), state)
        self.assertEqual(state["kind"], "stratified_schedule")
        self.assertEqual(state["position"], 2)
        self.assertEqual(state["n"], len(self.ITEMS))
        self.assertEqual(state["strata_count"], 3)
        self.assertEqual(
            state["schedule_length"], len(self.QUOTAS_SCHEDULE))

    def test_resume_window_equals_one_shot_slice(self):
        full = self._one_shot()
        for start in range(len(self.QUOTAS_SCHEDULE) + 1):
            state = weighted_sample_stratified_schedule_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, self.SEED, start=start)
            draws = len(self.QUOTAS_SCHEDULE) - start
            rounds, _ = weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, draws)
            self.assertEqual(rounds, full[start:])

    def test_chained_resumes_equal_one_shot_run(self):
        full = self._one_shot()
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED)
        chained = []
        for draws in (1, 2, 0, 2):
            rounds, state = \
                weighted_sample_stratified_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, state, draws)
            chained.extend(rounds)
        self.assertEqual(chained, full)
        self.assertEqual(
            state["position"], len(self.QUOTAS_SCHEDULE))

    def test_value_resume_matches_index_resume(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=1)
        index_rounds, index_state = \
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 3)
        value_rounds, value_state = \
            weighted_sample_stratified_schedule_resume(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 3)
        self.assertEqual(
            value_rounds,
            [[self.ITEMS[i] for i in r] for r in index_rounds])
        # 两个入口的下一状态逐字段一致, 可互换续接。
        self.assertEqual(index_state, value_state)
        tail_i, _ = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA,
            self.QUOTAS_SCHEDULE, value_state, 1)
        tail_v, _ = weighted_sample_stratified_schedule_resume(
            self.ITEMS, self.WEIGHTS, self.STRATA,
            self.QUOTAS_SCHEDULE, index_state, 1)
        self.assertEqual(
            tail_v, [[self.ITEMS[i] for i in r] for r in tail_i])

    def test_resume_values_handle_duplicate_items_by_position(self):
        items = ["x", "x", "x", "x"]
        weights = [1, 1, 1, 1]
        strata = [0, 0, 1, 1]
        schedule = [[1, 1], [2, 2]]
        state = weighted_sample_stratified_schedule_checkpoint(
            items, weights, strata, schedule, 5)
        index_rounds, _ = \
            weighted_sample_stratified_schedule_resume_indices(
                items, weights, strata, schedule, state, 2)
        value_rounds, _ = weighted_sample_stratified_schedule_resume(
            items, weights, strata, schedule, state, 2)
        self.assertEqual(
            value_rounds,
            [[items[i] for i in r] for r in index_rounds])

    def test_draws_zero_returns_empty_and_state_copy(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=2)
        rounds, next_state = \
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(next_state, state)
        self.assertIsNot(next_state, state)

    def test_zero_quota_rounds_advance_position_without_rng(self):
        # 全零配额的轮次只推进 position, 不消耗随机流: 跨过该行的恢复与
        # 一次性调用逐项一致。
        schedule = [[1, 0, 1], [0, 0, 0], [1, 1, 0]]
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, schedule,
            self.SEED, start=1)
        rounds, state = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, schedule, state, 2)
        full = weighted_sample_stratified_schedule_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, schedule, 3, self.SEED)
        self.assertEqual(rounds, full[1:])
        self.assertEqual(rounds[0], [])
        self.assertEqual(state["position"], 3)

    def test_end_of_plan_accepts_only_empty_window(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=len(self.QUOTAS_SCHEDULE))
        rounds, next_state = \
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(
            next_state["position"], len(self.QUOTAS_SCHEDULE))
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 1)

    def test_resume_window_out_of_range(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=3)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 3)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 3)

    def test_state_survives_serialize_metrics_round_trip(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=2)
        restored = deserialize_metrics(serialize_metrics(state))
        expected, _ = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA,
            self.QUOTAS_SCHEDULE, state, 2)
        actual, next_state = \
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, restored, 2)
        self.assertEqual(actual, expected)
        # 下一状态同样可序列化往返并继续恢复。
        full = self._one_shot()
        restored_next = deserialize_metrics(serialize_metrics(next_state))
        tail, _ = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA,
            self.QUOTAS_SCHEDULE, restored_next, 1)
        self.assertEqual(tail, full[4:])

    def test_state_survives_json_round_trip(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=1)
        restored = json.loads(json.dumps(state))
        rounds, _ = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA,
            self.QUOTAS_SCHEDULE, restored, 2)
        self.assertEqual(rounds, self._one_shot()[1:3])

    def test_exact_weight_types_supported(self):
        weights = [Fraction(1, 3), Decimal("0.5"), 10 ** 60, 2,
                   Fraction(2, 5), Decimal("1.25"), 1, 10 ** 40 + 7]
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, weights, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=1)
        rounds, _ = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, weights, self.STRATA, self.QUOTAS_SCHEDULE,
            state, 4)
        full = weighted_sample_stratified_schedule_indices(
            self.ITEMS, weights, self.STRATA, self.QUOTAS_SCHEDULE,
            5, self.SEED)
        self.assertEqual(rounds, full[1:])
        # 状态可经 serialize_metrics 往返(超大整数保持精确十进制)。
        restored = deserialize_metrics(serialize_metrics(state))
        again, _ = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, weights, self.STRATA, self.QUOTAS_SCHEDULE,
            restored, 4)
        self.assertEqual(again, rounds)

    def test_checkpoint_validates_like_batch_entry(self):
        with self.assertRaises(TypeError):
            weighted_sample_stratified_schedule_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                [[1, 1, True]], self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                [[1, 1, 9]], self.SEED)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, self.SEED, start=6)
        with self.assertRaises(TypeError):
            weighted_sample_stratified_schedule_checkpoint(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, self.SEED, start=1.5)
        # start == 计划长度合法。
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=len(self.QUOTAS_SCHEDULE))
        self.assertEqual(
            state["position"], len(self.QUOTAS_SCHEDULE))

    def test_resume_rejects_non_mapping_state(self):
        for bad in (None, 42, "state", [("position", 0)]):
            with self.assertRaises(TypeError):
                weighted_sample_stratified_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, bad, 1)
            with self.assertRaises(TypeError):
                weighted_sample_stratified_schedule_resume(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, bad, 1)

    def test_resume_rejects_bad_draws(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED)
        for bad in (True, 1.5, "1", None):
            with self.assertRaises(TypeError):
                weighted_sample_stratified_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, state, bad)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, state, -1)

    def test_resume_rejects_structurally_invalid_state(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=1)
        import copy as _copy
        # 缺失字段。
        for key in state:
            bad = dict(state)
            del bad[key]
            with self.assertRaises(ValueError):
                weighted_sample_stratified_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, bad, 1)
        # 多余字段。
        bad = dict(state)
        bad["extra"] = 1
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, bad, 1)
        # 版本 / kind 不支持。
        for key, value in (("version", 2), ("version", "1"),
                           ("kind", "stratified"), ("kind", "schedule")):
            bad = dict(state)
            bad[key] = value
            with self.assertRaises(ValueError):
                weighted_sample_stratified_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, bad, 1)
        # 篡改字段(摘要失配)。
        for key, value in (("position", 0), ("n", 7), ("strata_count", 2),
                           ("schedule_length", 4)):
            bad = _copy.deepcopy(state)
            bad[key] = value
            with self.assertRaises(ValueError):
                weighted_sample_stratified_schedule_resume_indices(
                    self.ITEMS, self.WEIGHTS, self.STRATA,
                    self.QUOTAS_SCHEDULE, bad, 1)
        # 篡改抽样路径标记与 RNG 快照。
        bad = _copy.deepcopy(state)
        bad["exact"][0][0] = not bad["exact"][0][0]
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, bad, 1)
        bad = _copy.deepcopy(state)
        bad["rng"]["mt"][0] += 1
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE, bad, 1)

    def test_resume_rejects_mismatched_inputs(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE,
            self.SEED, start=1)
        # items / weights / strata / quotas_schedule 任一不匹配都拒绝。
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                ["a", "b", "c", "d", "e", "f", "g", "z"],
                self.WEIGHTS, self.STRATA, self.QUOTAS_SCHEDULE, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, [5, 1, 3, 2, 4, 1, 2, 7],
                self.STRATA, self.QUOTAS_SCHEDULE, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, [0, 0, 1, 1, 2, 2, 2, 1],
                self.QUOTAS_SCHEDULE, state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                [[0, 1, 2]] + self.QUOTAS_SCHEDULE[1:], state, 1)
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, self.WEIGHTS, self.STRATA,
                self.QUOTAS_SCHEDULE + [[0, 0, 0]], state, 1)
        # 权重类型变化(同值不同类型)同样改变抽样路径, 必须拒绝。
        weights = list(self.WEIGHTS)
        weights[0] = 5.0
        with self.assertRaises(ValueError):
            weighted_sample_stratified_schedule_resume_indices(
                self.ITEMS, weights, self.STRATA,
                self.QUOTAS_SCHEDULE, state, 1)

    def test_resume_does_not_mutate_inputs_or_state(self):
        items = list(self.ITEMS)
        weights = list(self.WEIGHTS)
        strata = list(self.STRATA)
        schedule = [list(row) for row in self.QUOTAS_SCHEDULE]
        state = weighted_sample_stratified_schedule_checkpoint(
            items, weights, strata, schedule, self.SEED, start=1)
        import copy as _copy
        snapshot = _copy.deepcopy(state)
        weighted_sample_stratified_schedule_resume_indices(
            items, weights, strata, schedule, state, 2)
        weighted_sample_stratified_schedule_resume(
            items, weights, strata, schedule, state, 2)
        self.assertEqual(state, snapshot)
        self.assertEqual(items, self.ITEMS)
        self.assertEqual(weights, self.WEIGHTS)
        self.assertEqual(strata, self.STRATA)
        self.assertEqual(
            schedule, [list(row) for row in self.QUOTAS_SCHEDULE])

    def test_empty_plan_session(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            self.ITEMS, self.WEIGHTS, self.STRATA, [], self.SEED)
        self.assertEqual(state["position"], 0)
        self.assertEqual(state["schedule_length"], 0)
        rounds, state = weighted_sample_stratified_schedule_resume_indices(
            self.ITEMS, self.WEIGHTS, self.STRATA, [], state, 0)
        self.assertEqual(rounds, [])
        self.assertEqual(state["position"], 0)

    def test_empty_items_session(self):
        state = weighted_sample_stratified_schedule_checkpoint(
            [], [], [], [[], []], self.SEED)
        rounds, state = weighted_sample_stratified_schedule_resume_indices(
            [], [], [], [[], []], state, 2)
        self.assertEqual(rounds, [[], []])
        self.assertEqual(state["position"], 2)


if __name__ == "__main__":
    unittest.main()
