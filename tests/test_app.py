import math
import unittest

import app
from app import weighted_sample, weighted_sample_indices, serialize_metrics


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


class ExactBigIntSampleTest(unittest.TestCase):
    """累计整数权重超过 2**53 时的任意精度精确路径。"""

    BIG = 10 ** 100

    def test_huge_weights_multiround(self):
        items = ["a", "b", "c"]
        weights = [self.BIG, 2 * self.BIG, 3 * self.BIG]
        idx = weighted_sample_indices(items, weights, 3, 42)
        self.assertEqual(sorted(idx), [0, 1, 2])
        self.assertEqual(len(set(idx)), 3)
        self.assertEqual(
            weighted_sample(items, weights, 3, 42),
            [items[i] for i in idx],
        )
        # 相同 seed 与输入 -> 唯一相同序列。
        for _ in range(5):
            self.assertEqual(
                weighted_sample_indices(items, weights, 3, 42), idx
            )

    def test_extreme_disparity_tiny_weights_not_swallowed(self):
        # 微小正权重相对 10**100 仍存在, 大权重被抽走后必被选中。
        items = ["tiny1", "tiny2", "huge"]
        weights = [1, 1, self.BIG]
        for seed in range(30):
            idx = weighted_sample_indices(items, weights, 3, seed)
            self.assertEqual(sorted(idx), [0, 1, 2])
            # 两个单位权重位置都必须出现在序列中。
            self.assertIn(0, idx)
            self.assertIn(1, idx)

    def test_zero_weight_never_chosen_on_exact_path(self):
        items = ["zero", "big", "zero2"]
        weights = [0, self.BIG, 0]
        for seed in range(50):
            self.assertEqual(
                weighted_sample_indices(items, weights, 1, seed), [1]
            )
        # 大权重被抽走后只剩零权重 -> 唯一结果 ValueError。
        with self.assertRaises(ValueError):
            weighted_sample_indices(items, weights, 2, 0)

    def test_exact_path_engages_above_threshold(self):
        # 总权重 2**54 > 2**53, 两个位置比例精确各半, 多种子下都能居首。
        weights = [1 << 53, 1 << 53]
        firsts = {
            weighted_sample_indices(["a", "b"], weights, 1, seed)[0]
            for seed in range(60)
        }
        self.assertEqual(firsts, {0, 1})

    def test_at_threshold_keeps_baseline_float_path(self):
        # 累计值恰为 2**53 时仍走基线浮点路径, 序列语义不变。
        weights = [1 << 53, 1, 2]
        out = weighted_sample(["a", "b", "c"], weights, 2, 7)
        self.assertEqual(out, weighted_sample(["a", "b", "c"], weights, 2, 7))
        self.assertEqual(len(out), 2)

    def test_beyond_float_range_still_exact(self):
        # 累计值无法转换为有限浮点数(超出 float 上限)也必须正常工作。
        weights = [10 ** 400, 10 ** 400, 1]
        idx = weighted_sample_indices(["x", "y", "z"], weights, 3, 5)
        self.assertEqual(sorted(idx), [0, 1, 2])
        self.assertEqual(
            weighted_sample_indices(["x", "y", "z"], weights, 3, 5), idx
        )

    def test_k_zero_validates_then_returns_empty(self):
        self.assertEqual(
            weighted_sample_indices(["a", "b"], [self.BIG, 1], 0, 0), []
        )
        with self.assertRaises(ValueError):
            weighted_sample_indices(["a"], [float("nan")], 0, 0)
        with self.assertRaises(TypeError):
            weighted_sample_indices(["a"], [True], 0, 0)

    def test_inputs_not_mutated_on_exact_path(self):
        items = ["a", "b", "c"]
        weights = [self.BIG, 1, 0]
        items_snapshot = list(items)
        weights_snapshot = list(weights)
        weighted_sample_indices(items, weights, 2, 9)
        self.assertEqual(items, items_snapshot)
        self.assertEqual(weights, weights_snapshot)

    def test_indices_valid_and_match_values_entry(self):
        items = list(range(6))
        weights = [self.BIG, 1, 0, 3 * self.BIG, 7, 2]
        for seed in range(20):
            idx = weighted_sample_indices(items, weights, 4, seed)
            self.assertEqual(len(idx), 4)
            self.assertEqual(len(set(idx)), 4)
            self.assertTrue(all(0 <= i < len(items) for i in idx))
            self.assertNotIn(2, idx)  # 零权重位置
            self.assertEqual(
                [items[i] for i in idx],
                weighted_sample(items, weights, 4, seed),
            )

    def test_mixed_int_float_weights_keep_float_rules(self):
        # 含非整数权重时仍按既有浮点规则, 不进入精确路径。
        weights = [self.BIG, 0.5]
        out = weighted_sample(["a", "b"], weights, 1, 3)
        self.assertEqual(out, ["a"])
        self.assertEqual(weighted_sample(["a", "b"], weights, 1, 3), out)


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


if __name__ == "__main__":
    unittest.main()
