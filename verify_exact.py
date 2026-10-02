#!/usr/bin/env python3
"""精确加权无放回采样的独立校验脚本。

不依赖测试框架, 直接针对 app 公开入口验证:
  1. 索引在范围内、无重复、数量正确;
  2. weighted_sample 的 values 与 weighted_sample_indices 逐项对应;
  3. 10**100 级别权重、极端比例、多轮抽取均确定且按精确整数比例;
  4. 零权重永不选中; 微小正权重不被浮点吞掉;
  5. 相同 (输入, seed) 给出唯一相同序列;
  6. 异常仍按既有 TypeError / ValueError 分类; 入参不被修改;
  7. 小整数(累计 <= 2**53)保持基线浮点路径的固定序列。

用法:  python3 verify_exact.py   (全部通过时退出码为 0)
"""

import math
import random
import sys

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
print()
if _FAILURES:
    print("结果: %d 项失败" % len(_FAILURES))
    for f in _FAILURES:
        print("  -", f)
    sys.exit(1)
print("结果: 全部校验通过")
sys.exit(0)
