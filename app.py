"""Sample Kit.

公开接口:
    weighted_sample(items, weights, k, seed=0)
        按元素位置的加权无放回抽样, 相同 (输入, seed) 给出完全一致的序列。
    weighted_sample_indices(items, weights, k, seed=0)
        与 weighted_sample 同规则, 但返回按抽样先后排列的零基原始索引;
        items 中相等的值仍按不同位置独立处理。
    weighted_sample_excluding_indices(items, weights, k, excluded=(), seed=0)
        与 weighted_sample_indices 同规则, 但先按原始零基位置排除
        excluded 中的位置再抽样: excluded 按集合语义解释(重复位置与排列
        顺序不影响结果), 被排除的位置即使权重为正也绝不出现, 未排除的
        零权重位置仍永不入选; 返回按抽样先后排列的零基原始索引。
        excluded 为空时结果与 weighted_sample_indices 逐项相同。
        excluded 必须是非文本且长度可确定的序列, 成员必须是非布尔整数
        且处于 items 的零基范围内; 结构或成员类型错误抛 TypeError,
        越界位置抛 ValueError。k=0 时仍完成全部校验并返回空列表;
        k>0 而未排除位置中的正权重不足 k 个时, 在产生任何结果前抛
        ValueError。
    weighted_sample_excluding(items, weights, k, excluded=(), seed=0)
        与 weighted_sample_excluding_indices 同规则(同一套校验与异常
        类别), 但按相同索引返回元素值列表, 两个入口逐项对应。
    weighted_sample_many(items, weights, k, draws, seed=0, start=0)
        weighted_sample 的批量入口: 一次调用按同一输入生成 draws 轮加权
        无放回样本, 返回长度等于 draws 的外层序列, 每轮返回元素值。
        每轮都从原始位置重新开始(同一轮内位置最多出现一次, 重复值按位置
        区分, 轮次之间允许再次选中同一位置); 所有轮次共享同一个由 seed
        初始化的随机流, 第一轮与 weighted_sample 逐项相同。
        可选的 start(默认 0)表示先从该 seed 对应的轮次流开始跳过 start
        个完整轮次(跳过只消耗同一条确定性随机流), 再生成 draws 轮;
        结果与 start=0 的完整调用按零基区间 [start, start+draws) 切片
        逐项一致。start 只接受非布尔整数(其他类型 TypeError), 不得为负
        (负数 ValueError)。
    weighted_sample_many_indices(items, weights, k, draws, seed=0, start=0)
        与 weighted_sample_many 同规则(含 start 窗口语义), 但每轮返回
        按抽样先后排列的零基原始索引, 两个批量入口逐轮对应。
    weighted_sample_schedule_indices(items, weights_schedule, k, draws,
        seed=0, start=0)
        按轮次变化权重的批量入口: weights_schedule 是有限非文本序列,
        成员均为与 items 等长的权重序列; 第 start+j 轮使用
        weights_schedule[start+j]。返回 draws 轮, 每轮是按抽样先后排列
        的零基原始索引; 每轮从全部位置重新开始, 轮内无放回, 重复值按
        位置区分。所有轮共享由 seed 初始化的一条随机流; start 只跳过
        完整轮次并消耗与从 0 生成时相同的随机流, k=0 的轮次返回空列表
        且不消耗随机流。start=0 的首轮与 weighted_sample_indices 对应行
        逐项一致; 权重各行相同则与 weighted_sample_many_indices 同参
        完全一致。校验在返回任何轮次前完成: schedule 或任一行结构非法
        抛 TypeError; 行长度不等于 items、窗口超出 schedule 范围、负
        权重、NaN、无穷权重, 或任一行在 k>0 时正权重位置不足 k 个时抛
        ValueError; draws=0 仍完成全部校验并返回空列表。不修改入参与
        schedule。
    weighted_sample_schedule(items, weights_schedule, k, draws, seed=0,
        start=0)
        与 weighted_sample_schedule_indices 同规则(同一套校验顺序与
        异常类别), 但每轮按相同索引返回元素值列表, 两个入口逐轮逐项
        对应。
    weighted_sample_counts(items, weights, k, draws, seed=0, start=0)
        weighted_sample_many_indices 的批量频次入口: 接受与该入口相同
        的 items、weights、k、draws、seed、start 语义与校验顺序, 按同一
        随机流生成窗口内的轮次, 返回长度等于 items 的整数 list counts,
        counts[i] 是零基区间 [start, start+draws) 中原始位置 i 被选中的
        次数(每轮无放回, 相等的元素值仍按不同位置分别累计)。结果等于
        把 weighted_sample_many_indices 对应窗口的全部轮次按位置摊平
        计数; 首轮、后续轮次、相同种子以及 k=0 的随机流消耗逐项对齐。
        draws=0 或 k=0 返回全零列表(仍完成全部校验), 正权重不足在返回
        列表前抛 ValueError, 任何失败都不给出部分计数。计数为任意精度
        整数, 可直接交给 serialize_metrics 并经 deserialize_metrics
        精确往返。不修改入参。
    weighted_sample_stream_indices(items, weights, k, draws, seed=0, start=0)
        weighted_sample_many_indices 的按需逐轮入口: 返回一个可迭代对象,
        调用方逐轮取得与 weighted_sample_many_indices 完全一致的轮次
        (每轮一份按抽样先后排列的零基原始索引列表), 不必一次物化全部
        draws 轮。完整校验在调用时完成, 失败结果在产生第一轮前确定。
        start 语义与批量入口相同: 迭代时先按需跳过 start 个完整轮次。
    weighted_sample_stream(items, weights, k, draws, seed=0, start=0)
        与 weighted_sample_stream_indices 同规则, 但每轮按相同索引产出
        元素值列表, 与 weighted_sample_many 逐轮对应。
    weighted_sample_many_excluding_indices(items, weights, k, excluded,
        draws, seed=0, start=0)
        weighted_sample_excluding_indices 的批量入口: 一次调用按同一输入
        生成 draws 轮"按原始零基位置排除后"的加权无放回样本, 返回长度
        等于 draws 的外层序列, 每轮返回按抽样先后排列的原始零基索引。
        每轮都从同一组未排除位置重新开始(轮内位置最多出现一次, 轮次
        之间恢复全部未排除位置, 重复值按位置区分), 被排除的位置即使
        权重为正也绝不出现, 未排除的零权重位置仍永不入选; 所有轮次共享
        同一个由 seed 初始化的随机流, start=0 的第一轮与
        weighted_sample_excluding_indices 逐项相同, excluded 为空时与
        weighted_sample_many_indices 逐轮一致。start 语义与既有批量
        入口相同: 先跳过 start 个完整轮次(只消耗同一条确定性随机流),
        结果与 start=0 的完整调用按区间 [start, start+draws) 切片逐项
        一致。校验顺序固定为 items/weights/k/seed、excluded、draws、
        start, 随后在产生任何一轮前完成未排除位置的正权重可行性检查;
        draws=0 返回空结果, k=0 时每轮为空且跳过轮次不消耗随机流。
    weighted_sample_many_excluding(items, weights, k, excluded, draws,
        seed=0, start=0)
        与 weighted_sample_many_excluding_indices 同规则(同一套校验
        顺序、异常类别与 start 窗口语义), 但每轮按相同索引返回元素值,
        两个批量排除入口逐轮逐项对应。
    weighted_sample_excluding_counts(items, weights, k, excluded, draws,
        seed=0, start=0)
        weighted_sample_many_excluding_indices 的批量频次入口: 接受与该
        入口相同的 items、weights、k、excluded、draws、seed、start 语义
        与固定校验顺序, 按同一随机流生成窗口内的轮次, 返回长度等于
        items 的整数 list counts, counts[i] 是零基区间
        [start, start+draws) 中原始位置 i 被选中的次数; 被排除位置的
        计数始终为零, 其余位置按每轮重新开始的未排除位置池累计(相等
        的元素值仍按不同位置分别累计)。结果等于把
        weighted_sample_many_excluding_indices 对应窗口的全部轮次按
        位置摊平计数; 首轮、后续轮次、相同种子以及 k=0 的随机流消耗
        逐项对齐。draws=0 或 k=0 返回全零列表(仍完成全部校验, 含
        excluded 与可行性检查), 正权重不足在返回列表前抛 ValueError,
        任何失败都不给出部分计数。计数为任意精度整数, 可直接交给
        serialize_metrics 并经 deserialize_metrics 精确往返。不修改
        入参, 也不修改 excluded。
    weighted_sample_stream_excluding_indices(items, weights, k, excluded,
        draws, seed=0, start=0)
        weighted_sample_many_excluding_indices 的按需逐轮入口: 返回一个
        可迭代对象, 调用方逐轮取得与批量入口完全一致的轮次(每轮一份
        按抽样先后排列的零基原始索引列表), 不必一次物化全部 draws 轮。
        轮次虽按需产出, 但全部参数与可行性错误都在创建时完成校验并
        当场抛出, 不会延迟到已经产出部分轮次之后; start 在迭代时按需
        跳过, 语义与批量入口相同。
    weighted_sample_stream_excluding(items, weights, k, excluded, draws,
        seed=0, start=0)
        与 weighted_sample_stream_excluding_indices 同规则(同一套
        创建时校验与 start 窗口语义), 但每轮按相同索引产出元素值列表,
        与 weighted_sample_many_excluding 逐轮对应。
    weighted_sample_checkpoint(items, weights, k, seed=0, start=0)
        创建可暂停/恢复的采样会话断点: 接受与批量入口相同的输入及 start,
        在完成与批量入口一致的全部校验(含正权重可行性)后, 把随机流推进到
        "已完成 start 轮"的位置并快照, 返回只含 JSON 原生值的状态映射。
        状态携带版本、当前位置(已完成轮次)、k/n、校验 items 与 weights
        所需的指纹、标签化 seed 以及 RNG 内部状态; 可直接交给
        serialize_metrics, 经 json 序列化/解析(甚至跨进程)后仍可恢复,
        调用方不依赖任何进程内对象身份。
    weighted_sample_resume_indices(items, weights, k, state, draws)
        从断点继续: 传入与创建断点时相同的 items、weights、k 与状态,
        返回 (轮次列表, 下一状态)。第一轮从断点位置开始, 逐轮等于
        weighted_sample_many_indices 对应零基区间 [pos, pos+draws);
        下一状态可再次传入本入口继续推进。draws=0 时返回空轮次与未改变
        的状态; k=0 时每轮为空索引列表且位置照常推进。状态不是映射抛
        TypeError; 状态结构非法、版本不支持或与 items/weights/k 不匹配
        统一抛 ValueError; 其余输入错误沿用既有 TypeError / ValueError。
    weighted_sample_resume(items, weights, k, state, draws)
        按元素值恢复的公开入口, 规则与 weighted_sample_resume_indices
        完全一致(同一套 items/weights/k 采样入口校验、state 恢复入口校验
        与异常类别; weights 不足仍是 ValueError): 传入与创建断点时相同的
        items、weights、k 与状态, 返回 (轮次列表, 下一状态)。每轮是元素值
        列表, 其顺序与内容等于按索引恢复返回的每轮原始位置逐项映射
        (round_values[j] == items[round_indices[j]]), 因此相同值的不同位置
        分别消耗, 轮内绝不出现重复位置。返回的下一状态与按索引入口返回的
        完全相同(position、RNG 快照、digest 一致), 可再次传入本入口(或按
        索引入口)继续推进; draws=0 时返回空轮次与未改变的状态副本, k=0 时
        生成 draws 个空列表并按轮数推进 position、不消耗随机流。不修改入参,
        也不修改传入的状态映射。
    weighted_sample_excluding_checkpoint(items, weights, k, excluded, seed=0,
        start=0)
        排除采样会话的断点创建入口: 接受与 weighted_sample_checkpoint 相同
        的 items、weights、k、seed、start 校验, 并按排除入口的集合语义处理
        excluded(重复位置与排列顺序不影响结果; 结构或成员类型错误抛
        TypeError, 越界位置抛 ValueError), 随后在产生任何状态前完成未排除
        位置的正权重可行性检查。校验通过后先完成 start 个轮次(每轮从同一组
        未排除位置重新开始无放回抽样, 轮次共享 seed 的随机流, start=0 时
        首轮与 weighted_sample_excluding_indices 一致), 再返回当前位置和
        只含 JSON 原生值的可序列化状态; 状态绑定版本、位置、抽样参数(k/n)、
        规范化后的 excluded、items/weights 指纹、标签化 seed、RNG 内部状态
        与抽样计划, 可经 serialize_metrics 与 deserialize_metrics 往返后
        继续恢复。不修改入参, 也不修改 excluded。
    weighted_sample_excluding_resume_indices(items, weights, k, excluded,
        state, draws)
        排除采样会话的按索引恢复入口: 传入与创建断点时相同的 items、
        weights、k、excluded 与状态, 返回 (索引轮次列表, 下一状态)。第一轮
        从断点位置开始, 逐轮等于 weighted_sample_many_excluding_indices
        的零基区间 [pos, pos+draws); 多次续接与一次性生成逐项相同,
        excluded 为空时与 weighted_sample_resume_indices 一致。draws=0
        返回空轮次与不变的状态副本; k=0 时生成 draws 个空轮次、只推进位置
        且不消耗随机流。状态不是映射抛 TypeError; 字段缺失或额外、版本不
        支持、摘要或输入不匹配统一抛 ValueError, 且绝不产生部分轮次;
        其余输入错误沿用既有 TypeError / ValueError。不修改入参与状态。
    weighted_sample_excluding_resume(items, weights, k, excluded, state,
        draws)
        排除采样会话的按元素值恢复入口, 规则与
        weighted_sample_excluding_resume_indices 完全一致(同一套校验
        顺序与异常类别): 每轮按原始位置映射元素值, 返回的下一状态与按索引
        入口逐字段一致, 可再次传入任一恢复入口继续推进。
    serialize_metrics(metrics)
        将指标树稳定序列化为紧凑 JSON 文本, 任意精度整数保持精确十进制。
        字典键先统一转换为成员名文本(str 原样, None->null, bool->true/false,
        int->十进制, 有限 float->编码器数值文本), 再按 Unicode 文本升序排列;
        不同原始键转换得到同一成员名时抛 ValueError。
        值额外支持 decimal.Decimal 与 fractions.Fraction(递归适用于顶层、
        字典值、列表、元组及其嵌套): 有限 Decimal 按其自身十进制表示写成
        不带引号的合法 JSON 数字, 保留精度、指数形式、尾随零与负零符号;
        Fraction 固定写成 [分子, 正分母] 两个精确整数的 JSON 数组(整数
        分数也保留两个元素), 分量不经过浮点。非有限 Decimal(NaN、sNaN、
        正负无穷)抛 ValueError; Decimal / Fraction 仅可作为值, 作为字典
        键按 TypeError 拒绝。
    deserialize_metrics(text)
        serialize_metrics 的逆入口: 把指标序列化文本还原为可继续计算的
        Python 数据树, 供独立数值调用方核对序列化前后的精确数值。只接受
        str(其他类型统一 TypeError); null、布尔值、字符串、数组和对象分别
        还原为 None、bool、str、list 和 dict, 对象成员名保持文本形式与
        文本中的先后次序, 不因排序改变含义。数字解析完全绕开浮点转换:
        没有小数点或指数标记的数字还原为任意精度 int; 带小数点或指数标记
        的有限数字还原为 Decimal —— 即使数值恰好为整数, 也保留正负号、
        刻度、指数与负零。超长整数、极大或极小指数在解释器整数转文本限制
        较低时仍成功并保持精确十进制。serialize_metrics 对 Fraction 产生
        的二元素数组在没有类型标签的现有格式下按普通 list 还原, 不根据
        形状推断类型。允许合法 JSON 的空白与 Unicode 转义; NaN、Infinity、
        -Infinity、语法错误、重复对象成员名, 以及任何无法保持上述精度的
        数字统一抛 ValueError, 错误时不返回部分结果。还原后的数据再次交给
        serialize_metrics 时, 整数和 Decimal 的十进制内容保持精确, 键排序、
        紧凑分隔符、Unicode 输出及既有冲突检测规则继续生效。

权重接受非布尔的 int / float / fractions.Fraction / decimal.Decimal, 并允许
四种类型混合使用; 每个权重按自身精确数值参与抽样。float 必须有限非负;
Decimal 必须有限非负(NaN、sNaN、正负无穷和严格小于零的值都以 ValueError
拒绝, 且 decimal 自身的比较异常不会泄漏), 带符号的零与 0 一样永不入选;
Decimal 以精确十进制值参与(极小正值、超大指数均保持精确比例), 内部与
Fraction 一样统一放大为精确整数后走纯整数抽样路径。

这些函数都在产生任何结果/文本之前完成全部校验, 非法输入以稳定的
TypeError / ValueError 告知调用方, 且不会修改入参。
"""

import collections.abc
import hashlib
import hmac
import json
import math
import numbers
import random
import sys
from decimal import Decimal, InvalidOperation
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

    # ---- 3/4. 权重元素类型与取值 (TypeError / ValueError) ----
    _validate_weight_elements(weights)
    return n


def _validate_weight_elements(weights):
    """权重元素的类型与取值校验 (TypeError / ValueError)。

    与 _validate_sample_inputs 的第 3、4 步完全相同: 布尔值与非实数权重
    抛 TypeError; 负权重、NaN、无穷抛 ValueError。schedule 批量入口对
    每一行权重复用本函数, 保证与单轮入口同一套规则、同一异常类别。
    """
    # ---- 权重类型: 布尔值和非实数权重 (TypeError) ----
    # decimal.Decimal 不注册为 numbers.Real, 但它是精确十进制实数, 这里
    # 与 int / float / Fraction 一视同仁地接受。
    for index, w in enumerate(weights):
        if isinstance(w, bool) or not (
            isinstance(w, numbers.Real) or isinstance(w, Decimal)
        ):
            raise TypeError(
                "weight at index %d must be a real number, not %s"
                % (index, type(w).__name__)
            )

    # ---- 权重取值: NaN / 无穷 / 负数 (ValueError) ----
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
        if isinstance(w, Decimal):
            # 必须在任何比较之前判定: NaN(含 sNaN)与 Decimal 的有序比较会
            # 抛 decimal.InvalidOperation, 该异常绝不能泄漏给调用方。
            # is_nan() 同时覆盖静默 NaN 与 sNaN; is_infinite() 覆盖正负
            # 无穷。判定不经过浮点, 超大指数(如 1E100000)也安全。
            if w.is_nan():
                raise ValueError("weight at index %d must not be NaN" % index)
            if w.is_infinite():
                raise ValueError("weight at index %d must be finite" % index)
            # 合法 Decimal 在此必为有限值; 带符号的零 is_signed() 为真但
            # 数值等于零, 不在这里拒绝, 抽样阶段与 +0 一样永不入选。
            if w < 0:
                raise ValueError("negative weight")
            continue
        if math.isnan(w):
            raise ValueError("weight at index %d must not be NaN" % index)
        if math.isinf(w):
            raise ValueError("weight at index %d must be finite" % index)
        if w < 0:
            raise ValueError("negative weight")


def _validate_draws(draws):
    """批量入口的 draws 必须是非布尔非负整数 (TypeError / ValueError)。"""
    if isinstance(draws, bool) or not isinstance(draws, int):
        raise TypeError("draws must be a non-boolean integer")
    if draws < 0:
        raise ValueError("draws must be non-negative")


def _validate_start(start):
    """批量/流式入口的 start 必须是非布尔非负整数 (TypeError / ValueError)。"""
    if isinstance(start, bool) or not isinstance(start, int):
        raise TypeError("start must be a non-boolean integer")
    if start < 0:
        raise ValueError("start must be non-negative")


def _validate_excluded_positions(excluded, n):
    """校验排除入口的 excluded, 返回排除位置的集合。

    excluded 必须是非文本且长度可确定的序列(与 items / weights 同一结构
    规则), 成员必须是非布尔整数且处于 items 的零基范围 [0, n) 内; 结构或
    成员类型错误抛 TypeError, 越界位置抛 ValueError。排除位置按集合语义
    解释: 重复成员与排列顺序都不影响返回的集合, 也不影响抽样结果。
    调用前 items / weights / k / seed 已通过 _validate_sample_inputs 校验,
    n 为位置总数; 不修改入参。
    """
    if not _is_length_determinable_sequence(excluded):
        raise TypeError("excluded must be a length-determinable sequence")
    positions = set()
    for position in excluded:
        if isinstance(position, bool) or not isinstance(position, int):
            raise TypeError(
                "excluded positions must be non-boolean integers, not %s"
                % type(position).__name__
            )
        if position < 0 or position >= n:
            raise ValueError("excluded position out of range")
        positions.add(position)
    return positions


def _count_positive_weights(weights):
    """统计严格为正的权重个数。

    整数直接判正负, 不经过浮点 —— 超大整数(如 10**400)也是合法有限值;
    浮点 +0.0/-0.0 都不计入, 正的有限浮点才计入。Decimal 的 +0 与带符号
    零(-0)同样不计入。调用前权重已通过类型与取值校验(无 bool / NaN /
    无穷 / 负数)。
    """
    count = 0
    for w in weights:
        if isinstance(w, int):
            if w > 0:
                count += 1
        elif isinstance(w, Decimal):
            # 已排除 NaN / 无穷, 这里的比较不会抛 decimal.InvalidOperation;
            # Decimal('-0') > 0 为 False, 带符号零始终不可选。
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

    每个有限 float 都是分母为 2 的幂的精确分数, int / Fraction / Decimal
    同样精确; 取全部分母的最小公倍数作为统一比例放大后, 所有权重成为精确
    整数, 相对比例逐点保持 —— 正权重仍为正(每个正权重位置保留候选资格,
    哪怕是分子为 1、分母为 10**100 的极小正 Fraction, 或 Decimal('1E-100')
    这样的极小正十进制数), 零权重仍为零(永不被选中, 含 Decimal 的带符号
    零)。用于三种场景: 权重序列包含 Fraction 或 Decimal(杜绝任何 float
    转换把微小正有理数吞成零、或把精确比例舍入; Decimal 与 float 混合时
    直接做加法还会抛 TypeError), 以及浮点求和/累计会溢出的极端输入。
    抽样概率严格等于原始正权重的相对比例。
    """
    fractions = [Fraction(w) for w in pool_weights]
    scale = 1
    for f in fractions:
        scale = math.lcm(scale, f.denominator)
    return [int(f * scale) for f in fractions]


def _contains_fraction(pool_weights):
    return any(isinstance(w, Fraction) for w in pool_weights)


def _contains_decimal(pool_weights):
    return any(isinstance(w, Decimal) for w in pool_weights)


def _select_sampling_plan(pool_weights, k):
    """返回 (抽样用权重, 是否走纯整数精确路径)。

    路径选择规则:
      1. 权重序列中只要出现 Fraction 或 Decimal(可与 int / 有限 float 及
         彼此混合), 就把全部权重按 LCM 统一放大为精确整数后走纯整数路径。
         这样每个精确有理数 / 十进制数都以精确数学值参与抽样: 严格为正的
         Fraction / Decimal(哪怕极小, 如 1E-100)不会因转成 float 而变成
         零, 比例也不被浮点舍入改变, 超大指数(如 1E100000)同样精确;
         且必须先于浮点求和检查 —— Decimal 与 float 混合做加法会直接抛
         TypeError, 任何浮点累计都不可行。
      2. 全整数且累计超 2**53 走纯整数路径(基线规则)。
      3. 总和可正常表示的纯 int / float 输入保持既有浮点路径与锁定序列
         不变。
      4. 浮点求和/累计会溢出(有限浮点权重总和为无穷, 或超大整数与浮点
         混合求和溢出)时, 把权重精确放大为整数后走纯整数路径 —— 只改变
         原本会产生无效或不完整结果的极端场景。
    """
    if k > 0 and (
        _contains_fraction(pool_weights) or _contains_decimal(pool_weights)
    ):
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


def _draw_indices_once_pool(pool, planned_weights, k, rng, use_exact):
    """从固定的未排除位置池出发完成一轮抽样。

    与 _draw_indices_once 相同的"每轮复制后交给抽样器"规则, 区别仅在于
    位置池由调用方预先按 excluded 剔除(保留下来的位置仍携带原始零基
    索引): 每次调用都复制 pool / planned_weights, 抽样器就地弹出只作用
    于副本, 因此每轮都从同一组未排除位置重新开始, 轮次之间恢复全部未
    排除位置; rng 由调用方共享, 多轮连续消耗同一随机流。绝不修改入参。
    """
    if use_exact:
        return _sample_indices_exact_integer(
            list(pool), list(planned_weights), k, rng
        )
    return _sample_indices_float(list(pool), list(planned_weights), k, rng)


def _validate_excluding_batch_inputs(
    items, weights, k, seed, excluded, draws, start
):
    """批量/流式排除入口共用的全部前置校验与抽样准备。

    校验顺序固定: 先 items、weights、k、seed(_validate_sample_inputs),
    再 excluded(_validate_excluded_positions), 最后 draws、start; 随后做
    未排除位置的正权重可行性检查。全部失败都在任何一轮物化之前以稳定的
    TypeError / ValueError 确定抛出, 绝不返回部分结果(即使 draws=0 或
    start 很大也完成全部校验)。通过后返回 (pool, planned_weights,
    use_exact, rng): pool 是按原始顺序保留的未排除位置(携带原始零基
    索引), planned_weights 是按抽样计划(可能经过精确放大)复制出的本地
    权重, rng 已由 seed 初始化但尚未消耗任何轮次 —— start 个轮次的跳过
    由调用方在真正生成前按既有规则进行(k=0 或 draws=0 时不跳过、不消耗
    随机流)。不修改入参。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    excluded_set = _validate_excluded_positions(excluded, n)
    _validate_draws(draws)
    _validate_start(start)

    # 复制到本地并剔除被排除的位置, 绝不修改入参; 保留下来的位置仍携带
    # 原始零基索引, 抽样器记录的 pool[i] 即为原始位置。
    pool = [i for i in range(n) if i not in excluded_set]
    pool_weights = [weights[i] for i in pool]

    # 可行性前置检查: k>0 时未排除位置中的正权重个数必须不少于 k(同时
    # 覆盖可用位置不足的情形), 与单轮排除入口同一判定; k=0 时即使全部
    # 位置被排除或权重全为零也合法。
    if k > 0 and k > _count_positive_weights(pool_weights):
        raise ValueError("no positive weight")

    rng = random.Random(seed)
    planned_weights, use_exact = _select_sampling_plan(pool_weights, k)
    return pool, planned_weights, use_exact, rng


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


def weighted_sample_excluding_indices(items, weights, k, excluded=(), seed=0):
    """按原始位置排除部分位置后的加权无放回抽样, 返回零基原始索引。

    先完成与 weighted_sample_indices 完全一致的 items、weights、k、seed
    及权重有限性/非负性校验, 再校验 excluded(非文本可确定长度序列, 成员
    为非布尔整数且在 items 零基范围内; 结构或成员类型错误抛 TypeError,
    越界位置抛 ValueError)。随后在未被排除的位置中按权重比例无放回抽取
    k 个不同位置: 被排除的位置即使权重为正也绝不出现, 未排除的零权重位
    置仍永不入选; excluded 按集合语义解释, 重复成员与排列顺序不影响结果。
    excluded 为空时与 weighted_sample_indices 逐项相同(同一随机流、同一
    抽样计划); 相同 (输入, excluded, seed) 唯一确定同一序列。k=0 时仍
    完成全部校验并返回空列表; k>0 而未排除位置中的正权重不足 k 个时,
    在产生任何结果前抛 ValueError。不修改入参。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    excluded_set = _validate_excluded_positions(excluded, n)

    # 复制到本地并剔除被排除的位置, 绝不修改入参; 保留下来的位置仍携带
    # 原始零基索引, 抽样器记录的 pool[i] 即为原始位置。
    pool = [i for i in range(n) if i not in excluded_set]
    pool_weights = [weights[i] for i in pool]

    # 与批量/流式入口相同的可行性前置检查: k>0 时未排除位置中的正权重
    # 个数必须不少于 k(正权重个数同时覆盖可用位置不足的情形), 在产生
    # 任何结果之前确定抛 ValueError; k=0 时即使全部位置被排除或权重
    # 全为零也合法。
    if k > 0 and k > _count_positive_weights(pool_weights):
        raise ValueError("no positive weight")

    rng = random.Random(seed)
    planned_weights, use_exact = _select_sampling_plan(pool_weights, k)
    # 抽样器会就地弹出已选位置, 传入本地副本; excluded 为空时 pool 即
    # range(n)、pool_weights 即权重复制, 与 weighted_sample_indices 的
    # 随机流消耗和结果逐项一致。
    if use_exact:
        return _sample_indices_exact_integer(
            list(pool), list(planned_weights), k, rng
        )
    return _sample_indices_float(list(pool), list(planned_weights), k, rng)


def weighted_sample_excluding(items, weights, k, excluded=(), seed=0):
    """weighted_sample_excluding_indices 的元素值入口: 规则、校验顺序与
    异常类别完全一致, 返回按抽取顺序排列的元素值列表, 与索引入口逐项对应
    (相同值的不同位置仍按位置独立处理)。"""
    indices = weighted_sample_excluding_indices(items, weights, k, excluded, seed)
    return [items[i] for i in indices]


def weighted_sample_many_indices(items, weights, k, draws, seed=0, start=0):
    """weighted_sample_indices 的批量入口: 一次调用生成 draws 轮样本。

    返回长度等于 draws 的外层序列, 每个元素是一轮按抽样先后排列的零基
    原始索引。每轮都从原始位置重新开始(同一轮内位置最多出现一次, 轮次
    之间允许再次选中同一位置); 所有轮次共享同一个由 seed 初始化的随机
    流, 第一轮与 weighted_sample_indices 逐项相同, 后续轮次继续消耗该
    流, 相同调用下得到相同的嵌套序列。seed=None 保留现有随机语义。

    可选的 start(默认 0)表示先从该 seed 对应的轮次流开始跳过 start 个
    完整轮次 —— 跳过只消耗同一条确定性随机流, 不改变任何选择规则 ——
    再生成 draws 轮; 因此返回值与 start=0 的完整调用结果按零基区间
    [start, start+draws) 切片逐项一致。start 只接受非布尔整数(其他类型
    抛 TypeError), 负数抛 ValueError; start=0 时行为与既有公开结果完全
    相同。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    _validate_draws(draws)
    _validate_start(start)

    # 可行性前置检查: 每轮无放回抽取 k 个位置, 至少需要 k 个正权重位置
    # (k=0 时即使权重全为零也合法)。在开始任何一轮抽样之前判定, 保证
    # 非法调用确定抛 ValueError 且绝不返回部分外层结果 —— 即使 draws
    # 为 0 或 start 很大也不例外。
    if k > 0 and k > _count_positive_weights(weights):
        raise ValueError("no positive weight")

    pool_weights = list(weights)
    rng = random.Random(seed)
    pool_weights, use_exact = _select_sampling_plan(pool_weights, k)

    # 先跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流, 因此
    # 后续轮次与 start=0 的完整调用按区间切片逐项一致。k=0 的轮次不消耗
    # 随机流, draws=0 时跳过与否不影响空结果, 两种情形都无需空转。
    if k > 0 and draws > 0:
        for _ in range(start):
            _draw_indices_once(n, pool_weights, k, rng, use_exact)

    rounds = []
    for _ in range(draws):
        rounds.append(
            _draw_indices_once(n, pool_weights, k, rng, use_exact)
        )
    return rounds


def weighted_sample_many(items, weights, k, draws, seed=0, start=0):
    """weighted_sample 的批量入口, 规则与 weighted_sample_many_indices
    完全一致(含 start 窗口语义), 区别仅在于每轮返回元素值而非原始索引;
    两个批量入口逐轮逐项对应。
    """
    rounds = weighted_sample_many_indices(items, weights, k, draws, seed, start)
    return [[items[i] for i in round_indices] for round_indices in rounds]


def _validate_schedule_inputs(items, weights_schedule, k, draws, seed, start):
    """weighted_sample_schedule(_indices) 共用的全部前置校验, 返回位置数 n。

    校验顺序固定: 先 items、k、seed(与既有采样入口同一套结构/类型规则),
    再 weights_schedule 及其每一行的结构(非文本且长度可确定的序列,
    TypeError), 然后 draws、start(非布尔非负整数); 随后 k 的取值范围、
    每一行长度与 items 一致、窗口 [start, start+draws) 不超出 schedule
    范围(ValueError); 接着对每一行权重做与单轮入口完全相同的元素类型
    (TypeError)与取值(ValueError)校验; 最后对每一行做 k>0 时的正权重
    可行性检查(ValueError)。全部校验在产生任何一轮之前完成, draws=0
    也不例外; 不修改入参。
    """
    # ---- 1. 结构与参数类型 (TypeError) ----
    if not _is_length_determinable_sequence(items):
        raise TypeError("items must be a length-determinable sequence")
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be a non-boolean integer")
    if not isinstance(seed, _SEED_TYPES):
        raise TypeError("unsupported seed type: %s" % type(seed).__name__)
    if not _is_length_determinable_sequence(weights_schedule):
        raise TypeError(
            "weights_schedule must be a length-determinable sequence"
        )
    for row in weights_schedule:
        if not _is_length_determinable_sequence(row):
            raise TypeError(
                "weights_schedule rows must be length-determinable sequences"
            )
    _validate_draws(draws)
    _validate_start(start)

    # ---- 2. 抽样数量、行长度与窗口范围 (ValueError) ----
    n = len(items)
    if k < 0 or k > n:
        raise ValueError("invalid sample size")
    for row in weights_schedule:
        if len(row) != n:
            raise ValueError("invalid sample size")
    if start + draws > len(weights_schedule):
        raise ValueError("schedule window out of range")

    # ---- 3. 每一行的权重元素类型与取值 (TypeError / ValueError) ----
    for row in weights_schedule:
        _validate_weight_elements(row)

    # ---- 4. 每一行的正权重可行性 (ValueError) ----
    # k>0 时任一行的正权重位置都必须不少于 k 个, 在产生任何一轮之前确定;
    # k=0 时即使某行权重全为零也合法。
    if k > 0:
        for row in weights_schedule:
            if k > _count_positive_weights(row):
                raise ValueError("no positive weight")
    return n


def weighted_sample_schedule_indices(
    items, weights_schedule, k, draws, seed=0, start=0
):
    """按轮次变化权重的批量入口: 一次调用生成 draws 轮样本, 每轮使用
    schedule 中对应行的权重。

    weights_schedule 是有限非文本序列, 成员均为与 items 等长的权重序列;
    第 start+j 轮(零基)使用 weights_schedule[start+j]。返回长度等于
    draws 的外层 list, 每个元素是一轮按抽样先后排列的零基原始索引。
    每轮都从全部原始位置重新开始(同一轮内位置最多出现一次, 重复值按
    位置区分, 轮次之间允许再次选中同一位置); 所有轮次共享同一个由 seed
    初始化的随机流。start=0 的第一轮与 weighted_sample_indices(items,
    weights_schedule[0], k, seed) 逐项相同; 各行权重完全相同时与
    weighted_sample_many_indices 同参调用逐轮逐项一致。

    可选的 start(默认 0)表示先从该 seed 对应的轮次流开始跳过 start 个
    完整轮次 —— 跳过只消耗同一条确定性随机流(被跳过的第 j 轮同样按
    weights_schedule[j] 的权重与抽样计划消耗), 不改变任何选择规则 ——
    再生成 draws 轮; 结果与 start=0 的完整调用按零基区间
    [start, start+draws) 切片逐项一致。start 只接受非布尔整数(其他类型
    抛 TypeError), 负数抛 ValueError。

    全部校验在返回任何轮次前完成: items、k、seed 沿用既有采样入口规则;
    draws、start 必须是非布尔非负整数; weights_schedule 非长度可确定的
    非文本序列、或任一行不是同类序列时抛 TypeError; 行长度与 items 不
    一致、窗口 [start, start+draws) 超出 schedule 范围、负权重、NaN、
    无穷权重, 或任一行在 k>0 时正权重位置不足 k 个时抛 ValueError。
    权重元素规则与既有入口相同(非布尔 int、有限非负 float、Fraction、
    Decimal, 可混合; 零权重永不被选中; 超大整数、Fraction、Decimal 全程
    不经过浮点)。draws=0 仍完成全部结构、权重与可行性校验并返回空
    list; k=0 时每轮为空 list 且不消耗随机流。seed=None 保留现有随机
    语义。不修改入参与 schedule。
    """
    n = _validate_schedule_inputs(
        items, weights_schedule, k, draws, seed, start
    )

    # draws=0: 全部校验已在上面完成, 直接返回空结果, 不消耗随机流。
    if draws == 0:
        return []

    rng = random.Random(seed)
    # 窗口 [0, start+draws) 内每一轮(含被跳过的轮次)都按自己那一行的
    # 权重选择抽样计划: 每轮复制一份权重, 绝不修改 schedule; 被跳过的
    # 第 j 轮同样按 weights_schedule[j] 的计划消耗随机流, 因此跳过
    # start 个完整轮次与从 0 生成时消耗的随机流完全相同。各行权重完全
    # 相同时每轮的计划也相同, 与 weighted_sample_many_indices 逐轮一致。
    plans = [
        _select_sampling_plan(list(weights_schedule[j]), k)
        for j in range(start + draws)
    ]

    # 先跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流。k=0 的
    # 轮次不消耗随机流, 无需空转 —— 与既有批量入口同一节奏。
    if k > 0:
        for j in range(start):
            planned_weights, use_exact = plans[j]
            _draw_indices_once(n, planned_weights, k, rng, use_exact)

    rounds = []
    for j in range(start, start + draws):
        planned_weights, use_exact = plans[j]
        rounds.append(
            _draw_indices_once(n, planned_weights, k, rng, use_exact)
        )
    return rounds


def weighted_sample_schedule(
    items, weights_schedule, k, draws, seed=0, start=0
):
    """weighted_sample_schedule_indices 的元素值入口: 规则、校验顺序与
    异常类别完全一致, 区别仅在于每轮按相同索引返回元素值列表; 两个
    schedule 入口逐轮逐项对应(相同值的不同位置仍按位置独立处理)。
    """
    rounds = weighted_sample_schedule_indices(
        items, weights_schedule, k, draws, seed, start
    )
    return [[items[i] for i in round_indices] for round_indices in rounds]


def weighted_sample_counts(items, weights, k, draws, seed=0, start=0):
    """weighted_sample_many_indices 的批量频次入口: 直接按原始零基位置
    累计窗口内的选中次数, 免去调用方逐轮遍历。

    接受与 weighted_sample_many_indices 完全相同的 items、weights、k、
    draws、seed、start 语义与固定校验顺序(items/weights/k/seed、draws、
    start, 随后正权重可行性检查), 按同一条由 seed 初始化的随机流先生成
    (并跳过)start 个完整轮次, 再生成 draws 轮; 返回长度等于 items 的
    list, counts[i] 即零基区间 [start, start+draws) 内位置 i 被选中的
    总次数(每轮无放回, 同一位置每轮至多计一次; 相等的元素值仍按不同
    位置分别累计)。因此对相同输入, 本入口与逐轮调用
    weighted_sample_many_indices 后再按位置摊平计数逐项一致 —— 首轮、
    后续轮次、相同种子以及 k=0 时的随机流消耗都与对应索引入口逐项对齐。

    draws=0 或 k=0 返回全零列表(k=0 的轮次不消耗随机流), 但仍完成既有
    全部校验; k>0 而正权重位置不足 k 个时在返回列表前抛 ValueError。
    全部失败都不返回部分计数。计数为任意精度整数, 可直接交给
    serialize_metrics 并经 deserialize_metrics 精确往返。不修改入参。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    _validate_draws(draws)
    _validate_start(start)

    # 与批量索引入口相同的可行性前置检查: 在构造计数列表并生成任何一轮
    # 之前确定失败, 保证绝不返回部分计数(即使 draws=0 或 start 很大)。
    if k > 0 and k > _count_positive_weights(weights):
        raise ValueError("no positive weight")

    pool_weights = list(weights)
    rng = random.Random(seed)
    pool_weights, use_exact = _select_sampling_plan(pool_weights, k)

    counts = [0] * n
    # 与 weighted_sample_many_indices 完全相同的跳过与生成节奏: k=0 的
    # 轮次不消耗随机流, draws=0 时跳过与否都不影响全零结果, 两种情形
    # 都无需空转 —— 计数入口与索引入口的随机流消耗因此逐项对齐。
    if k > 0 and draws > 0:
        for _ in range(start):
            _draw_indices_once(n, pool_weights, k, rng, use_exact)
        for _ in range(draws):
            for position in _draw_indices_once(
                n, pool_weights, k, rng, use_exact
            ):
                counts[position] += 1
    return counts


def weighted_sample_stream_indices(items, weights, k, draws, seed=0, start=0):
    """weighted_sample_many_indices 的按需逐轮入口。

    返回一个可迭代对象, 每次迭代产出一轮按抽样先后排列的零基原始索引
    列表, 共 draws 轮; 对相同输入和种子, 逐轮结果与
    weighted_sample_many_indices(items, weights, k, draws, seed) 返回的
    全部轮次完全一致(第一轮同样与 weighted_sample_indices 逐项相同)。
    每轮都从原始位置重新开始, 轮内不放回, 重复值按位置区分。

    可选的 start(默认 0)与批量入口语义相同: 迭代时先从该 seed 对应的
    轮次流按需跳过 start 个完整轮次(只消耗同一条确定性随机流), 再逐轮
    产出 draws 轮; 转成列表后与 start=0 的完整结果按零基区间
    [start, start+draws) 切片逐项一致。start 只接受非布尔整数(其他类型
    抛 TypeError), 负数抛 ValueError。

    与批量入口不同, 轮次在调用方消费时才逐轮生成, 长批次不必一次物化;
    但全部校验(结构、类型、取值、正权重可行性)都在调用时完成 —— 非法
    输入在调用当场抛出稳定的 TypeError / ValueError, 绝不会延迟到已经
    产出部分轮次之后。draws=0 时仍完成全部校验并返回不产出元素的迭代
    对象; k=0 时每轮产出空列表。不修改入参。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    _validate_draws(draws)
    _validate_start(start)

    # 与批量入口相同的可行性前置检查: 在产生第一轮之前确定失败结果,
    # 保证迭代过程中不会再抛出任何异常。
    if k > 0 and k > _count_positive_weights(weights):
        raise ValueError("no positive weight")

    # 复制到本地, 绝不修改入参。
    pool_weights = list(weights)
    rng = random.Random(seed)
    pool_weights, use_exact = _select_sampling_plan(pool_weights, k)

    def _rounds():
        # 按需跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流。
        # k=0 的轮次不消耗随机流, draws=0 时跳过与否不影响空结果, 两种
        # 情形都无需空转。
        if k > 0 and draws > 0:
            for _ in range(start):
                _draw_indices_once(n, pool_weights, k, rng, use_exact)
        for _ in range(draws):
            yield _draw_indices_once(n, pool_weights, k, rng, use_exact)

    return _rounds()


def weighted_sample_stream(items, weights, k, draws, seed=0, start=0):
    """weighted_sample 的按需逐轮入口, 规则与
    weighted_sample_stream_indices 完全一致(含 start 窗口语义), 区别
    仅在于每轮按相同索引产出元素值列表; 与 weighted_sample_many 的逐轮
    结果完全一致。
    """
    index_stream = weighted_sample_stream_indices(
        items, weights, k, draws, seed, start
    )
    return ([items[i] for i in round_indices] for round_indices in index_stream)


def weighted_sample_many_excluding_indices(
    items, weights, k, excluded, draws, seed=0, start=0
):
    """weighted_sample_excluding_indices 的批量入口: 一次调用生成
    draws 轮"按原始位置排除后"的加权无放回样本。

    返回长度等于 draws 的外层 list, 每个元素是一轮按抽样先后排列的零基
    原始索引。每轮都从同一组未排除位置重新开始(同一轮内位置最多出现
    一次, 轮次之间恢复全部未排除位置、允许再次选中同一位置); 被排除的
    位置即使权重为正也绝不出现, 未排除的零权重位置仍永不入选; 所有轮次
    共享同一个由 seed 初始化的随机流。start=0 时第一轮逐项等于
    weighted_sample_excluding_indices(items, weights, k, excluded, seed);
    excluded 为空时, 全部轮次与 weighted_sample_many_indices 的对应
    零基区间逐项一致(同一随机流、同一抽样计划)。

    可选的 start(默认 0)表示先从该 seed 对应的轮次流开始跳过 start 个
    完整轮次(跳过只消耗同一条确定性随机流), 再生成 draws 轮; 结果与
    start=0 的完整调用按零基区间 [start, start+draws) 切片逐项一致。
    start 只接受非布尔整数(其他类型抛 TypeError), 负数抛 ValueError。

    校验顺序固定: 先 items、weights、k、seed, 再 excluded(非文本可确定
    长度序列, 成员为非布尔整数且在 items 零基范围内, 重复成员与排列
    顺序忽略), 最后 draws、start; 结构或成员类型、k、seed、draws、start
    的类型错误统一抛 TypeError, 长度不符、k 或 draws/start 越界、负数或
    非有限权重、未排除位置正权重不足统一抛 ValueError。全部校验在产生
    任何一轮之前完成, 失败绝不返回部分结果 —— 即使 draws=0 或 start
    很大也不例外。draws=0 返回空 list; k=0 时每轮为空 list, 跳过与生成
    都不消耗随机流。seed=None 保留现有随机语义。不修改入参。
    """
    pool, planned_weights, use_exact, rng = _validate_excluding_batch_inputs(
        items, weights, k, seed, excluded, draws, start
    )

    # 先跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流, 因此
    # 后续轮次与 start=0 的完整调用按区间切片逐项一致。k=0 的轮次不消耗
    # 随机流, draws=0 时跳过与否不影响空结果, 两种情形都无需空转。
    if k > 0 and draws > 0:
        for _ in range(start):
            _draw_indices_once_pool(
                pool, planned_weights, k, rng, use_exact
            )

    rounds = []
    for _ in range(draws):
        rounds.append(
            _draw_indices_once_pool(
                pool, planned_weights, k, rng, use_exact
            )
        )
    return rounds


def weighted_sample_many_excluding(
    items, weights, k, excluded, draws, seed=0, start=0
):
    """weighted_sample_excluding 的批量入口, 规则与
    weighted_sample_many_excluding_indices 完全一致(同一套校验顺序、
    异常类别与 start 窗口语义), 区别仅在于每轮按相同索引返回元素值
    列表; 两个批量排除入口逐轮逐项对应(相同值的不同位置仍按位置独立
    处理)。
    """
    rounds = weighted_sample_many_excluding_indices(
        items, weights, k, excluded, draws, seed, start
    )
    return [[items[i] for i in round_indices] for round_indices in rounds]


def weighted_sample_excluding_counts(
    items, weights, k, excluded, draws, seed=0, start=0
):
    """weighted_sample_many_excluding_indices 的批量频次入口: 直接按原始
    零基位置累计窗口内的选中次数, 免去调用方逐轮遍历。

    接受与 weighted_sample_many_excluding_indices 完全相同的 items、
    weights、k、excluded、draws、seed、start 语义与固定校验顺序
    (items/weights/k/seed、excluded、draws、start, 随后未排除位置的
    正权重可行性检查; excluded 按集合语义解释, 重复成员与排列顺序忽略)。
    按同一条由 seed 初始化的随机流先生成(并跳过)start 个完整轮次,
    再生成 draws 轮; 返回长度等于 items 的 list, counts[i] 即零基区间
    [start, start+draws) 内位置 i 被选中的总次数。被排除位置的计数始终
    为零(即使其权重为正), 其余位置按"每轮重新开始的同一组未排除位置
    池"累计, 未排除的零权重位置仍永不入选; 相等的元素值仍按不同位置
    分别累计。因此对相同输入, 本入口与逐轮调用
    weighted_sample_many_excluding_indices 后再按位置摊平计数逐项一致
    —— 首轮、后续轮次、相同种子以及 k=0 时的随机流消耗都与对应索引
    入口逐项对齐。

    draws=0 或 k=0 返回全零列表(k=0 的轮次不消耗随机流), 但仍完成既有
    全部校验(含 excluded 与未排除位置的正权重可行性检查); k>0 而未排除
    位置中的正权重不足 k 个时在返回列表前抛 ValueError。全部失败都不
    返回部分计数。计数为任意精度整数, 可直接交给 serialize_metrics 并经
    deserialize_metrics 精确往返。不修改入参, 也不修改 excluded。
    """
    pool, planned_weights, use_exact, rng = _validate_excluding_batch_inputs(
        items, weights, k, seed, excluded, draws, start
    )

    counts = [0] * len(items)
    # 与 weighted_sample_many_excluding_indices 完全相同的跳过与生成
    # 节奏: k=0 的轮次不消耗随机流, draws=0 时跳过与否都不影响全零
    # 结果, 两种情形都无需空转 —— 计数入口与索引入口的随机流消耗因此
    # 逐项对齐。抽样器只返回未排除的原始位置, 被排除位置在 counts 中
    # 自然始终保持为零。
    if k > 0 and draws > 0:
        for _ in range(start):
            _draw_indices_once_pool(
                pool, planned_weights, k, rng, use_exact
            )
        for _ in range(draws):
            for position in _draw_indices_once_pool(
                pool, planned_weights, k, rng, use_exact
            ):
                counts[position] += 1
    return counts


def weighted_sample_stream_excluding_indices(
    items, weights, k, excluded, draws, seed=0, start=0
):
    """weighted_sample_many_excluding_indices 的按需逐轮入口。

    返回一个可迭代对象, 每次迭代产出一轮按抽样先后排列的零基原始索引
    列表, 共 draws 轮; 对相同输入和种子, 转成列表后与
    weighted_sample_many_excluding_indices(...) 的全部轮次完全一致,
    start=0 时第一轮同样与 weighted_sample_excluding_indices 逐项相同;
    excluded 为空时与 weighted_sample_stream_indices 逐轮一致。每轮都
    从同一组未排除位置重新开始, 轮内不放回, 轮间恢复全部未排除位置,
    重复值按位置区分。

    可选的 start(默认 0)与批量入口语义相同: 迭代时先从该 seed 对应的
    轮次流按需跳过 start 个完整轮次(只消耗同一条确定性随机流), 再逐轮
    产出 draws 轮。start 只接受非布尔整数(其他类型抛 TypeError),
    负数抛 ValueError。

    与批量入口不同, 轮次在调用方消费时才逐轮生成, 长批次不必一次物化;
    但全部参数与可行性错误(结构、成员类型、k、seed、excluded、draws、
    start 的类型与取值, 以及未排除位置正权重不足)都在创建时完成校验 —
    非法输入在调用当场抛出稳定的 TypeError / ValueError, 绝不会延迟到
    已经产出部分轮次之后。draws=0 时仍完成全部校验并返回不产出元素的
    迭代对象; k=0 时每轮产出空列表, 跳过轮次不消耗随机流。不修改入参。
    """
    pool, planned_weights, use_exact, rng = _validate_excluding_batch_inputs(
        items, weights, k, seed, excluded, draws, start
    )

    def _rounds():
        # 按需跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流。
        # k=0 的轮次不消耗随机流, draws=0 时跳过与否不影响空结果, 两种
        # 情形都无需空转。
        if k > 0 and draws > 0:
            for _ in range(start):
                _draw_indices_once_pool(
                    pool, planned_weights, k, rng, use_exact
                )
        for _ in range(draws):
            yield _draw_indices_once_pool(
                pool, planned_weights, k, rng, use_exact
            )

    return _rounds()


def weighted_sample_stream_excluding(
    items, weights, k, excluded, draws, seed=0, start=0
):
    """weighted_sample_excluding 的按需逐轮入口, 规则与
    weighted_sample_stream_excluding_indices 完全一致(同一套创建时
    校验与 start 窗口语义), 区别仅在于每轮按相同索引产出元素值列表;
    与 weighted_sample_many_excluding 的逐轮结果完全一致。
    """
    index_stream = weighted_sample_stream_excluding_indices(
        items, weights, k, excluded, draws, seed, start
    )
    return ([items[i] for i in round_indices] for round_indices in index_stream)


# ---------------------------------------------------------------------------
# 可暂停 / 恢复的采样会话
# ---------------------------------------------------------------------------

# 状态格式版本: 状态结构发生不兼容变化时递增; 恢复时只接受当前版本。
_CHECKPOINT_VERSION = 1


def _hash_text(text):
    """对文本取 sha256, 返回与 json.loads 往返一致的 hexdigest 字符串。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _weight_fingerprint_text(index, weight):
    """把单个权重规范化为参与指纹计算的文本行。

    行首的类型标签保证不同类型的同值权重(如 1 与 1.0、Decimal('1') 与
    Fraction(1, 1))不被视为同一输入 —— 它们可能走不同抽样路径; 同类型
    同值才逐字相同。判定只针对已通过 _validate_sample_inputs 的权重
    (非 bool、int/float/Fraction/Decimal、有限非负), 不会触发 decimal
    比较异常; Fraction 与大整数全程按精确有理值/十进制值处理, 不经过
    浮点, 超大 Decimal 指数同样安全。
    """
    if isinstance(weight, bool):  # 防御性: bool 已在输入校验中拒绝
        return "%d:b:%d" % (index, int(weight))
    if isinstance(weight, int):
        return "%d:i:%s" % (index, _int_to_decimal_text(weight))
    if isinstance(weight, Fraction):
        return "%d:f:%s/%s" % (
            index,
            _int_to_decimal_text(weight.numerator),
            _int_to_decimal_text(weight.denominator),
        )
    if isinstance(weight, Decimal):
        return "%d:d:%s" % (index, str(Decimal(weight)))
    # 有限非负 float: repr 文本对 -0.0 保留符号, 且 repr/eval 往返精确
    # 还原同一二进制浮点值。
    return "%d:r:%s" % (index, float.__repr__(weight))


def _weights_fingerprint(weights):
    """对整个权重序列取指纹: 逐位置规范化后整体 sha256。"""
    body = "\n".join(
        _weight_fingerprint_text(i, w) for i, w in enumerate(weights)
    )
    return _hash_text(body)


def _items_fingerprint(items):
    """对 items 取指纹。

    items 的元素类型不受采样入口约束(可以是任意对象), 故不能假定其可
    JSON 化; 指纹用于检测传入 items 是否与创建断点时逐位置一致(类型与
    值的 repr 均参与), 跨进程恢复时调用方须自行保证传入相同 items —
    状态本身不承载 items 内容。
    """
    digest = hashlib.sha256()
    for i, item in enumerate(items):
        digest.update(
            ("%d:%s:%r\n" % (i, type(item).__qualname__, item)).encode(
                "utf-8", "backslashreplace"
            )
        )
    return digest.hexdigest()


def _seed_to_tagged_value(seed):
    """把支持的 seed 类型编码为只含 JSON 原生值的标签化结构。

    标签: n=None; i=int(含 bool, 用第三元素 true 单独标记以免被 int
    吞掉); f=float; s=str; b=bytes; y=bytearray。float 的 NaN / ±Inf
    不是合法 JSON 值, 用文本 nan/inf/-inf 保留; -0.0 直接以 JSON 数值
    -0.0 保留符号。bytes/bytearray 用 latin-1 对 0..255 双向无损编码。
    """
    if seed is None:
        return ["n", None]
    if isinstance(seed, bool):
        return ["i", 1 if seed else 0, True]
    if isinstance(seed, int):
        return ["i", seed]
    if isinstance(seed, float):
        if math.isnan(seed):
            return ["f", "nan"]
        if math.isinf(seed):
            return ["f", "inf" if seed > 0 else "-inf"]
        return ["f", seed]
    if isinstance(seed, str):
        return ["s", seed]
    if isinstance(seed, bytes):
        return ["b", seed.decode("latin-1")]
    # bytearray
    return ["y", bytes(seed).decode("latin-1")]


def _tagged_value_to_seed(value):
    """_seed_to_tagged_value 的逆运算; 非法结构统一抛 ValueError。"""
    if not isinstance(value, list) or not value \
            or not isinstance(value[0], str):
        raise ValueError("invalid checkpoint seed encoding")
    tag = value[0]
    if tag == "n":
        if len(value) != 2 or value[1] is not None:
            raise ValueError("invalid checkpoint seed encoding")
        return None
    if tag == "i":
        number = value[1] if len(value) in (2, 3) else None
        if isinstance(number, bool) or not isinstance(number, int):
            raise ValueError("invalid checkpoint seed encoding")
        if len(value) == 2:
            return number
        if len(value) == 3 and value[2] is True and number in (0, 1):
            return bool(number)
        raise ValueError("invalid checkpoint seed encoding")
    if tag == "f":
        if len(value) != 2:
            raise ValueError("invalid checkpoint seed encoding")
        payload = value[1]
        if payload == "nan":
            return float("nan")
        if payload == "inf":
            return float("inf")
        if payload == "-inf":
            return float("-inf")
        if isinstance(payload, bool) or not isinstance(payload, (int, float)):
            raise ValueError("invalid checkpoint seed encoding")
        return float(payload)
    if tag == "s":
        if len(value) != 2 or not isinstance(value[1], str):
            raise ValueError("invalid checkpoint seed encoding")
        return value[1]
    if tag in ("b", "y"):
        if len(value) != 2 or not isinstance(value[1], str):
            raise ValueError("invalid checkpoint seed encoding")
        try:
            raw = value[1].encode("latin-1")
        except UnicodeEncodeError:
            raise ValueError("invalid checkpoint seed encoding")
        return raw if tag == "b" else bytearray(raw)
    raise ValueError("invalid checkpoint seed encoding")


def _rng_state_to_jsonable(state):
    """把 random.Random.getstate() 三元组编码为 JSON 原生结构。

    CPython 的 MT19937 状态为 (3, 625 个整数组成的元组, gauss 缓存):
    缓存为 None 或一个 float。整数(含 32 位无符号值)原样保留, 经
    serialize_metrics 仍是精确十进制; None/有限 float 分别标签化。
    """
    if (not isinstance(state, tuple) or len(state) != 3
            or state[0] != 3 or not isinstance(state[1], tuple)
            or len(state[1]) != 625):
        raise ValueError("invalid checkpoint RNG state")
    if any(isinstance(x, bool) or not isinstance(x, int) for x in state[1]):
        raise ValueError("invalid checkpoint RNG state")
    cached = state[2]
    if cached is None:
        cache = ["n", None]
    elif isinstance(cached, bool) or not isinstance(cached, float):
        raise ValueError("invalid checkpoint RNG state")
    elif not math.isfinite(cached):
        raise ValueError("invalid checkpoint RNG state")
    else:
        cache = ["f", cached]
    return {"v": 3, "mt": list(state[1]), "cached": cache}


def _rng_state_from_jsonable(payload):
    """_rng_state_to_jsonable 的逆运算; 非法结构统一抛 ValueError。"""
    if not isinstance(payload, dict) or set(payload) != {"v", "mt", "cached"}:
        raise ValueError("invalid checkpoint RNG state")
    if payload["v"] != 3 or not isinstance(payload["mt"], list) \
            or len(payload["mt"]) != 625:
        raise ValueError("invalid checkpoint RNG state")
    mt = []
    # MT19937: 前 624 项是 32 位无符号状态字, 末项是下一个位置索引
    # (0..624)。显式校验取值范围, 使被篡改(即使重算了摘要)的越界状态
    # 统一抛 ValueError, 而不是在 random.setstate 中泄漏 OverflowError。
    for pos, x in enumerate(payload["mt"]):
        if isinstance(x, bool) or not isinstance(x, int):
            raise ValueError("invalid checkpoint RNG state")
        if pos < 624:
            if not 0 <= x < (1 << 32):
                raise ValueError("invalid checkpoint RNG state")
        elif not 0 <= x <= 624:
            raise ValueError("invalid checkpoint RNG state")
        mt.append(x)
    encoded = payload["cached"]
    if not isinstance(encoded, list) or len(encoded) != 2:
        raise ValueError("invalid checkpoint RNG state")
    label, raw = encoded
    if label == "n":
        if raw is not None:
            raise ValueError("invalid checkpoint RNG state")
        cached = None
    elif label == "f":
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError("invalid checkpoint RNG state")
        cached = float(raw)
        if not math.isfinite(cached):
            raise ValueError("invalid checkpoint RNG state")
    else:
        raise ValueError("invalid checkpoint RNG state")
    return (3, tuple(mt), cached)


def _checkpoint_binding_digest(seed_tagged, position, k, n,
                               items_digest, weights_digest, exact, rng_payload):
    """把断点各字段绑定为一个防篡改摘要。

    用 serialize_metrics 对字段集合做规范化(键排序、紧凑、任意精度
    整数精确十进制)后再 sha256: 任意对 position / seed / RNG 快照 /
    指纹 / exact 的改动若不重算摘要, 恢复时都会被发现。校验为 O(状态
    大小), 恢复长批次无需从头重放随机流。
    """
    return _hash_text(serialize_metrics({
        "seed": seed_tagged,
        "position": position,
        "k": k,
        "n": n,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "exact": exact,
        "rng": rng_payload,
    }))


def _prepare_validated_session(items, weights, k, seed, start):
    """断点入口共用的前置准备: 与批量入口一致的校验、可行性检查与跳轮。

    返回 (n, planned_weights, use_exact, rng): rng 已由 seed 初始化并
    先消耗 start 个完整轮次(k=0 的轮次不消耗随机流), 其内部状态恰好
    对应批量序列中 "start 轮已完成" 的断点。planned_weights 是按抽样
    计划(可能经过精确放大)复制出的本地权重, 绝不修改入参。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    _validate_start(start)

    # 与批量入口相同的可行性前置检查: 即使只是创建断点, k 超过有效正
    # 权重个数也必须在返回任何状态前确定抛 ValueError。
    if k > 0 and k > _count_positive_weights(weights):
        raise ValueError("no positive weight")

    pool_weights = list(weights)
    rng = random.Random(seed)
    planned_weights, use_exact = _select_sampling_plan(pool_weights, k)

    # 与 weighted_sample_many_indices 的跳过逻辑一致: k=0 不消耗随机流。
    if k > 0:
        for _ in range(start):
            _draw_indices_once(n, planned_weights, k, rng, use_exact)
    return n, planned_weights, use_exact, rng


def weighted_sample_checkpoint(items, weights, k, seed=0, start=0):
    """创建采样会话断点(只含 JSON 原生值的状态映射)。

    校验规则与 weighted_sample_many_indices 完全一致(items、weights、
    k、seed、start 的类型与取值, 以及正权重可行性), 全部通过后把随机
    流推进到已完成 start 轮的位置并快照。返回的状态只含 str/int/bool/
    None/float/list/dict 等 JSON 原生值, 可直接交给 serialize_metrics,
    也可经 json 文本落盘后在另一进程中交给
    weighted_sample_resume_indices 恢复; 不依赖任何进程内对象身份。
    不修改入参。
    """
    n, planned_weights, use_exact, rng = _prepare_validated_session(
        items, weights, k, seed, start
    )
    seed_tagged = _seed_to_tagged_value(seed)
    rng_payload = _rng_state_to_jsonable(rng.getstate())
    items_digest = _items_fingerprint(items)
    weights_digest = _weights_fingerprint(weights)
    state = {
        "version": _CHECKPOINT_VERSION,
        "position": start,
        "k": k,
        "n": n,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "seed": seed_tagged,
        "exact": bool(use_exact),
        "rng": rng_payload,
    }
    state["digest"] = _checkpoint_binding_digest(
        seed_tagged, start, k, n, items_digest, weights_digest,
        bool(use_exact), rng_payload,
    )
    return state


def _normalize_checkpoint_numbers(value):
    """递归把状态 seed/rng 载荷中的 Decimal 替换为等值 float。

    断点状态经 serialize_metrics 序列化后再由 deserialize_metrics 还原时,
    带小数点或指数标记的数字(创建断点时只可能是 float 载荷, 如浮点 seed
    或 RNG 高斯缓存)以 Decimal 出现; serialize_metrics 写出的浮点文本是
    该浮点值的精确十进制表示, float() 往返得到同一二进制浮点值, 因此还原
    后的状态与 json 文本路径解析出的状态可互换。不含 Decimal 时返回原
    对象本身(零开销); 含 Decimal 时构造新结构, 绝不修改入参。Decimal 若
    出现在非法位置, 下游结构化校验仍按既有规则统一抛 ValueError。
    """
    if isinstance(value, Decimal):
        # 有限 Decimal -> float; 超出浮点范围的值(如 1E999)得到 inf, 后续
        # 摘要规范化(serialize_metrics 拒绝非有限浮点)或结构校验会以
        # ValueError 拒绝, 不会泄漏其他异常类型。
        return float(value)
    if isinstance(value, list):
        normalized = None
        for index, element in enumerate(value):
            new_element = _normalize_checkpoint_numbers(element)
            if new_element is not element:
                if normalized is None:
                    normalized = list(value)
                normalized[index] = new_element
        return value if normalized is None else normalized
    if isinstance(value, dict):
        normalized = None
        for key, element in value.items():
            new_element = _normalize_checkpoint_numbers(element)
            if new_element is not element:
                if normalized is None:
                    normalized = dict(value)
                normalized[key] = new_element
        return value if normalized is None else normalized
    return value


def _validate_checkpoint_state(state):
    """校验状态本身的结构与版本, 返回规范化字段。

    调用前须已确认 state 是映射(否则 TypeError 在外层抛出)。字段缺失、
    类型错误、非法取值、版本不支持、多余字段等一切结构问题统一抛
    ValueError。
    """
    required = ("version", "position", "k", "n", "items_digest",
                "weights_digest", "seed", "exact", "rng", "digest")
    if not all(key in state for key in required):
        raise ValueError("invalid checkpoint state: missing fields")
    if set(state) != set(required):
        raise ValueError("invalid checkpoint state: unexpected fields")

    version = state["version"]
    if (isinstance(version, bool) or not isinstance(version, int)
            or version != _CHECKPOINT_VERSION):
        raise ValueError("unsupported checkpoint version: %r" % (version,))
    position = state["position"]
    k = state["k"]
    n = state["n"]
    for name, value in (("position", position), ("k", k), ("n", n)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid checkpoint state: %s" % name)
    if k > n:
        raise ValueError("invalid checkpoint state: k exceeds n")
    if not isinstance(state["exact"], bool):
        raise ValueError("invalid checkpoint state: exact")
    for name in ("items_digest", "weights_digest", "digest"):
        if not isinstance(state[name], str):
            raise ValueError("invalid checkpoint state: %s" % name)

    # 状态可能经 serialize_metrics + deserialize_metrics 还原: 其中的
    # Decimal 载荷先还原为创建时的等值 float, 再解码与核对摘要 —— 两条
    # 文本路径(json / serialize_metrics)解析出的状态因此可互换恢复。
    seed_payload = _normalize_checkpoint_numbers(state["seed"])
    rng_payload = _normalize_checkpoint_numbers(state["rng"])

    # 两个逆运算对内部结构问题统一抛 ValueError。
    seed = _tagged_value_to_seed(seed_payload)
    rng_state = _rng_state_from_jsonable(rng_payload)

    # 绑定摘要: 任何对字段的篡改(位置、seed、RNG 快照、指纹、exact)若不
    # 附带重算的摘要, 都会在这里被发现 —— 因此恢复时不必从头重放随机流。
    expected_digest = _checkpoint_binding_digest(
        seed_payload, position, k, n, state["items_digest"],
        state["weights_digest"], state["exact"], rng_payload,
    )
    if not hmac.compare_digest(expected_digest, state["digest"]):
        raise ValueError("invalid checkpoint state: digest mismatch")
    return position, k, n, state["exact"], seed, rng_state, seed_payload


def _resume_rounds_indices(items, weights, k, state, draws):
    """两个恢复入口共用的已校验核心: 只产出索引轮次与下一状态。

    校验顺序按恢复入口约定固定: 先确认 state 是映射(否则 TypeError),
    再按既有规则校验 draws; 然后校验状态本身的结构/版本/摘要, 用状态携带
    的 seed 完成 items、weights、k 的采样入口校验; 最后核对状态与当前输入
    的绑定(k/n、items 指纹、weights 指纹、抽样计划)。任一失败都在物化任何
    轮次之前抛出既有 TypeError / ValueError(正权重可行性失败同样是
    ValueError); JSON / Decimal / random 层面的意外异常统一收敛为
    ValueError, 绝不以其他类型泄漏。全部通过后直接从 RNG 快照续接, 返回
    (索引轮次, 下一状态); 不修改入参, 也不修改传入的状态映射。
    """
    # 状态结构与版本先校验(ValueError), 取出的 seed 再用于采样输入校验,
    # 保证 _validate_sample_inputs 的 seed 类型规则同样被执行。
    position, state_k, state_n, use_exact, seed, rng_state, seed_payload = (
        _validate_checkpoint_state(state)
    )
    n = _validate_sample_inputs(items, weights, k, seed)

    # 状态与当前采样输入的一致性。
    if state_k != k or state_n != n:
        raise ValueError("checkpoint state does not match items/weights/k")
    if state["items_digest"] != _items_fingerprint(items):
        raise ValueError("checkpoint state does not match items")
    if state["weights_digest"] != _weights_fingerprint(weights):
        raise ValueError("checkpoint state does not match weights")

    # 正权重可行性与抽样计划必须与创建断点时一致; 权重已逐位置指纹核对,
    # 这里重建计划并比对 exact 标志。RNG 快照与 (seed, position) 的绑定
    # 已由状态摘要保证未被篡改, 故恢复直接从快照继续, 无需从头重放。
    if k > 0 and k > _count_positive_weights(weights):
        raise ValueError("no positive weight")
    planned_weights, planned_exact = _select_sampling_plan(list(weights), k)
    if planned_exact != use_exact:
        raise ValueError("invalid checkpoint state: sampling plan mismatch")

    # 全部校验通过后才物化轮次: 直接从快照状态继续, 与批量区间逐轮一致。
    rng = random.Random()
    try:
        rng.setstate(rng_state)
    except ValueError:
        raise
    except Exception as exc:
        # 结构与取值范围已在上游校验; 任何解释器层面的额外拒绝都统一成
        # ValueError, 绝不泄漏其他异常类型, 也不会已产出部分轮次。
        raise ValueError("invalid checkpoint RNG state") from exc
    rounds = []
    for _ in range(draws):
        rounds.append(
            _draw_indices_once(n, planned_weights, k, rng, planned_exact)
        )

    next_state = dict(state)
    next_rng_payload = _rng_state_to_jsonable(rng.getstate())
    next_position = position + draws
    next_state["position"] = next_position
    next_state["rng"] = next_rng_payload
    # seed 载荷使用校验时规范化后的形式: 经 deserialize_metrics 还原的
    # 状态其 Decimal 已回到等值 float, 下一状态因此与 JSON 原生状态链
    # 逐字段一致, 可继续经任一文本路径序列化/解析后再恢复。
    next_state["seed"] = seed_payload
    # 摘要必须随 position / RNG 一并刷新, 否则链式再恢复时会因摘要失配
    # 而失败(其余字段与原状态相同)。
    next_state["digest"] = _checkpoint_binding_digest(
        seed_payload, next_position, k, n,
        state["items_digest"], state["weights_digest"],
        planned_exact, next_rng_payload,
    )
    return rounds, next_state


def weighted_sample_resume_indices(items, weights, k, state, draws):
    """从断点继续产出索引轮次, 返回 (轮次列表, 下一状态)。

    第一轮从断点记录的位置开始; 逐轮结果与
    weighted_sample_many_indices(items, weights, k, draws, seed,
    start=position) 完全一致, 即等于 start=0 完整批量序列的零基区间
    [position, position+draws)。返回前完成与采样入口一致的全部输入
    校验, 并核对状态与 items、weights、k 及 (seed, 位置, RNG 快照)的
    自洽性: 状态不是映射抛 TypeError; 非法状态、不支持的版本、状态与
    输入不匹配统一抛 ValueError; items/weights/k/draws 的错误沿用既有
    TypeError / ValueError。所有失败都在任何轮次物化之前确定, 绝不返回
    部分轮次。draws=0 返回空轮次与位置不变的新状态; k=0 时每轮为空
    列表, 位置仍逐轮加一。不修改入参, 也不修改传入的状态映射。
    """
    # 状态不是映射: TypeError(文档约定的明确分类)。映射前提下的一切
    # 结构/版本/摘要问题在 _validate_checkpoint_state 中统一为 ValueError。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    # draws 的类型/取值规则独立于状态, 先按既有规则校验(TypeError /
    # ValueError), 再解析状态。
    _validate_draws(draws)
    return _resume_rounds_indices(items, weights, k, state, draws)


def weighted_sample_resume(items, weights, k, state, draws):
    """按元素值从断点继续, 返回 (元素值轮次列表, 下一状态)。

    校验顺序按恢复入口约定固定: 调用开始先按现有采样入口完成 items、
    weights、k 的结构、长度、权重取值与范围校验(这部分与 seed 无关;
    state 携带的 seed 其标签化编码与既有种子类型语义随后随 state 一并
    校验), 再按现有恢复入口校验 state 的映射类型、版本、字段集合、摘要、
    随机数状态以及 state 与当前输入的绑定, draws 必须是非布尔非负整数。
    状态不是映射抛 TypeError; 非法状态、版本不支持、状态与输入不匹配、
    正权重不足等一律抛 ValueError; 其余输入错误沿用既有 TypeError /
    ValueError。所有失败都在产生任何轮次之前确定, JSON / Decimal /
    random 的异常不会以其他类型泄漏。

    每轮返回元素值列表, 与 weighted_sample_resume_indices 返回的每轮
    原始位置逐项对应(第 j 个值恰为 items[第 j 个索引]): 相同值的不同
    位置分别消耗, 轮内不会出现重复位置。返回的下一状态与按索引入口产出
    的完全相同(position、RNG 快照、digest 一致), 只含 JSON 原生值,
    可直接再次传入本入口, 或经 serialize_metrics 与 json 解析后继续
    恢复。draws=0 返回空轮次与位置、随机状态不变的状态副本; k=0 时生成
    draws 个空列表并按轮数推进 position, 不消耗随机流。不修改入参,
    也不修改传入的状态映射。
    """
    # 第一步: 先按现有采样入口完成 items、weights、k 的结构、长度、权重
    # 取值与范围校验。这些检查只用到 seed 的类型(0 恒为合法种子), 与
    # seed 的具体值无关; state 中携带的 seed 其编码与类型在下一步状态
    # 校验时由 _tagged_value_to_seed 按既有种子语义核对。因此即使 state
    # 本身已损坏, 非法 items/weights/k 仍优先以采样入口的异常类别报告。
    _validate_sample_inputs(items, weights, k, 0)

    # 第二步: 恢复入口的映射类型检查与 draws 规则(TypeError / ValueError)。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    _validate_draws(draws)

    # 第三步: 状态结构/版本/字段/摘要/RNG、state 与输入绑定(含从状态
    # 解出的 seed 再跑一次采样入口校验)、正权重可行性与抽样计划核对,
    # 全部通过后从 RNG 快照续接产出索引轮次。与按索引入口共用同一个
    # 已校验核心, 因此轮次内容、下一状态、异常类别与其逐项一致;
    # JSON / Decimal / random 异常同样统一收敛为 ValueError。
    index_rounds, next_state = _resume_rounds_indices(
        items, weights, k, state, draws
    )
    # 按每轮原始位置逐项映射为元素值: 相同值的不同位置各自独立映射,
    # 轮内不重复位置这一性质随索引结果原样保留。只读取 items, 不修改入参。
    rounds = [[items[i] for i in round_indices] for round_indices in index_rounds]
    return rounds, next_state


# ---------------------------------------------------------------------------
# 可暂停 / 恢复的排除采样会话
# ---------------------------------------------------------------------------

def _excluding_checkpoint_binding_digest(
    seed_tagged, position, k, n, excluded_list,
    items_digest, weights_digest, exact, rng_payload,
):
    """把排除断点各字段绑定为一个防篡改摘要。

    与 _checkpoint_binding_digest 同一构造(serialize_metrics 规范化后
    sha256), 额外绑定规范化后的 excluded 位置列表: 对排除集合、位置、
    seed、RNG 快照、指纹或 exact 的任何改动若不重算摘要, 恢复时都会被
    发现, 因此恢复长批次无需从头重放随机流。
    """
    return _hash_text(serialize_metrics({
        "seed": seed_tagged,
        "position": position,
        "k": k,
        "n": n,
        "excluded": excluded_list,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "exact": exact,
        "rng": rng_payload,
    }))


def weighted_sample_excluding_checkpoint(
    items, weights, k, excluded, seed=0, start=0
):
    """创建排除采样会话断点(只含 JSON 原生值的状态映射)。

    校验顺序与批量排除入口一致: 先 items、weights、k、seed
    (_validate_sample_inputs), 再 excluded(非文本可确定长度序列, 成员
    为非布尔整数且在 items 零基范围内, 按集合语义解释 —— 重复成员与排列
    顺序不影响结果), 最后 start; 随后在产生任何状态前完成未排除位置的
    正权重可行性检查(k>0 而未排除正权重不足 k 个时抛 ValueError)。
    全部通过后先完成 start 个轮次(每轮从同一组未排除位置重新开始无放回
    抽样, 轮次共享由 seed 初始化的同一随机流, k=0 的轮次不消耗随机流),
    把随机流推进到 "已完成 start 轮" 的位置并快照。

    返回的状态只含 str/int/bool/None/float/list/dict 等 JSON 原生值,
    绑定版本、当前位置(已完成轮次)、k/n、规范化后的 excluded(升序去重
    位置列表)、items 与 weights 指纹、标签化 seed、抽样计划(exact)与
    RNG 内部状态; 可直接交给 serialize_metrics, 经 json 文本落盘或
    deserialize_metrics 还原(甚至跨进程)后仍可交给
    weighted_sample_excluding_resume_indices 恢复, 不依赖任何进程内
    对象身份。excluded 为空时与 weighted_sample_checkpoint 的状态逐字段
    一致(除 excluded 字段本身)。不修改入参, 也不修改 excluded。
    """
    n = _validate_sample_inputs(items, weights, k, seed)
    excluded_set = _validate_excluded_positions(excluded, n)
    _validate_start(start)

    # 复制到本地并剔除被排除的位置, 绝不修改入参; 与批量排除入口相同的
    # 可行性前置检查: 即使只是创建断点, k 超过未排除位置的正权重个数也
    # 必须在返回任何状态前确定抛 ValueError。
    pool = [i for i in range(n) if i not in excluded_set]
    pool_weights = [weights[i] for i in pool]
    if k > 0 and k > _count_positive_weights(pool_weights):
        raise ValueError("no positive weight")

    rng = random.Random(seed)
    planned_weights, use_exact = _select_sampling_plan(pool_weights, k)

    # 与 weighted_sample_many_excluding_indices 的跳过逻辑一致: k=0 的
    # 轮次不消耗随机流; excluded 为空时 pool 即 range(n), 与
    # weighted_sample_checkpoint 消耗的随机流完全相同。
    if k > 0:
        for _ in range(start):
            _draw_indices_once_pool(pool, planned_weights, k, rng, use_exact)

    # 集合语义规范化: 升序去重的位置列表是 excluded 的唯一状态表示。
    excluded_list = sorted(excluded_set)
    seed_tagged = _seed_to_tagged_value(seed)
    rng_payload = _rng_state_to_jsonable(rng.getstate())
    items_digest = _items_fingerprint(items)
    weights_digest = _weights_fingerprint(weights)
    state = {
        "version": _CHECKPOINT_VERSION,
        "position": start,
        "k": k,
        "n": n,
        "excluded": excluded_list,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "seed": seed_tagged,
        "exact": bool(use_exact),
        "rng": rng_payload,
    }
    state["digest"] = _excluding_checkpoint_binding_digest(
        seed_tagged, start, k, n, excluded_list, items_digest,
        weights_digest, bool(use_exact), rng_payload,
    )
    return state


def _validate_excluding_checkpoint_state(state):
    """校验排除断点状态本身的结构与版本, 返回规范化字段。

    调用前须已确认 state 是映射(否则 TypeError 在外层抛出)。字段缺失、
    类型错误、非法取值、版本不支持、多余字段、excluded 不是规范化位置
    列表等一切结构问题统一抛 ValueError。
    """
    required = ("version", "position", "k", "n", "excluded", "items_digest",
                "weights_digest", "seed", "exact", "rng", "digest")
    if not all(key in state for key in required):
        raise ValueError("invalid checkpoint state: missing fields")
    if set(state) != set(required):
        raise ValueError("invalid checkpoint state: unexpected fields")

    version = state["version"]
    if (isinstance(version, bool) or not isinstance(version, int)
            or version != _CHECKPOINT_VERSION):
        raise ValueError("unsupported checkpoint version: %r" % (version,))
    position = state["position"]
    k = state["k"]
    n = state["n"]
    for name, value in (("position", position), ("k", k), ("n", n)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid checkpoint state: %s" % name)
    if k > n:
        raise ValueError("invalid checkpoint state: k exceeds n")
    if not isinstance(state["exact"], bool):
        raise ValueError("invalid checkpoint state: exact")
    for name in ("items_digest", "weights_digest", "digest"):
        if not isinstance(state[name], str):
            raise ValueError("invalid checkpoint state: %s" % name)

    # excluded 在状态中只以规范化形式(升序去重的非布尔整数位置列表, 全部
    # 处于 [0, n))出现; 任何其他结构都视为非法状态。经 json /
    # deserialize_metrics 往返后成员仍是 int, 规范化形式保持不变。
    excluded_list = state["excluded"]
    if not isinstance(excluded_list, list):
        raise ValueError("invalid checkpoint state: excluded")
    for member in excluded_list:
        if (isinstance(member, bool) or not isinstance(member, int)
                or member < 0 or member >= n):
            raise ValueError("invalid checkpoint state: excluded")
    if excluded_list != sorted(set(excluded_list)):
        raise ValueError("invalid checkpoint state: excluded")

    # 状态可能经 serialize_metrics + deserialize_metrics 还原: 其中的
    # Decimal 载荷先还原为创建时的等值 float, 再解码与核对摘要 —— 两条
    # 文本路径(json / serialize_metrics)解析出的状态因此可互换恢复。
    seed_payload = _normalize_checkpoint_numbers(state["seed"])
    rng_payload = _normalize_checkpoint_numbers(state["rng"])

    # 两个逆运算对内部结构问题统一抛 ValueError。
    seed = _tagged_value_to_seed(seed_payload)
    rng_state = _rng_state_from_jsonable(rng_payload)

    # 绑定摘要: 任何对字段的篡改(位置、excluded、seed、RNG 快照、指纹、
    # exact)若不附带重算的摘要, 都会在这里被发现 —— 因此恢复时不必从头
    # 重放随机流。
    expected_digest = _excluding_checkpoint_binding_digest(
        seed_payload, position, k, n, excluded_list, state["items_digest"],
        state["weights_digest"], state["exact"], rng_payload,
    )
    if not hmac.compare_digest(expected_digest, state["digest"]):
        raise ValueError("invalid checkpoint state: digest mismatch")
    return (position, k, n, excluded_list, state["exact"], seed, rng_state,
            seed_payload)


def _resume_excluding_rounds_indices(items, weights, k, excluded, state,
                                     draws):
    """两个排除恢复入口共用的已校验核心: 只产出索引轮次与下一状态。

    校验顺序按恢复入口约定固定: 先确认 state 是映射(否则 TypeError 在外层
    抛出)并按既有规则校验 draws; 然后校验状态本身的结构/版本/摘要, 用状态
    携带的 seed 完成 items、weights、k 的采样入口校验, 再按排除入口规则
    校验 excluded; 最后核对状态与当前输入的绑定(k/n、excluded 集合、items
    指纹、weights 指纹、抽样计划)。任一失败都在物化任何轮次之前抛出既有
    TypeError / ValueError(未排除位置正权重不足同样是 ValueError);
    JSON / Decimal / random 层面的意外异常统一收敛为 ValueError, 绝不以
    其他类型泄漏。全部通过后直接从 RNG 快照续接, 返回 (索引轮次, 下一
    状态); 不修改入参, 也不修改传入的状态映射。
    """
    # 状态结构与版本先校验(ValueError), 取出的 seed 再用于采样输入校验,
    # 保证 _validate_sample_inputs 的 seed 类型规则同样被执行。
    (position, state_k, state_n, state_excluded, use_exact, seed, rng_state,
     seed_payload) = _validate_excluding_checkpoint_state(state)
    n = _validate_sample_inputs(items, weights, k, seed)
    excluded_set = _validate_excluded_positions(excluded, n)

    # 状态与当前采样输入的一致性: excluded 按集合语义比较, 调用方传入的
    # 重复成员与排列顺序不影响判定。
    if state_k != k or state_n != n:
        raise ValueError("checkpoint state does not match items/weights/k")
    if set(state_excluded) != excluded_set:
        raise ValueError("checkpoint state does not match excluded")
    if state["items_digest"] != _items_fingerprint(items):
        raise ValueError("checkpoint state does not match items")
    if state["weights_digest"] != _weights_fingerprint(weights):
        raise ValueError("checkpoint state does not match weights")

    # 未排除位置的正权重可行性与抽样计划必须与创建断点时一致; 权重已逐
    # 位置指纹核对, 这里重建计划并比对 exact 标志。RNG 快照与 (seed,
    # position, excluded) 的绑定已由状态摘要保证未被篡改, 故恢复直接从
    # 快照继续, 无需从头重放。
    pool = [i for i in range(n) if i not in excluded_set]
    pool_weights = [weights[i] for i in pool]
    if k > 0 and k > _count_positive_weights(pool_weights):
        raise ValueError("no positive weight")
    planned_weights, planned_exact = _select_sampling_plan(pool_weights, k)
    if planned_exact != use_exact:
        raise ValueError("invalid checkpoint state: sampling plan mismatch")

    # 全部校验通过后才物化轮次: 直接从快照状态继续, 与批量排除入口的
    # 对应区间逐轮一致。
    rng = random.Random()
    try:
        rng.setstate(rng_state)
    except ValueError:
        raise
    except Exception as exc:
        # 结构与取值范围已在上游校验; 任何解释器层面的额外拒绝都统一成
        # ValueError, 绝不泄漏其他异常类型, 也不会已产出部分轮次。
        raise ValueError("invalid checkpoint RNG state") from exc
    rounds = []
    for _ in range(draws):
        rounds.append(
            _draw_indices_once_pool(pool, planned_weights, k, rng,
                                    planned_exact)
        )

    next_state = dict(state)
    next_rng_payload = _rng_state_to_jsonable(rng.getstate())
    next_position = position + draws
    next_state["position"] = next_position
    next_state["rng"] = next_rng_payload
    # excluded 与 seed 载荷使用校验时规范化后的形式: 经 deserialize_metrics
    # 还原的状态其 Decimal 已回到等值 float, 下一状态因此与 JSON 原生状态
    # 链逐字段一致, 可继续经任一文本路径序列化/解析后再恢复。
    next_state["excluded"] = list(state_excluded)
    next_state["seed"] = seed_payload
    # 摘要必须随 position / RNG 一并刷新, 否则链式再恢复时会因摘要失配
    # 而失败(其余字段与原状态相同)。
    next_state["digest"] = _excluding_checkpoint_binding_digest(
        seed_payload, next_position, k, n, list(state_excluded),
        state["items_digest"], state["weights_digest"],
        planned_exact, next_rng_payload,
    )
    return rounds, next_state


def weighted_sample_excluding_resume_indices(
    items, weights, k, excluded, state, draws
):
    """从排除断点继续产出索引轮次, 返回 (轮次列表, 下一状态)。

    第一轮从断点记录的位置开始; 逐轮结果与
    weighted_sample_many_excluding_indices(items, weights, k, excluded,
    draws, seed, start=position) 完全一致, 即等于 start=0 完整批量排除
    序列的零基区间 [position, position+draws); 多次续接与一次性生成逐项
    相同, excluded 为空时与 weighted_sample_resume_indices 的对应窗口
    一致。返回前完成与采样入口一致的全部输入校验(含 excluded 的集合语义
    校验), 并核对状态与 items、weights、k、excluded 及 (seed, 位置, RNG
    快照)的自洽性: 状态不是映射抛 TypeError; 字段缺失或额外、版本不支持、
    摘要或输入不匹配统一抛 ValueError; items/weights/k/excluded/draws 的
    错误沿用既有 TypeError / ValueError。所有失败都在任何轮次物化之前
    确定, 绝不返回部分轮次。draws=0 返回空轮次与位置不变的状态副本;
    k=0 时每轮为空列表, 位置仍逐轮加一且不消耗随机流。不修改入参,
    也不修改传入的状态映射与 excluded。
    """
    # 状态不是映射: TypeError(文档约定的明确分类)。映射前提下的一切
    # 结构/版本/摘要问题在 _validate_excluding_checkpoint_state 中统一为
    # ValueError。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    # draws 的类型/取值规则独立于状态, 先按既有规则校验(TypeError /
    # ValueError), 再解析状态。
    _validate_draws(draws)
    return _resume_excluding_rounds_indices(
        items, weights, k, excluded, state, draws
    )


def weighted_sample_excluding_resume(
    items, weights, k, excluded, state, draws
):
    """按元素值从排除断点继续, 返回 (元素值轮次列表, 下一状态)。

    校验顺序按恢复入口约定固定: 调用开始先按现有采样入口完成 items、
    weights、k 的结构、长度、权重取值与范围校验(这部分与 seed 无关;
    state 携带的 seed 其标签化编码与既有种子类型语义随后随 state 一并
    校验), 再按排除入口规则校验 excluded, 然后按现有恢复入口校验 state
    的映射类型、版本、字段集合、摘要、随机数状态以及 state 与当前输入的
    绑定, draws 必须是非布尔非负整数。状态不是映射抛 TypeError; 非法
    状态、版本不支持、状态与输入不匹配、未排除位置正权重不足等一律抛
    ValueError; 其余输入错误沿用既有 TypeError / ValueError。所有失败
    都在产生任何轮次之前确定, JSON / Decimal / random 的异常不会以其他
    类型泄漏。

    每轮返回元素值列表, 与 weighted_sample_excluding_resume_indices
    返回的每轮原始位置逐项对应(第 j 个值恰为 items[第 j 个索引]): 相同
    值的不同位置分别消耗, 轮内不会出现重复位置。返回的下一状态与按索引
    入口产出的逐字段一致(position、excluded、RNG 快照、digest 相同),
    只含 JSON 原生值, 可直接再次传入本入口或按索引入口, 或经
    serialize_metrics 与 json 解析后继续恢复。draws=0 返回空轮次与位置、
    随机状态不变的状态副本; k=0 时生成 draws 个空列表并按轮数推进
    position, 不消耗随机流。不修改入参, 也不修改传入的状态映射与
    excluded。
    """
    # 第一步: 先按现有采样入口完成 items、weights、k 的结构、长度、权重
    # 取值与范围校验, 再按排除入口规则校验 excluded。这些检查只用到 seed
    # 的类型(0 恒为合法种子), 与 seed 的具体值无关; state 中携带的 seed
    # 其编码与类型在下一步状态校验时由 _tagged_value_to_seed 按既有种子
    # 语义核对。因此即使 state 本身已损坏, 非法 items/weights/k/excluded
    # 仍优先以采样/排除入口的异常类别报告。
    n = _validate_sample_inputs(items, weights, k, 0)
    _validate_excluded_positions(excluded, n)

    # 第二步: 恢复入口的映射类型检查与 draws 规则(TypeError / ValueError)。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    _validate_draws(draws)

    # 第三步: 状态结构/版本/字段/摘要/RNG、state 与输入绑定(含从状态
    # 解出的 seed 再跑一次采样入口校验与 excluded 集合比对)、正权重可行
    # 性与抽样计划核对, 全部通过后从 RNG 快照续接产出索引轮次。与按索引
    # 入口共用同一个已校验核心, 因此轮次内容、下一状态、异常类别与其
    # 逐项一致; JSON / Decimal / random 异常同样统一收敛为 ValueError。
    index_rounds, next_state = _resume_excluding_rounds_indices(
        items, weights, k, excluded, state, draws
    )
    # 按每轮原始位置逐项映射为元素值: 相同值的不同位置各自独立映射,
    # 轮内不重复位置这一性质随索引结果原样保留。只读取 items, 不修改入参。
    rounds = [[items[i] for i in round_indices] for round_indices in index_rounds]
    return rounds, next_state


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


def _decimal_to_json_number_text(value):
    """把有限 Decimal 精确转换成合法 JSON 数值文本, 全程不经过浮点。

    直接采用 Decimal 自身的十进制表示(str), 因此按值本身保留精度、指数
    形式、尾随零与负零符号(如 "1.50"、"1E+2"、"-0.00"、"-1E-100");
    有限 Decimal 的该文本始终是合法 JSON 数字(数字、小数点、E 指数语法
    完全一致), 故输出不带引号, 由调用方直接拼入 JSON。超大指数(如
    1E100000)同样原样保留, 不受双精度范围限制。剥除 Decimal 子类可能
    自定义的 __str__/__repr__, 结果只取决于十进制值与系数表示。调用前
    value 已经 _check_jsonable 确认为有限值(NaN/sNaN/正负无穷均已先抛
    ValueError), 这里不做任何有序比较, decimal 的比较异常不会泄漏。
    """
    return str(Decimal(value))


def _fraction_to_fixed_array_text(value):
    """把 Fraction 精确写成含两个整数的 JSON 数组文本。

    先放规范化后的分子, 再放恒为正的分母; 整数分数(如 Fraction(2, 1))
    仍保留两个元素。两个分量都走 _int_to_decimal_text, 与超大整数一样
    保持任意位数精确, 全程不经过浮点。剥除 Fraction 子类可能自定义的
    __str__/__repr__, 结果只取决于规范化后的分子/分母。
    """
    fraction = Fraction(value)
    return "[" + _int_to_decimal_text(fraction.numerator) + "," \
        + _int_to_decimal_text(fraction.denominator) + "]"


class _ExactIntegerEncoder(json.JSONEncoder):
    """沿用标准库 JSON 编码器的全部规则, 只替换精确数值的文本生成。

    通过 iterencode(..., _one_shot=False) 强制使用 Python 版
    _make_iterencode, 并注入自定义 _intstr / _decimalstr / _fractionstr:
    字符串转义、float 数值文本(-0.0、指数写法)、None/bool、分隔符、键
    排序、tuple 按数组等行为均与 json.dumps 完全一致。bool 在编码器内部
    先于 int 分派, 不会进入 _intstr, 因此仍输出 true/false。

    与标准库 _make_iterencode 相比, 仅在三个标量分派点(int/float 之后)
    各加一条 Decimal / Fraction 分支: 有限 Decimal 输出不带引号的合法
    JSON 数字文本; Fraction 固定输出 [分子, 正分母] 两个精确整数。字典键
    分派不增加这两个分支 —— Decimal / Fraction 作为键已在校验阶段按
    TypeError 拒绝, 编码器收到的键仍只有 str/int/float/bool/None。
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
        return _build_exact_iterencode(
            markers, self.default, encoder, indent, floatstr,
            self.key_separator, self.item_separator, self.sort_keys,
            self.skipkeys, _one_shot,
            _int_to_decimal_text,
            _decimal_to_json_number_text,
            _fraction_to_fixed_array_text,
        )(o, 0)


# 与标准库 _make_iterencode 平行的工厂: 每次 iterencode 都用当前编码器的
# 配置新建一组递归闭包(markers/分隔符/排序标志均为本次调用私有)。
def _build_exact_iterencode(markers, default, encoder, indent, floatstr,
                            key_separator, item_separator, sort_keys,
                            skipkeys, one_shot, intstr, decimalstr,
                            fractionstr):
    """构造识别 Decimal / Fraction 标量的递归 JSON 编码闭包。

    结构逐段复制标准库 _make_iterencode 的 Python 实现, 仅在列表元素、
    字典值、顶层标量三处的 isinstance(value, float) 分支之后追加 Decimal
    / Fraction 分派; 字典键分派保持原样(只认 str/int/float/bool/None)。
    这样紧凑分隔符、键排序、tuple 按数组、循环引用标记、add_note 上下文
    等可观察行为与标准库完全一致, 只是新增两类精确数值。
    """
    ValueError_ = ValueError
    dict_ = dict
    id_ = id
    isinstance_ = isinstance
    list_ = list
    tuple_ = tuple

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield "[]"
            return
        if markers is not None:
            markerid = id_(lst)
            if markerid in markers:
                raise ValueError_("Circular reference detected")
            markers[markerid] = lst
        buf = "["
        if indent is not None:
            _current_indent_level += 1
            newline_indent = "\n" + indent * _current_indent_level
            separator = item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = item_separator
        for i, value in enumerate(lst):
            if i:
                buf = separator
            try:
                if isinstance_(value, str):
                    yield buf + encoder(value)
                elif value is None:
                    yield buf + "null"
                elif value is True:
                    yield buf + "true"
                elif value is False:
                    yield buf + "false"
                elif isinstance_(value, int):
                    # int/float 子类可覆盖 __repr__, 但仍按数值编码;
                    # 同理 Decimal/Fraction 子类也剥掉自定义文本方法。
                    yield buf + intstr(value)
                elif isinstance_(value, float):
                    yield buf + floatstr(value)
                elif isinstance_(value, Decimal):
                    yield buf + decimalstr(value)
                elif isinstance_(value, Fraction):
                    yield buf + fractionstr(value)
                else:
                    yield buf
                    if isinstance_(value, (list_, tuple_)):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance_(value, dict_):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                    yield from chunks
            except GeneratorExit:
                raise
            except BaseException as exc:
                exc.add_note(
                    "when serializing %s item %d" % (type(lst).__name__, i)
                )
                raise
        if newline_indent is not None:
            _current_indent_level -= 1
            yield "\n" + indent * _current_indent_level
        yield "]"
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield "{}"
            return
        if markers is not None:
            markerid = id_(dct)
            if markerid in markers:
                raise ValueError_("Circular reference detected")
            markers[markerid] = dct
        yield "{"
        if indent is not None:
            _current_indent_level += 1
            newline_indent = "\n" + indent * _current_indent_level
            item_sep = item_separator + newline_indent
        else:
            newline_indent = None
            item_sep = item_separator
        first = True
        if sort_keys:
            items = sorted(dct.items())
        else:
            items = dct.items()
        for key, value in items:
            # 键分派与标准库完全一致: 校验阶段已把 Decimal / Fraction 键
            # 按 TypeError 拒绝, 这里不需要也不能把它们转成成员名。
            if isinstance_(key, str):
                pass
            elif isinstance_(key, float):
                key = floatstr(key)
            elif key is True:
                key = "true"
            elif key is False:
                key = "false"
            elif key is None:
                key = "null"
            elif isinstance_(key, int):
                key = intstr(key)
            elif skipkeys:
                continue
            else:
                raise TypeError(
                    "keys must be str, int, float, bool or None, "
                    "not %s" % key.__class__.__name__
                )
            if first:
                first = False
                if newline_indent is not None:
                    yield newline_indent
            else:
                yield item_sep
            yield encoder(key)
            yield key_separator
            try:
                if isinstance_(value, str):
                    yield encoder(value)
                elif value is None:
                    yield "null"
                elif value is True:
                    yield "true"
                elif value is False:
                    yield "false"
                elif isinstance_(value, int):
                    yield intstr(value)
                elif isinstance_(value, float):
                    yield floatstr(value)
                elif isinstance_(value, Decimal):
                    yield decimalstr(value)
                elif isinstance_(value, Fraction):
                    yield fractionstr(value)
                else:
                    if isinstance_(value, (list_, tuple_)):
                        chunks = _iterencode_list(value, _current_indent_level)
                    elif isinstance_(value, dict_):
                        chunks = _iterencode_dict(value, _current_indent_level)
                    else:
                        chunks = _iterencode(value, _current_indent_level)
                    yield from chunks
            except GeneratorExit:
                raise
            except BaseException as exc:
                exc.add_note(
                    "when serializing %s item %r" % (type(dct).__name__, key)
                )
                raise
        if not first and newline_indent is not None:
            _current_indent_level -= 1
            yield "\n" + indent * _current_indent_level
        yield "}"
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance_(o, str):
            yield encoder(o)
        elif o is None:
            yield "null"
        elif o is True:
            yield "true"
        elif o is False:
            yield "false"
        elif isinstance_(o, int):
            yield intstr(o)
        elif isinstance_(o, float):
            yield floatstr(o)
        elif isinstance_(o, Decimal):
            yield decimalstr(o)
        elif isinstance_(o, Fraction):
            yield fractionstr(o)
        elif isinstance_(o, (list_, tuple_)):
            yield from _iterencode_list(o, _current_indent_level)
        elif isinstance_(o, dict_):
            yield from _iterencode_dict(o, _current_indent_level)
        else:
            if markers is not None:
                markerid = id_(o)
                if markerid in markers:
                    raise ValueError_("Circular reference detected")
                markers[markerid] = o
            newobj = default(o)
            try:
                yield from _iterencode(newobj, _current_indent_level)
            except GeneratorExit:
                raise
            except BaseException as exc:
                exc.add_note(
                    "when serializing %s object" % type(o).__name__
                )
                raise
            if markers is not None:
                del markers[markerid]

    return _iterencode


def _check_jsonable(value, on_path):
    """递归确认 value 可被 JSON 表示。

    - 任意大小的 int 原样接受(由 json 以精确十进制输出, 不经过浮点);
    - 有限 Decimal 接受(按自身十进制表示输出为裸 JSON 数字); NaN、sNaN、
      正负无穷一律抛 ValueError, 且先于任何有序比较判定, decimal 的比较
      异常不会泄漏;
    - Fraction 原样接受(有理数不可能为 NaN/无穷), 输出为 [分子, 正分母];
    - NaN / Infinity float 抛 ValueError;
    - 集合、循环引用及其他不可表示的值抛 TypeError; Decimal / Fraction
      仅可作为值, 作为字典键时按 TypeError 拒绝。
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
    if isinstance(value, Decimal):
        # 必须在任何有序比较之前判定: NaN(含 sNaN)与 Decimal 的有序比较
        # 会抛 decimal.InvalidOperation, 该异常绝不能泄漏给调用方。
        # is_nan() 同时覆盖静默 NaN 与 sNaN; is_infinite() 覆盖正负无穷。
        # 判定不经过浮点, 超大指数也安全。
        if value.is_nan():
            raise ValueError("Decimal NaN is not JSON serializable")
        if value.is_infinite():
            raise ValueError("Decimal Infinity is not JSON serializable")
        return
    if isinstance(value, Fraction):
        # Fraction 是精确有理数, 规范化后分母恒为正, 不可能为 NaN/无穷。
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


# ---------------------------------------------------------------------------
# 指标反序列化
# ---------------------------------------------------------------------------

def _decimal_text_to_exact_int(text):
    """把 JSON 整数文本精确转换为任意精度 int, 全程不经过浮点。

    与 _int_to_decimal_text 互为逆运算: CPython 3.11+ 的 int(text) 同样受
    sys.get_int_max_str_digits 限制, 超限直接抛 ValueError。这里按运行时
    当前上限减 1 的固定宽度把十进制文本分块, 每块的 int() 都严格位于限制
    之内, 再按 value = value * 10**块宽 + 块值 逐块累乘, 得到与 int(text)
    完全一致的任意精度整数: 支持任意位数, 负号原样保留。运行时关闭限制
    (上限为 0)或解释器没有该限制时直接使用 int, 与标准库行为一致。
    调用前 text 已由 JSON 扫描器确认为合法整数文本(可选负号后接十进制
    数字, 不含小数点与指数标记)。
    """
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    if _GET_INT_MAX_STR_DIGITS is None:
        value = int(digits)
    else:
        limit = _GET_INT_MAX_STR_DIGITS()
        if limit == 0 or len(digits) <= limit:
            # 常见路径: 位数本就在限制之内, 与 int(text) 完全一致。
            value = int(digits)
        else:
            width = limit - 1
            value = 0
            for start in range(0, len(digits), width):
                chunk = digits[start:start + width]
                value = value * (10 ** len(chunk)) + int(chunk)
    return -value if negative else value


def _decimal_text_to_decimal(text):
    """把带小数点或指数标记的 JSON 数字文本精确转换为 Decimal。

    Decimal 直接按十进制文本构造, 不经过浮点, 因此保留正负号、刻度、
    指数形式与负零(如 "1.50"、"1E+2"、"-0.00"), 且不受
    sys.get_int_max_str_digits 限制 —— 超长系数与极大/极小指数(如
    1E100000)都精确还原。指数超出 decimal 可表示范围(绝对值大于
    MAX_EMAX)时 Decimal 构造抛 decimal.InvalidOperation —— 该异常不是
    ValueError 且绝不能泄漏给调用方: 这类数字无法以精确十进制表示,
    按约定统一收敛为 ValueError。
    调用前 text 已由 JSON 扫描器确认为合法数字文本。
    """
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        raise ValueError(
            "number cannot be represented exactly as Decimal: %r" % text
        )


def _reject_json_constant(text):
    """拒绝 NaN / Infinity / -Infinity: 非有限值不是合法 JSON 数字,
    也无法以精确十进制表示, 统一抛 ValueError。"""
    raise ValueError("non-finite number is not deserializable: %s" % text)


def _pairs_to_dict_no_duplicates(pairs):
    """把对象成员对序列还原为 dict, 保持文本中的成员名与先后次序。

    成员名一律为 str(文本形式); 重复成员名会让后写者静默覆盖先写者,
    破坏序列化前后的精确对应, 按约定统一抛 ValueError, 绝不返回部分
    结果。
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object member name: %r" % key)
        result[key] = value
    return result


def deserialize_metrics(text):
    """把指标序列化文本还原为可继续计算的 Python 数据树。

    参数只接受 str, 其他类型(包括 bytes / bytearray)统一抛 TypeError。
    返回值按 JSON 结构还原: null -> None, true/false -> bool, 字符串 ->
    str(允许 Unicode 转义), 数组 -> list, 对象 -> dict(成员名保持文本
    形式与文本中的先后次序)。数字解析完全绕开浮点: 没有小数点或指数
    标记的数字返回任意精度 int; 带小数点或指数标记的有限数字返回
    Decimal, 保留正负号、刻度、指数与负零。NaN / Infinity / -Infinity、
    语法错误、重复对象成员名, 以及任何无法保持上述精度的数字统一抛
    ValueError; 解析要么完整成功, 要么整体失败, 绝不返回部分结果。
    """
    if not isinstance(text, str):
        raise TypeError(
            "metrics text must be a str, not %s" % type(text).__name__
        )
    # json 扫描器负责 JSON 语法(空白、转义、结构), 其 JSONDecodeError
    # 本身是 ValueError 的子类, 语法错误天然归入约定的异常分类; 数字与
    # 对象成员则全部由上面的精确钩子接管, 不经过任何浮点转换。
    return json.loads(
        text,
        parse_int=_decimal_text_to_exact_int,
        parse_float=_decimal_text_to_decimal,
        parse_constant=_reject_json_constant,
        object_pairs_hook=_pairs_to_dict_no_duplicates,
    )
