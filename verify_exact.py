#!/usr/bin/env python3
"""精确加权无放回采样的独立校验脚本。

不依赖测试框架, 直接针对 app 公开入口验证:
  1. 索引在范围内、无重复、数量正确;
  2. weighted_sample 的 values 与 weighted_sample_indices 逐项对应;
  3. 10**100 级别权重、极端比例、多轮抽取均确定且按精确整数比例;
  4. 零权重永不选中; 微小正权重不被浮点吞掉;
  5. 相同 (输入, seed) 给出唯一相同序列;
  6. 异常仍按既有 TypeError / ValueError 分类; 入参不被修改;
  7. 小整数(累计 <= 2**53)保持基线浮点路径的固定序列;
  8. deserialize_metrics 精确还原序列化文本(任意精度 int / Decimal,
     重复成员名与非有限值拒绝), 并可消费 checkpoint 状态文本恢复采样。

用法:  python3 verify_exact.py   (全部通过时退出码为 0)
"""

import math
import random
import sys
from fractions import Fraction

import app

_FAILURES = []


def check(condition, label):
    if condition:
        print("  PASS:", label)
    else:
        print("  FAIL:", label)
        _FAILURES.append(label)


def section(title):
    print()
    print("== %s" % title)


# ---------------------------------------------------------------------------
# 1. 结构不变量: 范围内 / 无重复 / 数量 / 两个入口逐项对应
# ---------------------------------------------------------------------------
section("结构不变量与 values<->indices 对应")

HUGE = 10 ** 100
STRUCT_CASES = [
    (["a", "b", "c", "d"], [HUGE, HUGE * 3, 0, 1], 3),
    (list("xyz"), [10 ** 100, 1, 10 ** 50], 2),
    ([0, 0, 0, 0, 0], [HUGE, 1, 2, 0, HUGE - 5], 4),
    (["only"], [HUGE], 1),
    ([], [], 0),
    (list(range(20)), [10 ** 80 + i for i in range(20)], 10),
]

structural_ok = True
for items, weights, k in STRUCT_CASES:
    for seed in range(30):
        idx = app.weighted_sample_indices(items, weights, k, seed)
        vals = app.weighted_sample(items, weights, k, seed)
        if len(idx) != k or len(set(idx)) != k:
            structural_ok = False
        if any(not isinstance(i, int) or i < 0 or i >= len(items) for i in idx):
            structural_ok = False
        if vals != [items[i] for i in idx]:
            structural_ok = False
check(structural_ok, "全部用例: 索引在范围内、无重复、数量正确, values 与 indices 逐项对应")


# ---------------------------------------------------------------------------
# 2. 确定性: 相同 seed + 输入唯一相同
# ---------------------------------------------------------------------------
section("确定性 (相同 seed/输入 -> 唯一序列)")

det_ok = True
items, weights, k = list("abcdef"), [HUGE, 1, HUGE * 2, 7, 0, 10 ** 90], 4
# 注: seed=None 按 random.Random 语义使用系统熵, 本就不保证可复现, 不纳入。
for seed in (0, 1, 42, 123456789, -5, 1.5, "seed", b"seed", bytearray(b"seed"), True):
    first = app.weighted_sample_indices(items, weights, k, seed)
    for _ in range(6):
        if app.weighted_sample_indices(items, weights, k, seed) != first:
            det_ok = False
check(det_ok, "多种确定性 seed 类型下序列完全可复现")

# seed=None 必须可用(不报错), 但语义上是随机种子。
app.weighted_sample_indices(items, weights, k, None)
print("  PASS: seed=None 可正常工作")


# ---------------------------------------------------------------------------
# 3. 零权重永不选中; 微小正权重保持精确可选中概率
# ---------------------------------------------------------------------------
section("零权重排除与微小正权重")

zero_ok = all(
    0 not in app.weighted_sample_indices(["z", "a"], [0, HUGE], 1, seed)
    for seed in range(200)
)
check(zero_ok, "零权重位置在 200 个 seed 下从不出现")

# 精确性反证: 直接驱动精确路径, needle 取 total-1 必须落在权重为 1 的位置。
# 任何浮点舍入都会把 1 相对 10**100 吞成 0。
class _FixedRNG:
    def __init__(self, values):
        self._values = list(values)

    def getrandbits(self, bits):
        return self._values.pop(0)


tiny = app._sample_indices_exact_integer(
    [0, 1], [HUGE, 1], 1, _FixedRNG([HUGE])  # needle = total - 1
)
check(tiny == [1], "权重 1 对 10**100: needle=total-1 精确落到微小正权重位置")

zero_exact = app._sample_indices_exact_integer(
    [0, 1, 2], [HUGE, 0, 1], 1, _FixedRNG([HUGE])  # 越过位置0累计即等于 needle
)
# 累计: 位置0 后 acc=HUGE, needle=HUGE 不满足 < ; 位置1 权重0, acc 仍 HUGE;
# 位置2 权重1, acc=HUGE+1 命中 -> 零权重位置 1 被跳过。
check(zero_exact == [2], "定位遍历时零权重位置被精确跳过")


# ---------------------------------------------------------------------------
# 4. 统计比例正确 (整数权重严格按比例)
# ---------------------------------------------------------------------------
section("第一轮选中比例的统计检验")

# 取总量超过 2**53 的三权重, 比例 1:2:5, 用大量 seed 统计第一轮落点。
BASE = 2 ** 52 + 11
w3 = [BASE, 2 * BASE, 5 * BASE]
counts = [0, 0, 0]
TRIALS = 6000
for seed in range(TRIALS):
    counts[app.weighted_sample_indices(["a", "b", "c"], w3, 1, seed)[0]] += 1

expected = (1 / 8, 2 / 8, 5 / 8)
prop_ok = all(
    abs(counts[i] / TRIALS - expected[i]) < 0.025 for i in range(3)
)
print("  观测比例: %.4f %.4f %.4f (期望 %.3f %.3f %.3f)" % (
    counts[0] / TRIALS, counts[1] / TRIALS, counts[2] / TRIALS, *expected))
check(prop_ok, "三位置比例收敛到精确的 1:2:5")


# ---------------------------------------------------------------------------
# 5. 多轮抽取: 每轮只在未选中位置中, 按剩余权重抽取
# ---------------------------------------------------------------------------
section("多轮无放回抽取")

multi_ok = True
for seed in range(300):
    idx = app.weighted_sample_indices(
        list(range(6)), [HUGE, 1, HUGE * 4, 3, 0, 10 ** 60], 5, seed
    )
    if len(idx) != 5 or len(set(idx)) != 5:
        multi_ok = False
    if 4 in idx:  # 零权重
        multi_ok = False

# 脚本化两轮, 验证抽走后按剩余权重定位。
two = app._sample_indices_exact_integer(
    [0, 1, 2, 3],
    [HUGE, 10, 5, 0],
    2,
    _FixedRNG([HUGE + 10, HUGE]),  # 第一轮中位置2(权5), 第二轮中位置1(权10)
)
multi_ok = multi_ok and two == [2, 1]
check(multi_ok, "5 轮抽取无重复/排除零权重, 且抽走后按剩余权重精确定位")


# ---------------------------------------------------------------------------
# 6. 无正权重 -> ValueError (精确路径)
# ---------------------------------------------------------------------------
section("异常分类")

def raises(exc, fn, label):
    try:
        fn()
    except exc:
        print("  PASS:", label)
        return True
    except Exception as e:  # noqa
        print("  FAIL:", label, "-> 得到", type(e).__name__)
        _FAILURES.append(label)
        return False
    print("  FAIL:", label, "-> 未抛异常")
    _FAILURES.append(label)
    return False


raises(ValueError,
       lambda: app.weighted_sample_indices(["a", "b"], [HUGE, 0], 2, 0),
       "唯一正权重被抽走后继续抽取 -> ValueError")
raises(ValueError,
       lambda: app.weighted_sample_indices(["a"], [0], 1, 0),
       "全零权重 k>0 -> ValueError")
raises(TypeError,
       lambda: app.weighted_sample_indices(["a", "b"], [HUGE, "1"], 1, 0),
       "非数权重 -> TypeError")
raises(TypeError,
       lambda: app.weighted_sample_indices(["a", "b"], [HUGE, True], 1, 0),
       "布尔权重 -> TypeError")
raises(ValueError,
       lambda: app.weighted_sample_indices(["a", "b"], [HUGE, -1], 1, 0),
       "负权重 -> ValueError")
raises(ValueError,
       lambda: app.weighted_sample_indices(["a", "b"], [HUGE, float("nan")], 1, 0),
       "NaN 权重 -> ValueError")
raises(ValueError,
       lambda: app.weighted_sample_indices(["a"], [HUGE], 2, 0),
       "k 越界 -> ValueError")
raises(TypeError,
       lambda: app.weighted_sample_indices(["a"], [HUGE], 1, object()),
       "非法 seed -> TypeError")
raises(TypeError,
       lambda: app.weighted_sample_indices("ab", [HUGE, 1], 1, 0),
       "items 为文本 -> TypeError")

# k=0 先完成全部校验再返回空。
raises(ValueError,
       lambda: app.weighted_sample_indices(["a"], [float("nan")], 0, 0),
       "k=0 时仍先校验权重 (NaN -> ValueError)")
check(app.weighted_sample_indices(["a", "b"], [HUGE, 0], 0, 0) == [],
      "k=0 且输入合法 -> []")


# ---------------------------------------------------------------------------
# 7. 入参不被修改
# ---------------------------------------------------------------------------
section("入参不变")

items, weights = list("abc"), [HUGE, HUGE * 2, 1]
items_snap, weights_snap = list(items), list(weights)
app.weighted_sample(items, weights, 3, 99)
app.weighted_sample_indices(items, weights, 2, -3)
check(items == items_snap and weights == weights_snap, "items / weights 原样保留")


# ---------------------------------------------------------------------------
# 8. 阈值边界: <= 2**53 保持基线固定序列; 浮点权重走原规则
# ---------------------------------------------------------------------------
section("向后兼容")

# 锁定的基线序列。
check(
    app.weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42)
    == ["green", "red"],
    "小整数基线序列保持 (seed=42)",
)
check(
    app.weighted_sample_indices(["a", "b", "c"], [1, 3, 2], 3, 7)
    == [1, 0, 2],
    "小整数基线索引保持 (seed=7)",
)

# 累计恰为 2**53 仍走浮点路径: 与直接浮点算法逐 seed 一致。
edge = [2 ** 53 - 1, 1]
edge_ok = True
for seed in range(50):
    pool, pw = [0, 1], list(edge)
    expect = app._sample_indices_float(pool, pw, 2, random.Random(seed))
    if app.weighted_sample_indices(["a", "b"], edge, 2, seed) != expect:
        edge_ok = False
check(edge_ok, "累计 = 2**53 边界仍为基线浮点路径序列")

# 累计 2**53+1 进入精确路径, 且微小权重统计上可被选中(约 1/2**53 太小,
# 故改用脚本化 RNG 已在第3节证明; 这里仅确认不抛错且确定)。
above = app.weighted_sample_indices(["a", "b"], [2 ** 53, 1], 1, 5)
check(above == app.weighted_sample_indices(["a", "b"], [2 ** 53, 1], 1, 5),
      "累计 2**53+1 走精确路径且确定")

# 非整数(浮点)权重继续按既有规则工作。
check(
    sorted(app.weighted_sample(["p", "q"], [0.5, 1.5], 2, 3)) == ["p", "q"],
    "浮点权重仍按既有规则工作",
)

# 10**400: float() 会 OverflowError, 精确路径必须正常工作。
idx400 = app.weighted_sample_indices(
    ["a", "b"], [10 ** 400, 10 ** 400], 2, 2026
)
check(sorted(idx400) == [0, 1] and
      idx400 == app.weighted_sample_indices(["a", "b"], [10 ** 400, 10 ** 400], 2, 2026),
      "10**400 级权重(无法转有限浮点)正常、确定地抽取")


# ---------------------------------------------------------------------------
# 9. 拒绝采样均匀性自检 (total=3, bits=2, needle=3 必须被拒绝)
# ---------------------------------------------------------------------------
section("拒绝采样无偏")

class _ScriptedReject:
    def __init__(self):
        self.saw = []

    def getrandbits(self, bits):
        # 先给两次必拒值 3, 再给可接受值 2。
        v = 3 if len(self.saw) < 2 else 2
        self.saw.append(v)
        return v


rng_r = _ScriptedReject()
picked = app._sample_indices_exact_integer([0, 1, 2], [1, 1, 1], 1, rng_r)
check(picked == [2] and rng_r.saw == [3, 3, 2],
      "needle 落在拒绝区间时重抽, 接受值取模后定位正确")


# ---------------------------------------------------------------------------
# 10. Fraction 权重: 精确有理数路径, 极小正权重不被浮点吞掉
# ---------------------------------------------------------------------------
section("Fraction 权重的精确无放回抽样")

# 10.1 极小正 Fraction 通过公开入口在精确比例允许时被选中。
#   [9, 1/100] 精确放大为 [900, 1], 锁定 seed 命中微小位置; 走浮点路径时
#   该微小权重相对总和虽不致归零, 但这里走的是精确路径, 比例严格为 1/901。
tiny_public = app.weighted_sample(
    ["big", "tiny"], [9, Fraction(1, 100)], 1, 2316
)
check(tiny_public == ["tiny"], "极小正 Fraction 在公开入口可被选中 (seed 锁定)")

# 10.2 极端比例 10**100 : 1/10**100 —— float() 后微小方严格为零, 浮点路径
#   永不可能选中; 精确放大为 [10**200, 1], needle=total-1 必须命中微小位置。
extreme = [10 ** 100, Fraction(1, 10 ** 100)]
scaled_extreme = app._scale_to_exact_integer_weights(extreme)
extreme_pick = app._sample_indices_exact_integer(
    [0, 1], list(scaled_extreme), 1, _FixedRNG([sum(scaled_extreme) - 1])
)
check(
    scaled_extreme == [10 ** 200, 1] and extreme_pick == [1],
    "极端比例下极小正 Fraction 不被浮点吞掉 (10**200:1, needle=total-1)",
)

# 10.3 零 Fraction 永不入选(含与超大整数混排、整轮抽满)。
zero_frac_ok = all(
    app.weighted_sample_indices(["x", "y"], [Fraction(7, 3), Fraction(0)], 1, s)
    == [0]
    for s in range(200)
)
zero_frac_ok = zero_frac_ok and all(
    app.weighted_sample_indices(["a", "z"], [10 ** 100, Fraction(0)], 1, s)
    == [0]
    for s in range(200)
)
zero_frac_ok = zero_frac_ok and all(
    sorted(app.weighted_sample_indices(
        ["a", "b", "c"],
        [Fraction(1, 2), Fraction(0), Fraction(1, 4)], 2, s)) == [0, 2]
    for s in range(100)
)
check(zero_frac_ok, "零 Fraction 在 200 个 seed 下从不出现, 整轮抽满也被排除")

# 10.4 零 Fraction 在精确定位遍历中被精确跳过。
zero_locate = [10 ** 100, Fraction(0), Fraction(1, 10 ** 100)]
scaled_zero = app._scale_to_exact_integer_weights(zero_locate)
zero_skip_pick = app._sample_indices_exact_integer(
    [0, 1, 2], list(scaled_zero), 1, _FixedRNG([sum(scaled_zero) - 1])
)
check(zero_skip_pick == [2] and scaled_zero[1] == 0,
      "定位遍历时零 Fraction 位置被精确跳过")

# 10.5 混合 int / Fraction / float 的批量序列可复现, 第一轮与单次一致,
#   values 与 indices 两个批量入口逐轮对应。
mixed_items = ["p", "q", "r"]
mixed_weights = [2, Fraction(1), 0.5]  # 精确放大为 [4, 2, 1]
mixed_locked = [[1, 0, 2], [0, 2, 1], [0, 1, 2], [0, 2, 1]]
mixed_idx = app.weighted_sample_many_indices(mixed_items, mixed_weights, 3, 4, 42)
mixed_val = app.weighted_sample_many(mixed_items, mixed_weights, 3, 4, 42)
mixed_ok = (
    mixed_idx == mixed_locked
    and mixed_idx == app.weighted_sample_many_indices(
        mixed_items, mixed_weights, 3, 4, 42)
    and mixed_val == [[mixed_items[i] for i in rd] for rd in mixed_idx]
    and mixed_idx[0] == app.weighted_sample_indices(
        mixed_items, mixed_weights, 3, 42)
    and mixed_val[0] == app.weighted_sample(mixed_items, mixed_weights, 3, 42)
)
check(mixed_ok, "混合 int/Fraction/float 批量序列可复现, 第一轮与单次逐项一致")

# 10.6 极大整数 + 极小分母 Fraction 混排: 不触发浮点转换, 确定可复现。
huge_mixed = [10 ** 400, Fraction(1, 10 ** 400), Fraction(0)]
hm_rounds = app.weighted_sample_many_indices(
    ["H", "t", "z"], huge_mixed, 1, 3, 7
)
check(
    hm_rounds == [[0], [0], [0]]
    and hm_rounds == app.weighted_sample_many_indices(
        ["H", "t", "z"], huge_mixed, 1, 3, 7),
    "混合大整数与 Fraction 的批量序列可复现, 零权重被排除",
)
for w in (Fraction(10 ** 5000, 1), Fraction(1, 10 ** 5000)):
    pick = app.weighted_sample_indices(["a", "b"], [w, 1], 1, 3)
    check(
        pick == app.weighted_sample_indices(["a", "b"], [w, 1], 1, 3),
        "极大分子/极大分母 Fraction 通过校验并确定抽取 (%s)"
        % ("大分子" if w.numerator > 1 else "大分母"),
    )

# 10.7 混合权重的统计比例: [1, 1/3] -> [3,1], 严格 3:1。
frac_counts = [0, 0]
FRAC_TRIALS = 4000
for seed in range(FRAC_TRIALS):
    frac_counts[app.weighted_sample_indices(
        ["a", "b"], [1, Fraction(1, 3)], 1, seed)[0]] += 1
frac_prop_ok = (
    abs(frac_counts[0] / FRAC_TRIALS - 0.75) < 0.04
    and abs(frac_counts[1] / FRAC_TRIALS - 0.25) < 0.04
)
print("  观测比例: %.4f %.4f (期望 0.7500 0.2500)"
      % (frac_counts[0] / FRAC_TRIALS, frac_counts[1] / FRAC_TRIALS))
check(frac_prop_ok, "混合 int/Fraction 第一轮比例收敛到精确的 3:1")

# 10.8 正权重位置不足: 单次与批量都在产生任何结果前抛 ValueError。
raises(ValueError,
       lambda: app.weighted_sample_indices(
           ["a", "b"], [Fraction(1), Fraction(0)], 2, 0),
       "Fraction: 单次入口正权重位置不足 -> ValueError")
raises(ValueError,
       lambda: app.weighted_sample_many_indices(
           ["a", "b"], [Fraction(1), Fraction(0)], 2, 1000, 0),
       "Fraction: 批量入口在任何一轮前 -> ValueError")
raises(ValueError,
       lambda: app.weighted_sample_indices(
           ["a"], [Fraction(0, 10 ** 100)], 1, 0),
       "极小分子的零 Fraction (0/10**100) k>0 -> ValueError")

# 10.9 非法输入只产生确定的 TypeError / ValueError。
raises(TypeError,
       lambda: app.weighted_sample_indices(["a", "b"], [Fraction(1), True], 1, 0),
       "Fraction 混排 bool 权重 -> TypeError")
raises(TypeError,
       lambda: app.weighted_sample_indices(["a", "b"], [Fraction(1), 1 + 2j], 1, 0),
       "Fraction 混排非实数权重 -> TypeError")
raises(ValueError,
       lambda: app.weighted_sample_indices(["a"], [Fraction(-1, 3)], 1, 0),
       "负 Fraction -> ValueError")
raises(ValueError,
       lambda: app.weighted_sample_indices(
           ["a", "b"], [Fraction(1), float("nan")], 1, 0),
       "Fraction 混排 NaN -> ValueError")
raises(ValueError,
       lambda: app.weighted_sample_indices(
           ["a", "b"], [Fraction(1), float("inf")], 1, 0),
       "Fraction 混排正无穷 -> ValueError")

# 10.10 k=0 返回空样本; draws=0 返回空轮次但完成全部校验。
check(app.weighted_sample_indices(
    ["a"], [Fraction(1, 10 ** 100)], 0, 0) == [],
    "Fraction: k=0 且输入合法 -> []")
check(app.weighted_sample_many_indices(["a"], [Fraction(1)], 1, 0, 0) == [],
    "Fraction: draws=0 -> []")
raises(ValueError,
       lambda: app.weighted_sample_many_indices(
           ["a"], [float("nan")], 0, 0, 0),
       "Fraction: draws=0 仍先完成权重校验 (NaN -> ValueError)")

# 10.11 seed=None 随机语义保留; 入参不被修改。
app.weighted_sample_indices(
    ["a", "b"], [Fraction(1, 2), Fraction(1, 3)], 1, None)
print("  PASS: Fraction 权重下 seed=None 可正常工作")

frac_items = ["p", "q", "r"]
frac_weights = [2, Fraction(1, 3), 0.5]
fi_snap, fw_snap = list(frac_items), list(frac_weights)
app.weighted_sample(frac_items, frac_weights, 3, 5)
app.weighted_sample_many(frac_items, frac_weights, 3, 4, 99)
app.weighted_sample_indices(frac_items, frac_weights, 2, -3)
check(frac_items == fi_snap and frac_weights == fw_snap,
      "Fraction: items / weights 原样保留")

# 10.12 不含 Fraction 的小整数 / 普通浮点可观察结果保持不变。
check(
    app.weighted_sample(["red", "green", "blue"], [1, 3, 2], 2, 42)
    == ["green", "red"],
    "Fraction 改动后小整数基线序列仍保持",
)
check(
    sorted(app.weighted_sample(["p", "q"], [0.5, 1.5], 2, 3)) == ["p", "q"],
    "Fraction 改动后普通浮点基线行为仍保持",
)


# ---------------------------------------------------------------------------
# 11. deserialize_metrics: 序列化文本的精确还原
# ---------------------------------------------------------------------------
section("deserialize_metrics 精确还原")

from decimal import Decimal as _Decimal

dm, sm = app.deserialize_metrics, app.serialize_metrics

# 11.1 结构还原: null/布尔/字符串/数组/对象 -> None/bool/str/list/dict。
check(dm('{"a": [1, null, true, "x"], "b": {}}')
      == {"a": [1, None, True, "x"], "b": {}},
      "嵌套结构按 JSON 类型还原, 成员名保持文本形式")
check(dm("{}") == {} and dm("[]") == [], "空对象/空数组还原")

# 11.2 数字完全绕开浮点: 无标记 -> 任意精度 int; 带标记 -> Decimal。
big = 10 ** 5000 - 1
check(dm(sm(big)) == big and type(dm(sm(big))) is int
      and dm(sm(-big)) == -big,
      "5000 位整数(超默认位数限制)往返精确")
dec_ok = all(
    type(dm(lit)) is _Decimal and str(dm(lit)) == str(_Decimal(lit))
    for lit in ("1.50", "-0.00", "0E3", "1E+2", "1E100000", "1E-100000")
)
check(dec_ok, "带小数点/指数标记的数字还原为 Decimal, 保留刻度/指数/负零")
check(type(dm("-0")) is int and dm("-0") == 0, "无标记 -0 按整数规则还原")

# 11.3 Fraction 的二元素数组按普通 list 还原; 再序列化文本逐字一致。
check(dm(sm(Fraction(3, 4))) == [3, 4]
      and type(dm(sm(Fraction(3, 4)))) is list
      and sm(dm(sm(Fraction(3, 4)))) == "[3,4]",
      "Fraction 二元素数组还原为普通 list 且可再精确序列化")

# 11.4 嵌套指标树往返: 整数与 Decimal 的十进制内容精确, 文本逐字一致。
tree = {"名": [1, _Decimal("1.50"), Fraction(3, 4), None, True],
        "big": 10 ** 100, "z": [_Decimal("-0.00")]}
check(sm(dm(sm(tree))) == sm(tree), "嵌套指标树 序列化->还原->序列化 逐字一致")

# 11.5 错误分类: 非 str -> TypeError; 非有限值/语法错误/重复成员名 ->
#   ValueError, 不返回部分结果。
raises(TypeError, lambda: dm(b"{}"), "非 str 输入 (bytes) -> TypeError")
raises(TypeError, lambda: dm(1), "非 str 输入 (int) -> TypeError")
raises(ValueError, lambda: dm("NaN"), "NaN -> ValueError")
raises(ValueError, lambda: dm("[Infinity]"), "Infinity -> ValueError")
raises(ValueError, lambda: dm('{"a":1,"a":2}'), "重复成员名 -> ValueError")
raises(ValueError, lambda: dm("[1,]"), "语法错误 -> ValueError")
raises(ValueError, lambda: dm("1E999999999999999999999999"),
       "无法精确表示的指数 -> ValueError")

# 11.6 checkpoint 状态文本可直接消费并恢复(含浮点 seed)。
cp_items, cp_weights, cp_k = list("abcd"), [1, 3, 2, 0], 3
cp_ok = True
for seed in (0, 42, 1.5, -0.0, 1e300, "s"):
    state = app.weighted_sample_checkpoint(cp_items, cp_weights, cp_k, seed,
                                           start=2)
    restored = dm(sm(state))
    rounds, next_state = app.weighted_sample_resume_indices(
        cp_items, cp_weights, cp_k, restored, 3)
    if rounds != app.weighted_sample_many_indices(
            cp_items, cp_weights, cp_k, 3, seed, start=2):
        cp_ok = False
    more, _ = app.weighted_sample_resume_indices(
        cp_items, cp_weights, cp_k, dm(sm(next_state)), 2)
    if more != app.weighted_sample_many_indices(
            cp_items, cp_weights, cp_k, 2, seed, start=5):
        cp_ok = False
check(cp_ok, "checkpoint 状态经 serialize/deserialize 还原后可断点续接")


# ---------------------------------------------------------------------------
print()
if _FAILURES:
    print("结果: %d 项失败" % len(_FAILURES))
    for f in _FAILURES:
        print("  -", f)
    sys.exit(1)
print("结果: 全部校验通过")
sys.exit(0)
