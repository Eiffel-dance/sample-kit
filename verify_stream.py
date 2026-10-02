#!/usr/bin/env python3
"""新增流式入口 weighted_sample_stream(_indices) 的独立校验。"""

import collections.abc
import math
import sys
from decimal import Decimal
from fractions import Fraction

import app

_FAILURES = []


def check(condition, label):
    if condition:
        print("  PASS:", label)
    else:
        print("  FAIL:", label)
        _FAILURES.append(label)


def raises(exc, fn, label):
    try:
        fn()
    except exc:
        print("  PASS:", label)
        return
    except Exception as e:  # noqa
        print("  FAIL:", label, "-> 得到", type(e).__name__)
    else:
        print("  FAIL:", label, "-> 未抛异常")
    _FAILURES.append(label)


# ---------------------------------------------------------------------------
# 1. 与批量/单轮入口完全一致: 各种权重类型与抽样路径
# ---------------------------------------------------------------------------
print("== 流式结果与批量入口逐项一致(含两种抽样路径)")

HUGE = 10 ** 100
CASES = [
    # (items, weights, k, draws, seed)
    (list("abcdef"), [1, 3, 2, 5, 0, 4], 4, 7, 42),            # 小整数浮点路径
    (list("abcdef"), [1, 3, 2, 5, 0, 4], 4, 7, 0),
    (list("abc"), [0.5, 1.5, 0.25], 2, 5, 9),                  # 纯 float 路径
    (["a", "b", "c", "d"], [HUGE, HUGE * 3, 0, 1], 3, 6, 11),  # 大整数精确路径
    (list(range(6)), [10 ** 80 + i for i in range(6)], 5, 4, -3),
    (["p", "q", "r"], [2, Fraction(1), 0.5], 3, 4, 42),        # Fraction 混合
    (["a", "b", "c", "d"],
     [Decimal("1.5"), 1, Fraction(1, 2), 0.25], 3, 6, 123),    # Decimal 混合
    (["a", "b"], [10 ** 400, 10 ** 400], 2, 3, 2026),          # float() 溢出
    (["x", "y"], [9, Fraction(1, 100)], 1, 5, 2316),           # 极小 Fraction
    (["x", "y"], [HUGE, Decimal("1E-100")], 2, 3, 5),          # 极小 Decimal
    ([], [], 0, 3, 0),
    (["only"], [HUGE], 1, 1, 0),
    (list("abcd"), [1, 0, 0, 2], 2, 10, 7),
]

ok = True
for items, weights, k, draws, seed in CASES:
    si = app.weighted_sample_stream_indices(items, weights, k, draws, seed)
    sv = app.weighted_sample_stream(items, weights, k, draws, seed)
    mi = app.weighted_sample_many_indices(items, weights, k, draws, seed)
    mv = app.weighted_sample_many(items, weights, k, draws, seed)
    got_i = list(si)
    got_v = list(sv)
    if got_i != mi or got_v != mv:
        ok = False
        print("    MISMATCH:", items, weights, k, draws, seed)
    # values 与 indices 逐轮逐项对应
    if got_v != [[items[i] for i in r] for r in got_i]:
        ok = False
    # 第一轮等于单轮入口
    if draws > 0 and got_i[0] != app.weighted_sample_indices(items, weights, k, seed):
        ok = False
    if draws > 0 and got_v[0] != app.weighted_sample(items, weights, k, seed):
        ok = False
    # 结构: 轮数、轮内无重复且索引合法
    if len(got_i) != draws or any(len(set(r)) != len(r) for r in got_i):
        ok = False
    if any(any(i < 0 or i >= len(items) for i in r) for r in got_i):
        ok = False
check(ok, "所有用例: 流式 == 批量, 第一轮 == 单轮, values<->indices 对应, 结构合法")

# ---------------------------------------------------------------------------
# 2. 返回类型: 可迭代对象/迭代器, 可重复独立迭代
# ---------------------------------------------------------------------------
print("== 返回可迭代对象, 多次调用相互独立且结果一致")

s1 = app.weighted_sample_stream_indices(list("abc"), [1, 2, 3], 2, 4, 42)
check(isinstance(s1, collections.abc.Iterator), "索引流返回迭代器")
s2 = app.weighted_sample_stream(list("abc"), [1, 2, 3], 2, 4, 42)
check(isinstance(s2, collections.abc.Iterator), "值流返回迭代器")
check(
    list(app.weighted_sample_stream_indices(list("abc"), [1, 2, 3], 2, 4, 42))
    == list(app.weighted_sample_stream_indices(list("abc"), [1, 2, 3], 2, 4, 42)),
    "两次独立调用得到相同序列(各自重新初始化随机流)",
)

# ---------------------------------------------------------------------------
# 3. 逐轮惰性: 部分消费的前缀等于批量前缀, 之后可继续
# ---------------------------------------------------------------------------
print("== 按需逐轮消费")

items, weights, k, draws, seed = list("abcdef"), [1, 3, 2, 5, 0, 4], 4, 8, 42
stream = app.weighted_sample_stream_indices(items, weights, k, draws, seed)
first = next(stream)
batch = app.weighted_sample_many_indices(items, weights, k, draws, seed)
check(first == batch[0], "首个 next() 等于批量第一轮")
second = next(stream)
check(second == batch[1], "第二个 next() 等于批量第二轮")
rest = list(stream)
check(rest == batch[2:], "继续消费得到批量剩余轮次")
check(list(app.weighted_sample_stream_indices(items, weights, k, draws, seed)) == batch,
      "完整迭代仍等于批量全部轮次")

# 值流同样逐轮惰性
vs = app.weighted_sample_stream(items, weights, k, 3, seed)
check(next(vs) == [items[i] for i in batch[0]], "值流首个 next() 与索引流对应")
check(list(vs) == [[items[i] for i in r] for r in batch[1:3]], "值流继续消费正确")

# 迭代器一次性: 耗尽后再 next 抛 StopIteration
done = app.weighted_sample_stream_indices(items, weights, 1, 2, 0)
list(done)
try:
    next(done)
    check(False, "耗尽后 next() 应抛 StopIteration")
except StopIteration:
    check(True, "耗尽后 next() 抛 StopIteration")

# ---------------------------------------------------------------------------
# 4. 校验在调用时(产出第一轮之前)同步完成
# ---------------------------------------------------------------------------
print("== 调用时 eager 校验, 不延迟到消费后")

def assert_raises_at_call(fn_factory, label):
    # 关键: 异常必须在“调用入口”时抛出, 而不是 next() 时。
    try:
        obj = fn_factory()
    except Exception as e:  # noqa
        print("  PASS:", label, "->", type(e).__name__)
        return
    try:
        next(iter(obj))
    except Exception as e:  # noqa
        print("  FAIL:", label, "-> 异常被延迟到消费时:", type(e).__name__)
        _FAILURES.append(label)
        return
    print("  FAIL:", label, "-> 未抛异常")
    _FAILURES.append(label)


# TypeError 类
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices("abc", [1, 2, 3], 1, 2, 0),
    "items 为文本 -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a", "b"], (x for x in [1, 2]), 1, 2, 0),
    "weights 为无长度生成器 -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], True, 2, 0),
    "k 为布尔 -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], 1, True, 0),
    "draws 为布尔 -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], 1, 2.0, 0),
    "draws 为 float -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], 1.5, 2, 0),
    "k 为 float -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], 1, 2, object()),
    "非法 seed -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a", "b"], [1, "1"], 1, 2, 0),
    "非实数权重 -> 调用时 TypeError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a", "b"], [1, True], 1, 2, 0),
    "布尔权重 -> 调用时 TypeError")

# ValueError 类
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1, 2], 1, 2, 0),
    "长度不一致 -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], 2, 2, 0),
    "k 超界 -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], 1, -1, 0),
    "draws 为负 -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [1], -1, 2, 0),
    "k 为负 -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [-1], 1, 2, 0),
    "负权重 -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [float("nan")], 1, 2, 0),
    "NaN 权重 -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [float("inf")], 1, 2, 0),
    "无穷权重 -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a"], [Decimal("NaN")], 1, 2, 0),
    "Decimal NaN -> 调用时 ValueError")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a", "b"], [1, 0], 2, 5, 0),
    "k 大于正权重个数 -> 调用时 ValueError(即使 draws 很多)")
assert_raises_at_call(
    lambda: app.weighted_sample_stream_indices(["a", "b"], [0, 0], 1, 1, 0),
    "k>0 且无有效正权重 -> 调用时 ValueError")

# 异常类型与批量入口保持一致
def same_exception_as_many(label, *args):
    stream_exc = many_exc = None
    try:
        app.weighted_sample_stream_indices(*args)
    except Exception as e:  # noqa
        stream_exc = type(e)
    try:
        app.weighted_sample_many_indices(*args)
    except Exception as e:  # noqa
        many_exc = type(e)
    check(stream_exc is many_exc and stream_exc is not None,
          "%s: 流式与批量同为 %s" % (label, many_exc.__name__ if many_exc else None))


same_exception_as_many("文本 items", "abc", [1, 2, 3], 1, 2, 0)
same_exception_as_many("bool k", ["a"], [1], True, 2, 0)
same_exception_as_many("bool draws", ["a"], [1], 1, False, 0)
same_exception_as_many("长度不一致", ["a"], [1, 2], 1, 2, 0)
same_exception_as_many("NaN", ["a"], [float("nan")], 1, 2, 0)
same_exception_as_many("正权重不足", ["a", "b"], [1, 0], 2, 9, 0)

# ---------------------------------------------------------------------------
# 5. draws=0: 完成全部校验并返回不产出元素的可迭代对象
# ---------------------------------------------------------------------------
print("== draws=0 / k=0")

empty = app.weighted_sample_stream_indices(["a", "b"], [1, 2], 2, 0, 0)
check(list(empty) == [], "draws=0 合法输入 -> 不产出元素的可迭代对象")
check(
    list(app.weighted_sample_stream_indices(["a", "b"], [1, 2], 2, 0, 0))
    == app.weighted_sample_many_indices(["a", "b"], [1, 2], 2, 0, 0),
    "draws=0 与批量入口结果一致([])",
)
check(
    list(app.weighted_sample_stream(["a", "b"], [1, 2], 2, 0, 0)) == [],
    "值流 draws=0 也为空",
)
# draws=0 仍须完成全部校验
raises(ValueError,
       lambda: app.weighted_sample_stream_indices(["a"], [float("nan")], 0, 0, 0),
       "draws=0 仍先校验权重 (NaN -> ValueError)")
raises(ValueError,
       lambda: app.weighted_sample_stream_indices(["a"], [1, 2], 0, 0, 0),
       "draws=0 仍校验长度一致")
raises(TypeError,
       lambda: app.weighted_sample_stream_indices(["a"], [1], 0, 0, object()),
       "draws=0 仍校验 seed 类型")
raises(TypeError,
       lambda: app.weighted_sample_stream_indices(["a"], [1], "0", 0, 0),
       "draws=0 仍校验 k 类型")
# k=0: 每轮产出空列表(即使权重全零), draws>0
z = list(app.weighted_sample_stream_indices(["a", "b"], [0, 0], 0, 4, 0))
check(z == [[], [], [], []], "k=0 -> 每轮空列表(全零权重也合法)")
zv = list(app.weighted_sample_stream(["a", "b"], [0, 0], 0, 2, 0))
check(zv == [[], []], "值流 k=0 -> 每轮空列表")
z00 = list(app.weighted_sample_stream_indices(["a"], [0], 0, 0, 0))
check(z00 == [], "k=0 且 draws=0 -> []")

# ---------------------------------------------------------------------------
# 6. 入参不被修改
# ---------------------------------------------------------------------------
print("== 入参不变")

for items, weights, k, draws, seed in CASES:
    snap_i, snap_w = list(items), list(weights)
    # 只消费部分轮次, 也不能改动入参
    it = app.weighted_sample_stream_indices(items, weights, k, draws, seed)
    for j, _ in enumerate(it):
        if j >= 1:
            break
    vt = app.weighted_sample_stream(items, weights, k, draws, seed)
    for j, _ in enumerate(vt):
        if j >= 1:
            break
    if items != snap_i or weights != snap_w:
        check(False, "入参被修改: %r %r" % (items, weights))
        break
else:
    check(True, "全部用例(含部分消费): items / weights 原样保留")

# ---------------------------------------------------------------------------
# 7. 支持的权重类型与确定性路径全覆盖
# ---------------------------------------------------------------------------
print("== int/float/Fraction/Decimal 及极端权重")

type_cases = [
    ([1, 2, 3], int),
    ([0.25, 0.75, 0.0], float),
    ([Fraction(1, 3), Fraction(2, 3), Fraction(0)], "Fraction"),
    ([Decimal("0.1"), Decimal("0.2"), Decimal("0")], "Decimal"),
    ([1, Fraction(1, 7), 0.5, Decimal("0.25")], "mixed"),
    ([10 ** 5000, 1], "huge-int"),
    ([1, Fraction(1, 10 ** 5000)], "tiny-fraction"),
    ([1, Decimal("1E-100000")], "tiny-decimal"),
    ([Decimal("1E100000"), Decimal("1E-100000")], "extreme-decimal"),
]
tok = True
for ws, name in type_cases:
    its = ["w%d" % i for i in range(len(ws))]
    # k 不超过正权重位置数(含零权重的用例无法抽满 len(ws))。
    positive = sum(1 for w in ws if w > 0)
    k = min(len(ws), positive) if positive else 0
    si = list(app.weighted_sample_stream_indices(its, ws, k, 5, 7))
    mi = app.weighted_sample_many_indices(its, ws, k, 5, 7)
    sv = list(app.weighted_sample_stream(its, ws, k, 5, 7))
    mv = app.weighted_sample_many(its, ws, k, 5, 7)
    if si != mi or sv != mv:
        tok = False
        print("    MISMATCH:", name)
    # 确定性
    if list(app.weighted_sample_stream_indices(its, ws, k, 5, 7)) != si:
        tok = False
check(tok, "所有权重类型/极端值: 流式 == 批量且确定可复现")

# seed 类型覆盖(与现有语义一致)
sok = True
for seed in (0, 1, 42, -5, 1.5, "seed", b"seed", bytearray(b"seed"), True):
    its, ws = list("abc"), [1, 3, 2]
    if list(app.weighted_sample_stream_indices(its, ws, 2, 3, seed)) \
            != app.weighted_sample_many_indices(its, ws, 2, 3, seed):
        sok = False
check(sok, "int/float/str/bytes/bytearray/bool seed 下流式 == 批量")

# seed=None 可用(随机语义), 轮数与结构正确
none_res = list(app.weighted_sample_stream_indices(list("abcd"), [1, 2, 3, 4], 2, 3, None))
check(len(none_res) == 3 and all(len(r) == 2 for r in none_res),
      "seed=None 可正常逐轮产出")

# ---------------------------------------------------------------------------
# 8. 轮间位置可重复出现, 轮内不重复
# ---------------------------------------------------------------------------
print("== 轮间重启语义")

rounds = list(app.weighted_sample_stream_indices(
    ["a", "b"], [Decimal("1"), Decimal("1")], 1, 20, 0))
check(len(rounds) == 20 and all(r == [0] or r == [1] for r in rounds),
      "20 轮均为合法单位置")
check(rounds == app.weighted_sample_many_indices(
    ["a", "b"], [Decimal("1"), Decimal("1")], 1, 20, 0),
    "与批量入口逐轮一致")

# 每轮都从原始位置重新开始: k=n 时每轮都是全部位置的一个排列
full = list(app.weighted_sample_stream_indices(list("abcd"), [1, 2, 3, 4], 4, 8, 3))
check(all(sorted(r) == [0, 1, 2, 3] for r in full),
      "k=n: 每轮都是全部原始位置的排列(轮间互不影响)")

# ---------------------------------------------------------------------------
print()
if _FAILURES:
    print("结果: %d 项失败" % len(_FAILURES))
    for f in _FAILURES:
        print("  -", f)
    sys.exit(1)
print("结果: 全部校验通过")
