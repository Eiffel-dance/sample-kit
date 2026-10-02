"""Sample Kit.

公开接口:
    weighted_sample(items, weights, k, seed=0)
        按元素位置的加权无放回抽样, 相同 (输入, seed) 给出完全一致的序列。
    weighted_sample_indices(items, weights, k, seed=0)
        与 weighted_sample 同规则, 但返回按抽样先后排列的零基原始索引;
        items 中相等的值仍按不同位置独立处理。
    weighted_sample_many(items, weights, k, draws, seed=0)
        一次调用进行 draws 轮加权无放回抽样, 返回长度为 draws 的外层序列,
        每轮为该轮抽中的元素值; 每轮都从原始位置重新开始。
    weighted_sample_many_indices(items, weights, k, draws, seed=0)
        与 weighted_sample_many 同规则, 但每轮返回按抽样先后排列的零基
        原始索引; 两个批量入口逐轮逐项对应。
    serialize_metrics(metrics)
        将指标树稳定序列化为紧凑 JSON 文本, 任意精度整数保持精确十进制。
        字典键先统一转换为成员名文本(str 原样, None->null, bool->true/false,
        int->十进制, 有限 float->编码器数值文本), 再按 Unicode 文本升序排列;
        不同原始键转换得到同一成员名时抛 ValueError。

批量入口的所有轮次共享同一个由 seed 初始化的随机流: 第一轮与对应的
单轮入口逐项相同, 后续轮次继续消耗该流; 同一轮内位置至多出现一次,
轮次之间允许再次选中同一位置。所有函数都在产生任何结果/文本之前完成
全部校验, 非法输入以稳定的 TypeError / ValueError 告知调用方, 且不会
修改入参。
"""

import collections.abc
import json
import math
import numbers
import random
import sys

# 文本/字节类型虽然满足 Sequence 协议, 但不作为“元素序列”接受。
_TEXT_TYPES = (str, bytes, bytearray)

# 与 random.Random 支持的种子类型保持一致: None, int(含 bool), float,
# str, bytes, bytearray。
_SEED_TYPES = (type(None), int, float, str, bytes, bytearray)

# 累计整数权重在该值(含)以内时, 走与基线一致的浮点 rng.random() 路径,
# 以保留已锁定的公开序列; 超过该值则切换到纯整数精确路径。
# 2**53 以内的整数均可被 IEEE-754 双精度精确表示。
_EXACT_INTEGER_THRESHOLD = 1 << 53

# 运行时整数<->文本转换的可配置位数上限(CPython 3.11+,
# sys.set_int_max_str_digits); 无此 API 的解释器上为 None。
_GET_INT_MAX_STR_DIGITS = getattr(sys, "get_int_max_str_digits", None)

# 各位数上限对应的 10**(上限-1) 分块基数缓存, 避免重复构造大数。
_INT_DECIMAL_CHUNK_BASES = {}


def _is_length_determinable_sequence(value):
    """items / weights 必须是长度可确定的非文本序列。"""
    return (
        isinstance(value, collections.abc.Sequence)
        and not isinstance(value, _TEXT_TYPES)
    )


def _validate_sample_inputs(items, weights, k, seed, draws=None):
    """weighted_sample(_indices) / weighted_sample_many(_indices) 共用的
    全部前置校验。

    draws 为 None 时按单轮入口校验; 否则额外按与 k 相同的规则校验批量
    轮数。校验通过后返回位置数 n; 非法输入以稳定的 TypeError /
    ValueError 告知调用方, 不会触碰 items / weights 的内容。
    """
    # ---- 1. 结构与参数类型 (TypeError) ----
    if not _is_length_determinable_sequence(items):
        raise TypeError("items must be a length-determinable sequence")
    if not _is_length_determinable_sequence(weights):
        raise TypeError("weights must be a length-determinable sequence")
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be a non-boolean integer")
    if draws is not None:
        if isinstance(draws, bool) or not isinstance(draws, int):
            raise TypeError("draws must be a non-boolean integer")
    if not isinstance(seed, _SEED_TYPES):
        raise TypeError("unsupported seed type: %s" % type(seed).__name__)

    # ---- 2. 长度与抽样数量 (ValueError) ----
    n = len(items)
    if len(weights) != n or k < 0 or k > n:
        raise ValueError("invalid sample size")
    if draws is not None and draws < 0:
        raise ValueError("draws must be non-negative")

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


def _use_exact_integer_path(pool_weights, k):
    """与单轮入口完全一致的路径判定: 全部权重均为 int (bool 已在类型
    校验中拒绝) 时, 以全量累计权重决定路径 —— 累计 > 2**53, 或累计无法
    转换为有限浮点(如 10**400, float() 抛 OverflowError)时走纯整数路径,
    杜绝浮点溢出与舍入; 全量累计 <= 2**53 时任意子集累计同样 <= 2**53,
    浮点路径逐轮精确可表示, 基线锁定的公开序列因此保持不变。
    """
    if k <= 0 or not all(isinstance(w, int) for w in pool_weights):
        return False
    total = sum(pool_weights)
    if total > _EXACT_INTEGER_THRESHOLD:
        return True
    try:
        float(total)
    except OverflowError:
        return True
    return False


def weighted_sample_indices(items, weights, k, seed=0):
    n = _validate_sample_inputs(items, weights, k, seed)

    # 复制到本地池, 绝不修改入参。
    pool = list(range(n))
    pool_weights = list(weights)
    rng = random.Random(seed)

    if _use_exact_integer_path(pool_weights, k):
        return _sample_indices_exact_integer(pool, pool_weights, k, rng)
    return _sample_indices_float(pool, pool_weights, k, rng)


def weighted_sample(items, weights, k, seed=0):
    indices = weighted_sample_indices(items, weights, k, seed)
    return [items[i] for i in indices]


def weighted_sample_many_indices(items, weights, k, draws, seed=0):
    """批量入口: 一次调用产出 draws 轮加权无放回抽样的零基原始索引。

    返回长度为 draws 的外层列表, 每个元素是该轮长度为 k 的索引列表。
    所有轮次共享同一个由 seed 初始化的随机流: 第一轮与
    weighted_sample_indices(items, weights, k, seed) 逐项相同, 后续轮次
    从同一原始位置序列重新开始, 继续消耗该随机流。同一轮内位置至多
    出现一次, 轮次之间允许再次选中同一位置。全部参数在任何抽样开始前
    一次性校验, 非法时抛 TypeError / ValueError 且不返回部分外层结果。
    """
    n = _validate_sample_inputs(items, weights, k, seed, draws)
    pool_weights = list(weights)

    # 批量入口要求“整次调用确定”可完成: 正权重位置数必须足以支撑每轮
    # 的 k 次无放回抽取。k=0 时即使权重全为零也合法(每轮为空)。该检查在
    # 抽样前完成, 保证失败时不会产生任何部分外层结果。校验已保证每个权重
    # 都是有限、非负的实数, 故 w > 0 对 int 与 float 均为精确判定。
    if k > 0:
        positive_positions = sum(1 for w in pool_weights if w > 0)
        if positive_positions < k:
            raise ValueError("no positive weight")

    rng = random.Random(seed)
    use_exact = _use_exact_integer_path(pool_weights, k)

    rounds = []
    for _ in range(draws):
        # 每轮从原始位置序列重新开始; 池与权重均为本轮私有副本,
        # 绝不修改入参, 也不影响其他轮次。
        pool = list(range(n))
        round_weights = list(pool_weights)
        if use_exact:
            rounds.append(
                _sample_indices_exact_integer(pool, round_weights, k, rng)
            )
        else:
            rounds.append(
                _sample_indices_float(pool, round_weights, k, rng)
            )
    return rounds


def weighted_sample_many(items, weights, k, draws, seed=0):
    """与 weighted_sample_many_indices 同规则, 但每轮返回元素值。"""
    rounds = weighted_sample_many_indices(items, weights, k, draws, seed)
    return [[items[i] for i in indices] for indices in rounds]


# ---------------------------------------------------------------------------
# 指标序列化
# ---------------------------------------------------------------------------

def _int_to_decimal_text(value):
    """把任意位数的 int 精确转换成十进制文本, 全程不经过浮点。

    CPython 3.11+ 的整数<->文本转换有可配置的位数上限
    (sys.set_int_max_str_digits, 默认约 4300 位, 最低 640 位), 直接
    str(value) 会在位数超限时抛 ValueError。这里按固定宽度的十进制块
    从低位向上 divmod, 块宽取运行时当前上限减 1, 故每块的转换都严格
    位于限制之内; 再把最高块的原文与其余补零到固定宽度的块拼接, 得到
    与 str(value) 逐字一致的结果: 零值为 "0", 负数带一个前导 "-"。

    运行时关闭限制(上限为 0)或解释器没有该限制时直接使用 str, 保持
    与标准库一致的速度。
    """
    if _GET_INT_MAX_STR_DIGITS is None:
        return str(int(value))
    limit = _GET_INT_MAX_STR_DIGITS()
    if limit == 0:
        return str(int(value))
    # 剥除 int 子类可能自定义的 __str__/__repr__: 标准库编码器对整数一律
    # 使用 int.__repr__, 序列化结果只取决于整数值, 且必须是合法十进制。
    value = int(value)
    width = limit - 1
    negative = value < 0
    if negative:
        value = -value
    base = _INT_DECIMAL_CHUNK_BASES.get(width)
    if base is None:
        base = 10 ** width
        _INT_DECIMAL_CHUNK_BASES[width] = base
    if value < base:
        # 常见路径: 位数本就在限制之内, 与 str 完全一致且零额外开销。
        text = str(value)
    else:
        low_chunks = []
        while value >= base:
            # 单次 divmod 同时取商和余数, 避免两次大数除法。
            value, remainder = divmod(value, base)
            low_chunks.append(remainder)
        parts = [str(value)]
        zero_pad = "0%d" % width
        for chunk in reversed(low_chunks):
            parts.append(format(chunk, zero_pad))
        text = "".join(parts)
    return "-" + text if negative else text


class _ExactIntegerEncoder(json.JSONEncoder):
    """沿用标准库 JSON 编码器的全部规则, 只把整数数值文本替换为不受
    位数限制的精确十进制转换。

    通过 iterencode(..., _one_shot=False) 强制使用 Python 版
    _make_iterencode, 并注入自定义 _intstr: 字符串转义、float 数值文本
    (-0.0、指数写法)、None/bool、分隔符、键排序、tuple 按数组等行为均
    与 json.dumps 完全一致。bool 在编码器内部先于 int 分派, 不会进入
    _intstr, 因此仍输出 true/false。
    """

    def iterencode(self, o, _one_shot=False):
        markers = {} if self.check_circular else None
        # 模块级名字在有 C 加速时已被别名成 c_ 版本, 否则是纯 Python 版本,
        # 与标准库 JSONEncoder.iterencode 的选择完全一致。
        if self.ensure_ascii:
            encoder = json.encoder.encode_basestring_ascii
        else:
            encoder = json.encoder.encode_basestring

        def floatstr(o, allow_nan=self.allow_nan,
                     _repr=float.__repr__, _inf=json.encoder.INFINITY,
                     _neginf=-json.encoder.INFINITY):
            if o != o:
                text = "NaN"
            elif o == _inf:
                text = "Infinity"
            elif o == _neginf:
                text = "-Infinity"
            else:
                return _repr(o)
            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: "
                    + repr(o)
                )
            return text

        if self.indent is None or isinstance(self.indent, str):
            indent = self.indent
        else:
            indent = " " * self.indent
        return json.encoder._make_iterencode(
            markers, self.default, encoder, indent, floatstr,
            self.key_separator, self.item_separator, self.sort_keys,
            self.skipkeys, _one_shot, _intstr=_int_to_decimal_text,
        )(o, 0)


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
        # 不用 str(key): 整数位数超过运行时限制时会失败。分块转换对任意
        # 位数都给出与 str 逐字一致的精确十进制成员名。
        return _int_to_decimal_text(key)
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
    return "".join(
        _ExactIntegerEncoder(
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).iterencode(normalized, _one_shot=False)
    )
