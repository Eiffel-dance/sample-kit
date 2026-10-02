"""Sample Kit.

公开接口:
    weighted_sample(items, weights, k, seed=0)
        按元素位置的加权无放回抽样, 相同 (输入, seed) 给出完全一致的序列。
    weighted_sample_indices(items, weights, k, seed=0)
        与 weighted_sample 同规则, 返回按抽样先后排列的零基原始索引;
        items 中相等的值仍按位置独立处理, 每个位置至多出现一次。
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

    校验顺序固定: 结构与类型 (TypeError) -> 长度与 k 范围 (ValueError)
    -> 权重元素类型 (TypeError) -> 权重取值 (ValueError)。任何失败都在
    抽样之前发生, 因此不会返回部分结果。
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
        if math.isnan(w):
            raise ValueError("weight at index %d must not be NaN" % index)
        if math.isinf(w):
            raise ValueError("weight at index %d must be finite" % index)
        if w < 0:
            raise ValueError("negative weight")

    return n


def _draw_indices(weights, k, seed, n):
    """确定性加权无放回抽取的共享核心, 返回原始位置索引列表。

    复制到本地 (索引, 权重) 池, 绝不修改入参; 每抽中一个位置就将其移出
    池, 故每个原始位置至多出现一次, 零权重位置永远不会被选中。
    """
    pool = list(enumerate(weights))
    indices = []
    rng = random.Random(seed)
    for _ in range(k):
        total = sum(w for _, w in pool)
        if total <= 0:
            # 仍有抽取请求, 但剩余权重没有正值。
            raise ValueError("no positive weight")
        needle = rng.random() * total
        acc = 0
        for i, (_, w) in enumerate(pool):
            acc += w
            if needle < acc:
                indices.append(pool[i][0])  # 记录原始位置
                pool.pop(i)  # 同一位置不可再次被选
                break
    return indices


def weighted_sample_indices(items, weights, k, seed=0):
    n = _validate_sample_inputs(items, weights, k, seed)
    # k 为 0 时同样完成上面的全部校验, 仅不进行抽取。
    return _draw_indices(weights, k, seed, n)


def weighted_sample(items, weights, k, seed=0):
    n = _validate_sample_inputs(items, weights, k, seed)
    indices = _draw_indices(weights, k, seed, n)
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
