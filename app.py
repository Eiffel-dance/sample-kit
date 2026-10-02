"""Sample Kit.

公开接口:
    weighted_sample(items, weights, k, seed=0)
        按元素位置的加权无放回抽样, 相同 (输入, seed) 给出完全一致的序列。
    weighted_sample_indices(items, weights, k, seed=0)
        与 weighted_sample 同规则, 但返回按抽样先后排列的零基原始索引;
        items 中相等的值仍按不同位置独立处理。
    weighted_sample_many(items, weights, k, draws, seed=0)
        weighted_sample 的批量入口: 一次调用按同一输入生成 draws 轮加权
        无放回样本, 返回长度等于 draws 的外层序列, 每轮返回元素值。
        每轮都从原始位置重新开始(同一轮内位置最多出现一次, 重复值按位置
        区分, 轮次之间允许再次选中同一位置); 所有轮次共享同一个由 seed
        初始化的随机流, 第一轮与 weighted_sample 逐项相同。
    weighted_sample_many_indices(items, weights, k, draws, seed=0)
        与 weighted_sample_many 同规则, 但每轮返回按抽样先后排列的零基
        原始索引, 两个批量入口逐轮对应。
    serialize_metrics(metrics)
        将指标树稳定序列化为紧凑 JSON 文本, 任意精度整数保持精确十进制。
        字典键先统一转换为成员名文本(str 原样, None->null, bool->true/false,
        int->十进制, 有限 float->编码器数值文本), 再按 Unicode 文本升序排列;
        不同原始键转换得到同一成员名时抛 ValueError。

这些函数都在产生任何结果/文本之前完成全部校验, 非法输入以稳定的
TypeError / ValueError 告知调用方, 且不会修改入参。
"""

import collections.abc
import json
import math
import numbers
import random
import sys
from fractions import Fraction

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
        if isinstance(w, Fraction):
            # Fraction 与 int 同为精确有理数, 既不可能是 NaN 也不可能是
            # 无穷; 直接按精确值判符号, 避免 math.isnan/isinf 把极大分子
            # 或极小分母的 Fraction(如 Fraction(10**5000, 1)、
            # Fraction(1, 10**5000))强制转成浮点而抛 OverflowError。
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


def _validate_draws(draws):
    """批量入口的 draws 必须是非布尔非负整数 (TypeError / ValueError)。"""
    if isinstance(draws, bool) or not isinstance(draws, int):
        raise TypeError("draws must be a non-boolean integer")
    if draws < 0:
        raise ValueError("draws must be non-negative")


def _count_positive_weights(weights):
    """统计严格为正的权重个数。

    整数直接判正负, 不经过浮点 —— 超大整数(如 10**400)也是合法有限值;
    浮点 +0.0/-0.0 都不计入, 正的有限浮点才计入。调用前权重已通过
    类型与取值校验(无 bool / NaN / 无穷 / 负数)。
    """
    count = 0
    for w in weights:
        if isinstance(w, int):
            if w > 0:
                count += 1
        elif w > 0:
            count += 1
    return count


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
    """决定整数权重是否走纯整数路径(规则与基线完全一致)。

    全部权重均为 int (bool 已在类型校验中拒绝) 时, 以全量累计权重决定:
    累计 > 2**53, 或累计无法转换为有限浮点(如 10**400, float() 抛
    OverflowError)时走纯整数路径, 杜绝浮点溢出与舍入。全量累计 <= 2**53
    时, 任意子集累计同样 <= 2**53, 浮点路径逐轮精确可表示, 基线锁定的
    公开序列因此保持不变。
    """
    if k > 0 and all(isinstance(w, int) for w in pool_weights):
        total = sum(pool_weights)
        if total > _EXACT_INTEGER_THRESHOLD:
            return True
        try:
            float(total)
        except OverflowError:
            return True
    return False


def _float_total_is_finite(pool_weights):
    """判断浮点路径的全量累计是否能表示为有限浮点。

    权重全部非负, 任意子集的累计都不超过全量累计, 因此全量累计有限时,
    浮点路径逐轮求和与 needle 边界计算都不可能溢出, 基线序列保持不变。
    全量累计溢出为无穷(如 [1e308, 1e308]), 或求和本身因超大整数与浮点
    混合而抛 OverflowError (如 [10**400, 1.0], int->float 转换溢出)时,
    浮点路径不可用, 调用方须改用精确路径。
    """
    try:
        total = sum(pool_weights)
        return not math.isinf(total)
    except OverflowError:
        return False


def _scale_to_exact_integer_weights(pool_weights):
    """把有限实数权重按统一比例放大为精确整数权重, 供纯整数路径使用。

    每个有限 float 都是分母为 2 的幂的精确分数, int / Fraction 同样
    精确; 取全部分母的最小公倍数作为统一比例放大后, 所有权重成为精确
    整数, 相对比例逐点保持 —— 正权重仍为正(每个正权重位置保留候选资
    格, 哪怕是分子为 1、分母为 10**100 的极小正 Fraction), 零权重仍为
    零(永不被选中)。用于两种场景: 权重序列包含 Fraction(杜绝任何
    float 转换把微小正有理数吞成零、或把精确比例舍入), 以及浮点求和/
    累计会溢出的极端输入。抽样概率严格等于原始正权重的相对比例。
    """
    fractions = [Fraction(w) for w in pool_weights]
    scale = 1
    for f in fractions:
        scale = math.lcm(scale, f.denominator)
    return [int(f * scale) for f in fractions]


def _contains_fraction(pool_weights):
    return any(isinstance(w, Fraction) for w in pool_weights)


def _select_sampling_plan(pool_weights, k):
    """返回 (抽样用权重, 是否走纯整数精确路径)。

    路径选择规则:
      1. 权重序列中只要出现 Fraction(可与 int 及有限 float 混合), 就把
         全部权重按 LCM 统一放大为精确整数后走纯整数路径。这样每个有理
         数都以精确数学值参与抽样: 严格为正的 Fraction(哪怕极小)不会因
         转成 float 而变成零, 比例也不被浮点舍入改变。
      2. 全整数且累计超 2**53 走纯整数路径(基线规则)。
      3. 总和可正常表示的纯 int / float 输入保持既有浮点路径与锁定序列
         不变。
      4. 浮点求和/累计会溢出(有限浮点权重总和为无穷, 或超大整数与浮点
         混合求和溢出)时, 把权重精确放大为整数后走纯整数路径 —— 只改变
         原本会产生无效或不完整结果的极端场景。
    """
    if k > 0 and _contains_fraction(pool_weights):
        return _scale_to_exact_integer_weights(pool_weights), True
    if _use_exact_integer_path(pool_weights, k):
        return pool_weights, True
    if k > 0 and not _float_total_is_finite(pool_weights):
        return _scale_to_exact_integer_weights(pool_weights), True
    return pool_weights, False


def _draw_indices_once(n, pool_weights, k, rng, use_exact):
    """从原始位置出发完成一轮抽样。

    每次调用都重建位置池并复制权重, 因此上一轮的抽走/弹出不会影响下一
    轮 —— 每轮都从全部原始位置重新开始; rng 由调用方共享, 多轮连续消耗
    同一随机流。绝不修改入参 pool_weights。
    """
    pool = list(range(n))
    weights = list(pool_weights)
    if use_exact:
        return _sample_indices_exact_integer(pool, weights, k, rng)
    return _sample_indices_float(pool, weights, k, rng)


def weighted_sample_indices(items, weights, k, seed=0):
    n = _validate_sample_inputs(items, weights, k, seed)

    # 复制到本地, 绝不修改入参。
    pool_weights = list(weights)
    rng = random.Random(seed)
    pool_weights, use_exact = _select_sampling_plan(pool_weights, k)

    return _draw_indices_once(n, pool_weights, k, rng, use_exact)


def weighted_sample(items, weights, k, seed=0):
    indices = weighted_sample_indices(items, weights, k, seed)
    return [items[i] for i in indices]


def weighted_sample_many_indices(items, weights, k, draws, seed=0):
    """weighted_sample_indices 的批量入口: 一次调用生成 draws 轮样本。

    返回长度等于 draws 的外层序列, 每个元素是一轮按抽样先后排列的零基
    原始索引。每轮都从原始位置重新开始(同一轮内位置最多出现一次, 轮次
    之间允许再次选中同一位置); 所有轮次共享同一个由 seed 初始化的随机
    流, 第一轮与 weighted_sample_indices 逐项相同, 后续轮次继续消耗该
    流, 相同调用下得到相同的嵌套序列。seed=None 保留现有随机语义。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    _validate_draws(draws)

    # 可行性前置检查: 每轮无放回抽取 k 个位置, 至少需要 k 个正权重位置
    # (k=0 时即使权重全为零也合法)。在开始任何一轮抽样之前判定, 保证
    # 非法调用确定抛 ValueError 且绝不返回部分外层结果。
    if k > 0 and k > _count_positive_weights(weights):
        raise ValueError("no positive weight")

    pool_weights = list(weights)
    rng = random.Random(seed)
    pool_weights, use_exact = _select_sampling_plan(pool_weights, k)

    rounds = []
    for _ in range(draws):
        rounds.append(
            _draw_indices_once(n, pool_weights, k, rng, use_exact)
        )
    return rounds


def weighted_sample_many(items, weights, k, draws, seed=0):
    """weighted_sample 的批量入口, 规则与 weighted_sample_many_indices
    完全一致, 区别仅在于每轮返回元素值而非原始索引; 两个批量入口逐轮
    逐项对应。
    """
    rounds = weighted_sample_many_indices(items, weights, k, draws, seed)
    return [[items[i] for i in round_indices] for round_indices in rounds]


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
