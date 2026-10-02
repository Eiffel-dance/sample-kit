"""Sample Kit.

公开接口:
    weighted_sample(items, weights, k, seed=0)
        按元素位置的加权无放回抽样, 相同 (输入, seed) 给出完全一致的序列。
    weighted_sample_indices(items, weights, k, seed=0)
        与 weighted_sample 同规则, 但返回按抽样先后排列的零基原始索引;
        items 中相等的值仍按不同位置独立处理。

权重全部为非负整数且累计值大于 2**53 时, 抽样切换到任意精度整数
路径, 按整数权重的精确比例决定, 不经过浮点, 与平台字长无关; 其余
情况沿用既有浮点规则, 公开序列与 seed 语义保持不变。
    serialize_metrics(metrics)
        将指标树稳定序列化为紧凑 JSON 文本, 任意精度整数保持精确十进制。

两个函数都在产生任何结果/文本之前完成全部校验, 非法输入以稳定的
TypeError / ValueError 告知调用方, 且不会修改入参。
"""

import collections.abc
import json
import math
import numbers
import random

# 文本/字节类型虽然满足 Sequence 协议, 但不作为“元素序列”接受。
_TEXT_TYPES = (str, bytes, bytearray)

# 与 random.Random 支持的种子类型保持一致: None, int(含 bool), float,
# str, bytes, bytearray。
_SEED_TYPES = (type(None), int, float, str, bytes, bytearray)


def _is_length_determinable_sequence(value):
    """items / weights 必须是长度可确定的非文本序列。"""
    return (
        isinstance(value, collections.abc.Sequence)
        and not isinstance(value, _TEXT_TYPES)
    )


def _validate_sample_inputs(items, weights, k, seed):
    """weighted_sample / weighted_sample_indices 共用的全部前置校验。

    校验通过后返回位置数 n; 非法输入以稳定的 TypeError / ValueError
    告知调用方, 不会触碰 items / weights 的内容。
    """
    # ---- 1. 结构与参数类型 (TypeError) ----
    if not _is_length_determinable_sequence(items):
        raise TypeError("items must be a length-determinable sequence")
    if not _is_length_determinable_sequence(weights):
        raise TypeError("weights must be a length-determinable sequence")
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be a non-boolean integer")
    if not isinstance(seed, _SEED_TYPES):
        raise TypeError("unsupported seed type: %s" % type(seed).__name__)

    # ---- 2. 长度与抽样数量 (ValueError) ----
    n = len(items)
    if len(weights) != n or k < 0 or k > n:
        raise ValueError("invalid sample size")

    # ---- 3. 权重类型: 布尔值和非实数权重 (TypeError) ----
    for index, w in enumerate(weights):
        if isinstance(w, bool) or not isinstance(w, numbers.Real):
            raise TypeError(
                "weight at index %d must be a real number, not %s"
                % (index, type(w).__name__)
            )

    # ---- 4. 权重取值: NaN / 无穷 / 负数 (ValueError) ----
    for index, w in enumerate(weights):
        if isinstance(w, int):
            # 任意精度整数必然有限且非 NaN; math.isnan/isinf 对超出
            # float 上限的巨大 int 会抛 OverflowError, 必须绕开。
            if w < 0:
                raise ValueError("negative weight")
            continue
        if math.isnan(w):
            raise ValueError("weight at index %d must not be NaN" % index)
        if math.isinf(w):
            raise ValueError("weight at index %d must be finite" % index)
        if w < 0:
            raise ValueError("negative weight")

    return n


# 整数权重累计值不超过 2**53 时, 浮点路径的累计与比较都是精确的,
# 继续沿用既有公开序列; 超过该阈值(或累计值无法表示为有限浮点数,
# 对整数而言等价于超过浮点最大精确整数)时切换到纯整数精确路径。
_EXACT_INT_TOTAL_THRESHOLD = 1 << 53


def _float_sample_indices(weights, k, rng):
    """基线浮点路径: 与既有公开序列逐位一致, 不得改动。"""
    pool = list(range(len(weights)))
    pool_weights = list(weights)
    indices = []
    for _ in range(k):
        total = sum(pool_weights)
        if total <= 0:
            # 仍有抽取请求, 但剩余权重没有正值。
            raise ValueError("no positive weight")
        needle = rng.random() * total
        acc = 0
        for i, w in enumerate(pool_weights):
            acc += w
            if needle < acc:
                indices.append(pool[i])  # 记录原始零基位置
                pool.pop(i)
                pool_weights.pop(i)  # 同一位置不可再次被选
                break
    return indices


def _exact_int_sample_indices(weights, k, rng):
    """任意精度整数路径。

    每轮以 rng.randrange(total) 取得 [0, total) 上的均匀整数针, 再按
    累计整数权重定位; 全程只使用任意精度整数运算, 比例精确, 不经过
    浮点, 因而不会溢出、不会因舍入吞掉微小正权重, 也与平台字长和
    浮点实现无关。零权重位置使累计值原地踏步, 永远不会被命中。
    """
    pool = list(range(len(weights)))
    pool_weights = list(weights)
    indices = []
    for _ in range(k):
        total = sum(pool_weights)
        if total <= 0:
            # 仍有抽取请求, 但剩余权重没有正值。
            raise ValueError("no positive weight")
        needle = rng.randrange(total)
        acc = 0
        for i, w in enumerate(pool_weights):
            acc += w
            if needle < acc:
                indices.append(pool[i])  # 记录原始零基位置
                pool.pop(i)
                pool_weights.pop(i)  # 同一位置不可再次被选
                break
    return indices


def weighted_sample_indices(items, weights, k, seed=0):
    _validate_sample_inputs(items, weights, k, seed)

    # 以下为确定性的加权无放回抽取; 复制到本地池, 绝不修改入参。
    rng = random.Random(seed)
    if (
        all(isinstance(w, int) for w in weights)
        and sum(weights) > _EXACT_INT_TOTAL_THRESHOLD
    ):
        # 全部为非负整数(布尔权重已在校验阶段拒绝)且累计值超出浮点
        # 精确范围: 按整数权重的精确比例抽取。
        return _exact_int_sample_indices(weights, k, rng)
    return _float_sample_indices(weights, k, rng)


def weighted_sample(items, weights, k, seed=0):
    indices = weighted_sample_indices(items, weights, k, seed)
    return [items[i] for i in indices]


# ---------------------------------------------------------------------------
# 指标序列化
# ---------------------------------------------------------------------------

def _check_jsonable(value, on_path):
    """递归确认 value 可被 JSON 表示。

    - 任意大小的 int 原样接受(由 json 以精确十进制输出, 不经过浮点);
    - NaN / Infinity 抛 ValueError;
    - 集合、循环引用及其他不可表示的值抛 TypeError。
    on_path 记录当前祖先容器的 id, 用于检出循环引用(兄弟节点共享同一
    对象不属于循环, 不做标记)。
    """
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):  # 必须在 float 之前; bool 已先行返回
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and Infinity are not JSON serializable")
        return
    if isinstance(value, str):
        return

    if isinstance(value, (list, tuple)):
        marker = id(value)
        if marker in on_path:
            raise TypeError("circular reference detected")
        on_path.add(marker)
        try:
            for element in value:
                _check_jsonable(element, on_path)
        finally:
            on_path.discard(marker)
        return

    if isinstance(value, dict):
        marker = id(value)
        if marker in on_path:
            raise TypeError("circular reference detected")
        on_path.add(marker)
        try:
            for key, element in value.items():
                # json 仅接受 str / int / float / bool / None 作为键。
                if key is None or isinstance(key, (str, int, float)):
                    if isinstance(key, float) and not math.isfinite(key):
                        raise ValueError(
                            "NaN and Infinity are not JSON serializable"
                        )
                else:
                    raise TypeError(
                        "dict keys must be str, int, float, bool or None, "
                        "not %s" % type(key).__name__
                    )
                _check_jsonable(element, on_path)
        finally:
            on_path.discard(marker)
        return

    # set / frozenset / bytes / 自定义对象等均不可表示。
    raise TypeError("object is not JSON serializable: %s" % type(value).__name__)


def serialize_metrics(metrics):
    # 先做完整校验: 把循环引用(json 原生报 ValueError)等统一成 TypeError,
    # 保证任何非法输入都不会产出截断或近似文本。
    _check_jsonable(metrics, set())
    return json.dumps(
        metrics,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
