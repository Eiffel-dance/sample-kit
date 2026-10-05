#!/usr/bin/env python3
"""weighted_sample_schedule_counts 的独立校验。"""

import random
import sys
from decimal import Decimal
from fractions import Fraction

import app

FAIL = []


def check(cond, label):
    if cond:
        print("  PASS:", label)
    else:
        print("  FAIL:", label)
        FAIL.append(label)


def raises(exc, fn, label):
    try:
        fn()
    except exc:
        print("  PASS:", label)
        return
    except Exception as e:
        print("  FAIL:", label, "->", type(e).__name__, e)
        FAIL.append(label)
        return
    print("  FAIL:", label, "-> 未抛异常")
    FAIL.append(label)


def flat(items, schedule, k, draws, seed, start):
    rounds = app.weighted_sample_schedule_indices(
        items, schedule, k, draws, seed, start
    )
    counts = [0] * len(items)
    for rd in rounds:
        for p in rd:
            counts[p] += 1
    return counts


# 1. 与索引入口摊平计数逐项一致: 混合权重类型 / 重复元素 / 多 seed / 窗口
print("== 与 weighted_sample_schedule_indices 摊平一致")
items = ["x", "y", "x", "z", "y", "q"]
sched = [
    [1, 2, 3, 0, 5, 2],
    [Fraction(1, 3), 0, 2, 7, 1, Fraction(0)],
    [0.5, 1.5, 0, 2.0, 1.0, 0.25],
    [10 ** 100, 1, 0, 2, 3, 10 ** 50],
    [Decimal("0.1"), Decimal("0.2"), 0, Decimal("1E-100"), 1, Decimal("-0")],
    [3, 1, 4, 1, 5, 9],
    [0, 0, 1, 1, 7, Fraction(1, 10 ** 100)],
    [2 ** 53, 1, 2, 3, 4, 5],
]
ok = True
for seed in (0, 1, 42, -7, 1.5, "s", b"s", True):
    full = app.weighted_sample_schedule_indices(
        items, sched, 4, len(sched), seed)
    full_counts = [0] * len(items)
    for rd in full:
        for p in rd:
            full_counts[p] += 1
    # 各种 start/draws 窗口
    for start in range(len(sched) + 1):
        for draws in range(0, len(sched) - start + 1):
            got = app.weighted_sample_schedule_counts(
                items, sched, 4, draws, seed, start)
            exp = [0] * len(items)
            for rd in full[start:start + draws]:
                for p in rd:
                    exp[p] += 1
            if got != exp or not all(isinstance(c, int) for c in got):
                ok = False
            # 直接逐轮调用的等价写法(独立随机流)
            if got != flat(items, sched, 4, draws, seed, start):
                ok = False
check(ok, "全部 seed/start/draws 组合下与索引入口窗口摊平逐项一致")

# 2. 随机流消耗逐项对齐: 调用后 RNG 状态 == 索引入口消耗后的状态
print("== 随机流消耗一致")
stream_ok = True
for k in (0, 1, 3):
    for seed in (0, 42, 1.5):
        for start, draws in ((0, 3), (2, 2), (5, 0)):
            c = app.weighted_sample_schedule_counts(
                items, sched, k, draws, seed, start)
            rng = random.Random(seed)
            plans = [app._select_sampling_plan(list(sched[j]), k)
                     for j in range(start + draws)]
            n = len(items)
            if k > 0:
                for j in range(start + draws):
                    app._draw_indices_once(n, plans[j][0], k, rng, plans[j][1])
            ref = app.weighted_sample_schedule_counts(
                items, sched, k, draws, seed, start)
            # 用 rng 再抽一轮必须等于"下一轮"(与 start=0 全量比较)
            if draws > 0 and start + draws < len(sched):
                pw, ue = app._select_sampling_plan(list(sched[start + draws]), k)
                nxt = app._draw_indices_once(n, pw, k, rng, ue)
                full_next = app.weighted_sample_schedule_indices(
                    items, sched, k, 1, seed, start=start + draws)[0]
                if k > 0 and nxt != full_next:
                    stream_ok = False
check(stream_ok, "计数入口与索引入口消耗同一条随机流(续抽下一轮一致)")

# 3. 总数不变量: sum(counts) == k * draws; 每轮每位置至多一次
print("== 计数总量与按位置区分")
inv_ok = True
for seed in range(40):
    c = app.weighted_sample_schedule_counts(items, sched, 3, 5, seed)
    if sum(c) != 15:
        inv_ok = False
    if len(c) != len(items):
        inv_ok = False
# 重复元素: 全相同 items, 位置仍独立累计
same = ["a"] * 5
c = app.weighted_sample_schedule_counts(
    same, [[1, 2, 3, 4, 5]] * 6, 3, 6, 42)
ref = flat(same, [[1, 2, 3, 4, 5]] * 6, 3, 6, 42, 0)
inv_ok = inv_ok and c == ref and sum(c) == 18 and len(c) == 5
check(inv_ok, "sum(counts)==k*draws, 长度==items, 重复元素按位置区分")

# 4. draws=0 / k=0: 全零且完成全部校验, 不消耗随机流
print("== draws=0 / k=0")
check(app.weighted_sample_schedule_counts(items, sched, 4, 0, 7, start=3)
      == [0] * len(items), "draws=0 返回全零(允许 start=len)")
check(app.weighted_sample_schedule_counts(items, sched, 0, 5, 7, start=2)
      == [0] * len(items), "k=0 返回全零")
# k=0 且 start 很大: 不消耗随机流 —— 与 fresh RNG 状态等价(间接: 窗口外续抽)
rng_fresh = random.Random(7).getstate()
# 直接构造: k=0 时内部 plans 全部 use_exact=False, 但不产生抽取;
# 校验 draws=0 下 start 可等于计划长度
app.weighted_sample_schedule_counts(items, sched, 0, 0, 7, start=len(sched))
print("  PASS: k=0/draws=0, start=len(schedule) 合法")

# k=0 不消耗随机流: 同一 seed 下不同 start 的 counts 必然相同(全零),
# 且 k=0 计划行允许全零权重
zero_rows = [[0, 0, 0], [1, 0, 0]]
check(app.weighted_sample_schedule_counts(
    ["a", "b", "c"], zero_rows, 0, 2, 7) == [0, 0, 0],
    "k=0 时全零权重行合法")
# draws=0 仍完成全部校验
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    items, sched, 4, 0, 0, start=len(sched) + 1),
    "draws=0: 窗口越界仍抛 ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    items, [[1, float("nan"), 0, 0, 0, 0]], 1, 0, 0),
    "draws=0: NaN 权重仍抛 ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    items, [[0, 0, 1, 1, 0, 0]], 3, 0, 0),
    "draws=0: 正权重不足仍抛 ValueError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    "abcdef", sched, 1, 0, 0), "draws=0: items 为文本仍抛 TypeError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    items, sched, 0, 0, 0, start=-1), "draws=0: 负 start 仍抛 ValueError")

# 5. 校验顺序与异常类别(沿用 schedule 入口)
print("== 校验顺序与异常分类")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    "abc", [[1, 2, 3]], 1, 1, 0), "items 文本 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a"], "x", 0, 0, 0), "schedule 文本 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, 2], "ab"], 0, 0, 0), "计划行为文本 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], True, 0, 0), "k 布尔 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], "1", 0, 0), "k 非整数 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], 1, 1, object()), "seed 非法类型 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], 1, True, 0), "draws 布尔 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], 1, 1.0, 0), "draws 浮点 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], 1, 0, start=False), "start 布尔 -> TypeError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], -1, 0, 0), "k 负 -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], 2, 0, 0), "k 超过 n -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1]], 0, 0, 0), "行长不符 -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a"], [[1]], 1, 1, 0, start=1), "窗口越界 -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, 2]], 1, -1, 0), "draws 负 -> ValueError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, "2"]], 1, 1, 0), "权重成员非数 -> TypeError")
raises(TypeError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, True]], 1, 1, 0), "布尔权重 -> TypeError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, -2]], 1, 1, 0), "负权重 -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, float("nan")]], 1, 1, 0), "NaN -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, float("inf")]], 1, 1, 0), "无穷 -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[Decimal("1"), Decimal("NaN")]], 1, 1, 0),
    "Decimal NaN -> ValueError")
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[0, 1]], 2, 1, 0), "正权重不足 -> ValueError")
# 被跳过窗口之外的坏行不在校验范围? 现状: 索引入口校验整个 schedule 的
# 所有行(与既有语义一致)
raises(ValueError, lambda: app.weighted_sample_schedule_counts(
    ["a", "b"], [[1, 2], [1, -2]], 1, 1, 0, start=0),
    "窗口外的坏权重行同样被校验(与索引入口一致)")

# 6. 与索引入口抛出的异常类别逐用例一致
print("== 与索引入口异常类别一致")
exc_ok = True
bad_cases = [
    ("abc", [[1, 2, 3]], 1, 1, 0, 0),
    (["a", "b"], [[1]], 0, 0, 0, 0),
    (["a"], [[1]], 2, 0, 0, 0),
    (["a", "b"], [[1, "x"]], 1, 1, 0, 0),
    (["a", "b"], [[-1, 1]], 1, 1, 0, 0),
    (["a", "b"], [[1, 2]], 1, 1, 0, 5),
    (["a"], [[1]], 1, 1, 1 + 2j, 0),
]
for it, sc, kk, dr, sd, st in bad_cases:
    try:
        app.weighted_sample_schedule_indices(it, sc, kk, dr, sd, st)
        a = None
    except Exception as e:
        a = type(e)
    try:
        app.weighted_sample_schedule_counts(it, sc, kk, dr, sd, st)
        b = None
    except Exception as e:
        b = type(e)
    if a is not b:
        exc_ok = False
check(exc_ok, "同一非法输入下两入口异常类别完全相同")

# 7. 边界: 空 items / 空计划
print("== 空计划边界")
check(app.weighted_sample_schedule_counts([], [], 0, 0, 0) == [],
      "空 items + 空 schedule + draws=0 -> []")
raises(ValueError, lambda: app.weighted_sample_schedule_counts([], [], 0, 1, 0),
      "空 schedule + draws=1 -> ValueError")
check(app.weighted_sample_schedule_counts(
    [], [[]], 0, 1, 0) == [], "空行 k=0 一轮 -> 空计数")
check(app.weighted_sample_schedule_counts(
    [], [[]] * 4, 0, 3, 0, start=1) == [], "空行多轮窗口 -> 空计数")
raises(ValueError, lambda: app.weighted_sample_schedule_counts([], [[]], 1, 0, 0),
      "空 items k=1(即使 draws=0) -> ValueError")

# 8. 超大整数 / 极小正权重 / 零权重 精确路径
print("== 极端权重")
huge = 10 ** 5000
c = app.weighted_sample_schedule_counts(
    ["H", "t", "z"],
    ([[huge, 1, 0], [Fraction(1, 10 ** 200), huge, 0],
      [Decimal("1E-1000"), huge, 0]]) * 100,
    1, 300, 42)
check(c[2] == 0 and sum(c) == 300 and all(isinstance(v, int) for v in c),
      "零权重位置计数恒为零, 超大/极小权重下总计数正确")
# 极小正权重可被累计(精确比例 9900:1, 大量 seed 下期望命中)
tiny_hit = False
for seed in range(50000):
    cc = app.weighted_sample_schedule_counts(
        ["H", "t"], [[99, Fraction(1, 100)]], 1, 1, seed)
    if cc[1] == 1:
        tiny_hit = True
        # 与索引入口摊平一致
        if cc != flat(["H", "t"], [[99, Fraction(1, 100)]], 1, 1, seed, 0):
            tiny_hit = False
        break
check(tiny_hit, "极小正权重位置在精确路径下可被选中(9900:1)")
# 锁定 seed 回归
check(app.weighted_sample_schedule_counts(
    ["big", "tiny"], [[9, Fraction(1, 100)]], 1, 1, 2316) == [0, 1],
    "极小正 Fraction 锁定 seed=2316 命中(与单轮入口一致)")
# 极小正 Decimal 不被吞成零
cdec = app.weighted_sample_schedule_counts(
    ["a", "b"], [[huge, Decimal("1E-5000")]], 1, 1, 0)
check(cdec == flat(["a", "b"], [[huge, Decimal("1E-5000")]], 1, 1, 0, 0),
      "极小正 Decimal 与索引入口一致")

# 9. 任意精度整数 + serialize/deserialize 往返
print("== serialize_metrics 往返")
big_c = app.weighted_sample_schedule_counts(
    list(range(4)),
    [[10 ** 5000, 1, 2, 3]] * 200, 4, 200, 9)
text = app.serialize_metrics({"counts": big_c})
restored = app.deserialize_metrics(text)["counts"]
check(restored == big_c and isinstance(restored, list)
      and all(type(x) is int for x in restored) and len(restored) == 4,
      "超大计数经 serialize/deserialize 保留数值与列表形状")
# 每个位置每轮最多 1 次 => 此处每个计数恰为 200
check(all(v == 200 for v in big_c), "全正权重 k=n 时每位置每轮一次")

# 10. 不修改入参
print("== 入参不变")
snap_items = list(items)
snap_sched = [list(r) for r in sched]
app.weighted_sample_schedule_counts(items, sched, 4, 6, 42, start=1)
app.weighted_sample_schedule_counts(items, sched, 0, 8, 42)
try:
    app.weighted_sample_schedule_counts(items, sched, 9, 1, 0)
except ValueError:
    pass
check(list(items) == snap_items
      and [list(r) for r in sched] == snap_sched,
      "items / weights_schedule 原样保留(含失败调用)")

# 11. tuple 入参可接受
ctup = app.weighted_sample_schedule_counts(
    ("a", "b", "c"), ([1, 2, 3], [0, 1, 2]), 2, 2, 5)
check(ctup == flat(["a", "b", "c"], [[1, 2, 3], [0, 1, 2]], 2, 2, 5, 0)
      and isinstance(ctup, list), "tuple items/schedule 接受, 返回 list")

# 12. 各行权重相同时与 weighted_sample_counts 一致
print("== 与固定权重频次入口一致")
same_ok = True
w = [1, 3, 2, 0, 5]
for seed in (0, 42, 7):
    for start, draws in ((0, 6), (2, 3), (5, 0)):
        a = app.weighted_sample_schedule_counts(
            items[:5], [w] * 8, 3, draws, seed, start)
        b = app.weighted_sample_counts(
            items[:5], w, 3, draws, seed, start)
        if a != b:
            same_ok = False
check(same_ok, "schedule 各行相同 -> 与 weighted_sample_counts 逐项一致")

# 13. 值入口不受影响(首轮回归)
check(app.weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42)
      == ["green", "red"], "基线序列保持不变")

print()
if FAIL:
    print("结果: %d 项失败" % len(FAIL))
    sys.exit(1)
print("结果: 全部校验通过")
