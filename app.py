"""Sample Kit.

公开接口:
    weighted_sample(items, weights, k, seed=0)
        按元素位置的加权无放回抽样, 相同 (输入, seed) 给出完全一致的序列。
    weighted_sample_indices(items, weights, k, seed=0)
        与 weighted_sample 同规则, 但返回按抽样先后排列的零基原始索引;
        items 中相等的值仍按不同位置独立处理。
    serialize_metrics(metrics)
        将指标树稳定序列化为紧凑 JSON 文本, 任意精度整数保持精确十进制。
        字典键先统一转换为成员名文本(str 原样, None->null, bool->true/false,
        int->十进制, 有限 float->编码器数值文本), 再按 Unicode 文本升序排列;
        不同原始键转换得到同一成员名时抛 ValueError。

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

# 累计整数权重在该值(含)以内时, 走与基线一致的浮点 rng.random() 路径,
# 以保留已锁定的公开序列; 超过该值则切换到纯整数精确路径。
# 2**53 以内的整数均可被 IEEE-754 双精度精确表示。
_EXACT_INTEGER_THRESHOLD = 1 << 53


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
        # 整数(布尔已在第 3 步拒绝)既不可能是 NaN 也不可能是无穷; 直接判断
        # 符号, 避免 math.isnan/isinf 把超大整数(如 10**400)转成浮点而抛
        # OverflowError —— 任意精度整数权重始终是合法的有限权重。
        if isinstance(w, int):
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


def _sample_indices_float(pool, weights, k, rng):
    """基于 rng.random() 的经典浮点加权无放回抽样(基线算法)。

    仅用于非整数权重, 或全部为整数且每轮累计权重都能被双精度精确表示
    的情形; 这样基线已锁定的公开序列完全不变。
    """
    indices = []
    for _ in range(k):
        total = sum(weights)
        if total <= 0:
            # 仍有抽取请求, 但剩余权重没有正值。
            raise ValueError("no positive weight")
        needle = rng.random() * total
        acc = 0
        for i, w in enumerate(weights):
            acc += w
            if needle < acc:
                indices.append(pool[i])  # 记录原始零基位置
                pool.pop(i)
                weights.pop(i)  # 同一位置不可再次被选
                break
    return indices


def _sample_indices_exact_integer(pool, weights, k, rng):
    """纯整数加权无放回抽样, 全程不经过浮点。

    每一轮在剩余位置中, 以各自整数权重为比例均匀抽取: 取区间
    [0, total) 内与平台无关的均匀整数 needle, 再按累计权重定位。
    needle 由 rng.getrandbits 拒绝采样产生 —— Mersenne Twister 的整数
    输出只取决于 seed, 与字长 / 浮点实现无关。拒绝落在 [total, 2**bits)
    的样本, 保证严格均匀, 微小正权重(哪怕相对 total 只有 10**-100)也
    保持精确的选中比例, 既不会被舍入吞掉, 零权重也永远不会被选中。
    """
    indices = []
    for _ in range(k):
        total = sum(weights)
        if total <= 0:
            # 仍有抽取请求, 但剩余权重没有正值。
            raise ValueError("no positive weight")
        bits = (total - 1).bit_length()
        modulus = 1 << bits
        # total 恰为 2 的幂时 [0, total) 恰好铺满 bits 位, 无需拒绝采样。
        if total == modulus:
            needle = rng.getrandbits(bits)
        else:
            # 最大的 modulus 的整数倍上界; needle 落在 [limit, modulus)
            # 时拒绝重抽, 避免取模引入的偏差。
            limit = modulus - (modulus % total)
            while True:
                needle = rng.getrandbits(bits)
                if needle < limit:
                    break
            needle %= total
        acc = 0
        for i, w in enumerate(weights):
            acc += w
            if needle < acc:
                indices.append(pool[i])  # 记录原始零基位置
                pool.pop(i)
                weights.pop(i)  # 同一位置不可再次被选
                break
    return indices


def weighted_sample_indices(items, weights, k, seed=0):
    n = _validate_sample_inputs(items, weights, k, seed)

    # 复制到本地池, 绝不修改入参。
    pool = list(range(n))
    pool_weights = list(weights)
    rng = random.Random(seed)

    # 全部权重均为 int (bool 已在类型校验中拒绝) 时, 以全量累计权重决定
    # 路径: 累计 > 2**53, 或累计无法转换为有限浮点(如 10**400,
    # float() 抛 OverflowError)时走纯整数路径, 杜绝浮点溢出与舍入。
    # 全量累计 <= 2**53 时, 任意子集累计同样 <= 2**53, 浮点路径逐轮
    # 精确可表示, 基线锁定的公开序列因此保持不变。
    use_exact = False
    if k > 0 and all(isinstance(w, int) for w in pool_weights):
        total = sum(pool_weights)
        if total > _EXACT_INTEGER_THRESHOLD:
            use_exact = True
        else:
            try:
                float(total)
            except OverflowError:
                use_exact = True

    if use_exact:
        return _sample_indices_exact_integer(pool, pool_weights, k, rng)
    return _sample_indices_float(pool, pool_weights, k, rng)


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


def _key_to_member_name(key):
    """把合法的 JSON 字典键转换为成员名文本。

    转换必须先于最终编码完成, 这样混合键类型也有确定结果:
    str 原样; None -> "null"; bool -> "true"/"false"; int -> 不带前导零的
    十进制; 有限 float -> 当前 JSON 编码器产生的数值文本(保留 -0.0 与
    指数表示)。调用前 key 已通过 _check_jsonable 校验。
    """
    if isinstance(key, str):
        return key
    if key is None:
        return "null"
    if isinstance(key, bool):  # 必须在 int 之前判断
        return "true" if key else "false"
    if isinstance(key, int):
        return str(key)
    # 有限 float: 复用编码器对浮点值的数值文本规则。
    return json.dumps(key, allow_nan=False)


def _normalize_dict_keys(value):
    """递归构造新树, 把每层字典的键统一转换为字符串成员名。

    不修改入参; 输入已通过 _check_jsonable 校验(键类型合法、浮点键有限、
    无循环引用, 共享子对象在此重复展开即可)。两个不同的原始键转换后得到
    同一成员名时抛 ValueError, 绝不静默覆盖或依赖插入顺序。
    """
    if isinstance(value, dict):
        normalized = {}
        for key, element in value.items():
            name = _key_to_member_name(key)
            if name in normalized:
                raise ValueError(
                    "dict keys collide after conversion to member name %r"
                    % name
                )
            normalized[name] = _normalize_dict_keys(element)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_normalize_dict_keys(element) for element in value]
    return value


def serialize_metrics(metrics):
    # 先做完整校验: 把循环引用(json 原生报 ValueError)等统一成 TypeError,
    # 保证任何非法输入都不会产出截断或近似文本。
    _check_jsonable(metrics, set())
    # 再把全部字典键转换为成员名文本(同时检出转换冲突), 最后编码时
    # 按键名的 Unicode 文本升序排列 —— 同一数据内容无论构造顺序如何
    # 都得到同一份文本。
    normalized = _normalize_dict_keys(metrics)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
