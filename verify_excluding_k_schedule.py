"""weighted_sample_excluding_k_schedule_* 新入口的独立验证脚本。

覆盖:
 1. 批量 vs 手动逐轮(同 seed 流, 零样本轮不耗流, 排除位置/零权重永不入选)
 2. 值入口按位置映射 items, 重复值按位置区分
 3. 流式物化 == 批量; start 跳过只耗完整轮次; 窗口切片语义
 4. 频次 == 批量摊平; draws=0 / k=0 / 混合零项
 5. excluded 集合语义(重复+乱序); excluded=() == k_schedule 入口
 6. k_schedule 各项相等 == 固定 k 排除入口
 7. checkpoint/resume: 分段 == 一次性窗口; JSON/serialize_metrics 往返;
    跨种恢复; 精确路径(Fraction/Decimal/超大整数); 状态防篡改与异常
 8. 校验顺序与异常类别(TypeError vs ValueError, 不修改输入, 无部分结果)
"""
import copy
import json
import random
import unittest
from decimal import Decimal
from fractions import Fraction

import app as A
from app import (
    weighted_sample_excluding_k_schedule_indices as bks_idx,
    weighted_sample_excluding_k_schedule as bks_val,
    weighted_sample_excluding_k_schedule_stream_indices as bks_stream_idx,
    weighted_sample_excluding_k_schedule_stream as bks_stream_val,
    weighted_sample_excluding_k_schedule_counts as bks_counts,
    weighted_sample_excluding_k_schedule_checkpoint as bks_ckpt,
    weighted_sample_excluding_k_schedule_resume_indices as bks_resume_idx,
    weighted_sample_excluding_k_schedule_resume as bks_resume,
    weighted_sample_k_schedule_indices as ks_idx,
    weighted_sample_k_schedule_stream_indices as ks_stream_idx,
    weighted_sample_k_schedule_counts as ks_counts,
    weighted_sample_k_schedule_checkpoint as ks_ckpt,
    weighted_sample_k_schedule_resume_indices as ks_resume_idx,
    weighted_sample_many_excluding_indices as me_idx,
    weighted_sample_many_excluding as me_val,
    weighted_sample_stream_excluding_indices as me_stream_idx,
    weighted_sample_excluding_counts as me_counts,
    weighted_sample_excluding_checkpoint as me_ckpt,
    weighted_sample_excluding_resume_indices as me_resume_idx,
    weighted_sample_excluding_indices as se_idx,
    serialize_metrics,
    deserialize_metrics,
)

ITEMS = ["a", "b", "x", "x", "e", "f"]
WEIGHTS = [3, 0, 7, 2, 1, 4]
KS = [2, 0, 3, 1, 0, 2]
EX = (1, 4)
EX_SEQ = [4, 1, 1, 4]  # 重复 + 乱序, 与 EX 等价


def manual_rounds(items, weights, k_schedule, excluded, draws, seed, start):
    """与规格一致的独立简化实现(每轮手动加权无放回), 用于交叉验证。"""
    n = len(items)
    excl = set(excluded)
    rng = random.Random(seed)
    out = []
    for j in range(start + draws):
        k = k_schedule[j]
        if j >= start:
            out.append([])
        if k == 0:
            continue
        pool = [i for i in range(n) if i not in excl]
        w = [float(weights[i]) for i in pool]
        chosen = []
        for _ in range(k):
            total = sum(w)
            needle = rng.random() * total
            acc = 0
            for t, ww in enumerate(w):
                acc += ww
                if needle < acc:
                    chosen.append(pool[t])
                    pool.pop(t)
                    w.pop(t)
                    break
        if j >= start:
            out[-1] = chosen
    return out


class CoreBehavior(unittest.TestCase):
    def test_batch_matches_manual(self):
        got = bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=7)
        want = manual_rounds(ITEMS, WEIGHTS, KS, EX, 6, 7, 0)
        self.assertEqual(got, want)

    def test_values_map_by_position(self):
        rounds_i = bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=7)
        rounds_v = bks_val(ITEMS, WEIGHTS, KS, EX, 6, seed=7)
        self.assertEqual(
            rounds_v, [[ITEMS[i] for i in r] for r in rounds_i]
        )
        # 重复值按位置区分: 位置 2 和 3 都是 "x", 一轮 k=3 可能同时选中。
        self.assertTrue(any(len(set(r) - set(EX)) == 3 for r in rounds_i))
        full = bks_val(["q", "q", "q"], [1, 1, 1], [3], (), 1, seed=1)
        self.assertEqual(full, [["q", "q", "q"]])

    def test_excluded_and_zero_never_chosen(self):
        for r in bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=123):
            self.assertFalse(set(EX).intersection(r))
            self.assertNotIn(1, r)  # 零权重 + 排除双重保证
            self.assertEqual(len(r), len(set(r)))  # 轮内无放回

    def test_excluded_set_semantics(self):
        base = bks_idx(ITEMS, WEIGHTS, KS, (), 6, seed=5)
        with_dup = bks_idx(ITEMS, WEIGHTS, KS, EX_SEQ, 6, seed=5)
        with_set = bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=5)
        self.assertEqual(with_dup, with_set)
        self.assertNotEqual(base, with_set)

    def test_empty_excluded_matches_k_schedule(self):
        for kwargs in (
            dict(draws=6, seed=3),
            dict(draws=3, seed=3, start=2),
            dict(draws=0, seed=8, start=3),
        ):
            self.assertEqual(
                bks_idx(ITEMS, WEIGHTS, KS, (), **kwargs),
                ks_idx(ITEMS, WEIGHTS, KS, **kwargs),
            )

    def test_constant_k_matches_fixed_excluding(self):
        k = 2
        schedule = [k] * 5
        for kwargs in (
            dict(draws=5, seed=11),
            dict(draws=3, seed=11, start=2),
            dict(draws=0, seed=11, start=5),
        ):
            d = dict(kwargs)
            d.pop("start", None)
            self.assertEqual(
                bks_idx(ITEMS, WEIGHTS, schedule, EX, kwargs["draws"],
                        kwargs.get("seed", 0), kwargs.get("start", 0)),
                me_idx(ITEMS, WEIGHTS, k, EX, kwargs["draws"],
                       kwargs.get("seed", 0), kwargs.get("start", 0)),
            )

    def test_start_window_slice(self):
        full = bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=9)
        for start, draws in ((0, 6), (1, 5), (2, 3), (5, 1), (6, 0)):
            self.assertEqual(
                bks_idx(ITEMS, WEIGHTS, KS, EX, draws, seed=9, start=start),
                full[start:start + draws],
            )

    def test_stream_matches_batch(self):
        for kwargs in (
            dict(draws=6, seed=4),
            dict(draws=3, seed=4, start=2),
            dict(draws=0, seed=4, start=3),
            dict(draws=2, seed=42, start=4),
        ):
            self.assertEqual(
                list(bks_stream_idx(ITEMS, WEIGHTS, KS, EX, **kwargs)),
                bks_idx(ITEMS, WEIGHTS, KS, EX, **kwargs),
            )
            self.assertEqual(
                list(bks_stream_val(ITEMS, WEIGHTS, KS, EX, **kwargs)),
                bks_val(ITEMS, WEIGHTS, KS, EX, **kwargs),
            )

    def test_counts_match_flatten(self):
        rounds = bks_idx(ITEMS, WEIGHTS, KS, EX, 4, seed=21, start=1)
        flat = [0] * 6
        for r in rounds:
            for p in r:
                flat[p] += 1
        self.assertEqual(
            bks_counts(ITEMS, WEIGHTS, KS, EX, 4, seed=21, start=1), flat
        )
        # draws=0 / k_schedule 全零 -> 全零
        self.assertEqual(bks_counts(ITEMS, WEIGHTS, KS, EX, 0, seed=0),
                         [0] * 6)
        self.assertEqual(bks_counts(ITEMS, WEIGHTS, [0, 0], EX, 2, seed=0),
                         [0] * 6)
        # 排除位置始终为零
        counts = bks_counts(ITEMS, WEIGHTS, KS, EX, 6, seed=21)
        for p in set(EX):
            self.assertEqual(counts[p], 0)


class ExactPaths(unittest.TestCase):
    def test_fraction_decimal_hugeint(self):
        items = list(range(6))
        cases = [
            [Fraction(1, 10**30), Fraction(3, 7), 0, 5, Fraction(1, 1), 9],
            [Decimal("1E-50"), Decimal("3.5"), 0, Decimal("2"), 1, 4],
            [10**200, 2 * 10**200, 0, 3, 1, 7],
            [Decimal("1E100000"), 1, 0, Decimal("2.5"), Fraction(1, 3), 0],
        ]
        for w in cases:
            r = bks_idx(items, w, [3, 0, 2], (3,), 3, seed=3)
            self.assertEqual(len(r), 3)
            self.assertEqual(r[1], [])
            for rr in r:
                self.assertNotIn(3, rr)
            # 与独立精确参考一致(直接比较各入口与流式/计数)
            self.assertEqual(
                list(bks_stream_idx(items, w, [3, 0, 2], (3,), 3, seed=3)),
                r,
            )
            flat = [0] * 6
            for rr in r:
                for p in rr:
                    flat[p] += 1
            self.assertEqual(
                bks_counts(items, w, [3, 0, 2], (3,), 3, seed=3), flat
            )

    def test_metrics_roundtrip_counts(self):
        w = [Fraction(1, 7), Decimal("8.25"), 0, 10**500, 1, 0]
        counts = bks_counts(list(range(6)), w, [4, 2, 0], (5,), 3, seed=6)
        text = serialize_metrics(counts)
        back = deserialize_metrics(text)
        self.assertEqual(back, counts)
        self.assertTrue(all(isinstance(c, int) for c in back))


class CheckpointResume(unittest.TestCase):
    def test_segmented_equals_one_shot(self):
        full = bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=13)
        state = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13)
        self.assertEqual(state["kind"], "excluding_k_schedule")
        self.assertEqual(state["excluded"], sorted(EX))
        r1, state = bks_resume_idx(
            ITEMS, WEIGHTS, KS, EX, state, 2
        )
        r2, state = bks_resume_idx(
            ITEMS, WEIGHTS, KS, EX, state, 3
        )
        r3, state = bks_resume_idx(
            ITEMS, WEIGHTS, KS, EX, state, 1
        )
        self.assertEqual(r1 + r2 + r3, full)
        self.assertEqual(state["position"], 6)
        # 到计划末尾再 draws=0
        empty, end_state = bks_resume_idx(
            ITEMS, WEIGHTS, KS, EX, state, 0
        )
        self.assertEqual(empty, [])
        self.assertEqual(end_state, state)

    def test_start_checkpoint_matches_one_shot_window(self):
        full = bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=13)
        state = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13, start=4)
        rounds, _ = bks_resume_idx(ITEMS, WEIGHTS, KS, EX, state, 2)
        self.assertEqual(rounds, full[4:6])

    def test_value_resume_state_interchangeable(self):
        state = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13, start=1)
        v_rounds, st1 = bks_resume(ITEMS, WEIGHTS, KS, EX, state, 2)
        state2 = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13, start=1)
        i_rounds, st2 = bks_resume_idx(ITEMS, WEIGHTS, KS, EX, state2, 2)
        self.assertEqual(v_rounds, [[ITEMS[i] for i in r] for r in i_rounds])
        self.assertEqual(st1, st2)
        # 值入口产出的状态可交给索引入口继续
        r3, _ = bks_resume_idx(ITEMS, WEIGHTS, KS, EX, st1, 3)
        full = bks_idx(ITEMS, WEIGHTS, KS, EX, 6, seed=13)
        self.assertEqual(i_rounds + r3, full[1:])

    def test_roundtrip_serialize(self):
        w = [Fraction(1, 9), Decimal("2.25"), 0, 10**400, 1, 3]
        full = bks_idx(list(range(6)), w, KS, EX, 6, seed=4)
        state0 = bks_ckpt(list(range(6)), w, KS, EX, seed=4, start=2)
        for restore in (
            lambda s: deserialize_metrics(serialize_metrics(s)),
            lambda s: json.loads(json.dumps(s)),
        ):
            state = restore(state0)
            rounds, next_state = bks_resume_idx(
                list(range(6)), w, KS, EX, state, 4
            )
            self.assertEqual(rounds, full[2:])
            # 下一状态仍可往返并继续到结尾
            state2 = restore(next_state)
            tail, _ = bks_resume_idx(
                list(range(6)), w, KS, EX, state2, 0
            )
            self.assertEqual(tail, [])

    def test_excluded_empty_matches_k_schedule_resume(self):
        state = bks_ckpt(ITEMS, WEIGHTS, KS, (), seed=17, start=2)
        rounds, _ = bks_resume_idx(ITEMS, WEIGHTS, KS, (), state, 4)
        ks_state = ks_ckpt(ITEMS, WEIGHTS, KS, seed=17, start=2)
        ks_rounds, _ = ks_resume_idx(ITEMS, WEIGHTS, KS, ks_state, 4)
        self.assertEqual(rounds, ks_rounds)

    def test_constant_k_matches_fixed_resume(self):
        sched = [2] * 5
        state = bks_ckpt(ITEMS, WEIGHTS, sched, EX, seed=19, start=1)
        rounds, _ = bks_resume_idx(ITEMS, WEIGHTS, sched, EX, state, 4)
        fixed_st = me_ckpt(ITEMS, WEIGHTS, 2, EX, seed=19, start=1)
        fixed_r, _ = me_resume_idx(
            ITEMS, WEIGHTS, 2, EX, fixed_st, 4
        )
        self.assertEqual(rounds, fixed_r)

    def test_zero_k_rounds_advance_position_without_rng(self):
        sched = [0, 0, 2, 0]
        full = bks_idx(ITEMS, WEIGHTS, sched, EX, 4, seed=3)
        state = bks_ckpt(ITEMS, WEIGHTS, sched, EX, seed=3, start=2)
        rounds, st = bks_resume_idx(ITEMS, WEIGHTS, sched, EX, state, 2)
        self.assertEqual(rounds, full[2:])
        self.assertEqual(st["position"], 4)
        # 零样本轮推进位置但 RNG 只被第 3 轮(j=2, k=2)消耗一次
        state0 = bks_ckpt(ITEMS, WEIGHTS, sched, EX, seed=3)
        r, st2 = bks_resume_idx(ITEMS, WEIGHTS, sched, EX, state0, 3)
        self.assertEqual(r, full[:3])
        self.assertEqual(st2["position"], 3)

    def test_state_tampering_rejected(self):
        state = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13)
        # 非映射
        with self.assertRaises(TypeError):
            bks_resume_idx(ITEMS, WEIGHTS, KS, EX, [("a", 1)], 1)
        # 字段缺失 / 多余
        for mutator in (
            lambda s: s.pop("rng"),
            lambda s: s.update(extra=1),
            lambda s: s.update(kind="k_schedule"),  # kind 不匹配
            lambda s: s.update(position=2),
            lambda s: s.update(excluded=[1]),
            lambda s: s.update(n=5),
            lambda s: s.update(schedule_length=5),
            lambda s: s.update(exact=not s["exact"]),
        ):
            bad = dict(state)
            mutator(bad)
            with self.assertRaises(ValueError):
                bks_resume_idx(ITEMS, WEIGHTS, KS, EX, bad, 1)
        # 其他 kind 的状态不可用
        other = ks_ckpt(ITEMS, WEIGHTS, KS, seed=13)
        with self.assertRaises(ValueError):
            bks_resume_idx(ITEMS, WEIGHTS, KS, EX, other, 1)

    def test_input_mismatch_rejected(self):
        state = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13)
        with self.assertRaises(ValueError):
            bks_resume_idx(
                list("abcdef"), WEIGHTS, KS, EX, state, 1
            )  # items 不同
        with self.assertRaises(ValueError):
            bks_resume_idx(
                ITEMS, [3, 0, 7, 2, 1, 5], KS, EX, state, 1
            )  # weights 不同
        with self.assertRaises(ValueError):
            bks_resume_idx(
                ITEMS, WEIGHTS, [2, 0, 3, 1, 0, 3], EX, state, 1
            )  # k_schedule 不同
        with self.assertRaises(ValueError):
            bks_resume_idx(
                ITEMS, WEIGHTS, KS, [0], state, 1
            )  # excluded 不同

    def test_resume_window_and_draws_errors(self):
        state = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13)
        with self.assertRaises(ValueError):
            bks_resume_idx(ITEMS, WEIGHTS, KS, EX, state, 7)
        with self.assertRaises(TypeError):
            bks_resume_idx(ITEMS, WEIGHTS, KS, EX, state, 1.0)
        with self.assertRaises(TypeError):
            bks_resume_idx(ITEMS, WEIGHTS, KS, EX, state, True)
        with self.assertRaises(ValueError):
            bks_resume_idx(ITEMS, WEIGHTS, KS, EX, state, -1)

    def test_checkpoint_start_at_end(self):
        state = bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13, start=6)
        self.assertEqual(state["position"], 6)
        rounds, st = bks_resume_idx(ITEMS, WEIGHTS, KS, EX, state, 0)
        self.assertEqual(rounds, [])
        with self.assertRaises(ValueError):
            bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=13, start=7)


class ValidationOrder(unittest.TestCase):
    """校验顺序: items、weights、seed、k_schedule、excluded、draws、start,
    再做窗口与排除后可行性检查。"""

    def test_type_errors_in_order(self):
        good = dict(
            items=ITEMS, weights=WEIGHTS, k_schedule=KS, excluded=EX,
            draws=2, seed=0, start=0,
        )

        def expect_error(order_index, **over):
            kw = dict(good)
            kw.update(over)
            return kw

        # items 最先
        with self.assertRaises(TypeError):
            bks_idx(items="abc", weights=WEIGHTS, k_schedule=KS, excluded=EX,
                    draws=2, seed=0, start=0)
        # weights
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, "abc", KS, EX, 2, 0, 0)
        # seed
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, KS, EX, 2, object(), 0)
        # k_schedule 结构
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, "abc", EX, 2, 0, 0)
        # k_schedule 成员
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, [1, 1.0], EX, 2, 0, 0)
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, [1, True], EX, 2, 0, 0)
        # excluded 结构 / 成员
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, KS, "abc", 2, 0, 0)
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, KS, [1.0], 2, 0, 0)
        # draws / start
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, KS, EX, 1.0, 0, 0)
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, WEIGHTS, KS, EX, 2, 0, 1.0)

    def test_value_errors(self):
        # 权重长度不符 ValueError; 权重元素类型错误是 TypeError
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS + [1], KS, EX, 2, 0, 0)
        with self.assertRaises(TypeError):
            bks_idx(ITEMS, [3, "s", 7, 2, 1, 4], KS, EX, 2, 0, 0)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, [3, -1, 7, 2, 1, 4], KS, EX, 2, 0, 0)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, [3, float("nan"), 7, 2, 1, 4], KS, EX, 2, 0, 0)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, [3, float("inf"), 7, 2, 1, 4], KS, EX, 2, 0, 0)
        # 计划成员越界
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, [7], EX, 1, 0, 0)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, [-1], EX, 1, 0, 0)
        # excluded 越界
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, KS, [6], 1, 0, 0)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, KS, [-1], 1, 0, 0)
        # 窗口越界
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, KS, EX, 7, 0, 0)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, KS, EX, 4, 0, 3)
        with self.assertRaises(ValueError):
            bks_ckpt(ITEMS, WEIGHTS, KS, EX, seed=0, start=7)
        # 排除后正权重不足: weights 有 4 个正权重位置 0,2,3,5;
        # 再排除 0 -> 只剩 3 个
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, [4], [0, 1, 4], 1, 0, 0)
        # 但 draws=0 仍做可行性检查(全计划检查)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, [4], [0, 1, 4], 0, 0, 0)
        # start 窗口内不可行也拒绝(全计划检查)
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, [2, 4], [0, 1, 4], 1, 0, 0)

    def test_draws_zero_full_validation(self):
        # draws=0 返回空 / 全零, 但结构、窗口 start<=len
        self.assertEqual(bks_idx(ITEMS, WEIGHTS, KS, EX, 0, seed=0), [])
        self.assertEqual(bks_counts(ITEMS, WEIGHTS, KS, EX, 0, seed=0),
                         [0] * 6)
        self.assertEqual(
            list(bks_stream_idx(ITEMS, WEIGHTS, KS, EX, 0, seed=0)), []
        )
        # start 越过计划长度即使 draws=0 也拒绝
        with self.assertRaises(ValueError):
            bks_idx(ITEMS, WEIGHTS, KS, EX, 0, 0, 7)

    def test_no_input_mutation(self):
        items = copy.deepcopy(ITEMS)
        weights = copy.deepcopy(WEIGHTS)
        ks = copy.deepcopy(KS)
        excluded = [4, 1, 1, 4]
        excl_copy = list(excluded)
        bks_idx(items, weights, ks, excluded, 4, seed=5, start=2)
        bks_counts(items, weights, ks, excluded, 4, seed=5, start=2)
        list(bks_stream_idx(items, weights, ks, excluded, 4, seed=5, start=2))
        st = bks_ckpt(items, weights, ks, excluded, seed=5, start=2)
        bks_resume_idx(items, weights, ks, excluded, st, 4)
        bks_resume(items, weights, ks, excluded, st, 2)
        self.assertEqual(items, ITEMS)
        self.assertEqual(weights, WEIGHTS)
        self.assertEqual(ks, KS)
        self.assertEqual(excluded, excl_copy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
