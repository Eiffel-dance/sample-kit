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
    weighted_sample_schedule_counts(items, weights_schedule, k, draws,
        seed=0, start=0)
        weighted_sample_schedule_indices 的批量频次入口: 接受与该入口
        相同的参数语义与固定校验顺序, 按同一随机流(每轮同一权重行与
        同一抽样计划)生成窗口内的轮次, 返回长度等于 items 的整数 list
        counts, counts[i] 是零基区间 [start, start+draws) 中原始位置 i
        被选中的次数(每轮无放回, 相等的元素值仍按不同位置分别累计)。
        结果等于把 weighted_sample_schedule_indices 对应窗口的全部轮次
        按位置摊平计数; start 只跳过前置完整轮次并保持窗口切片语义。
        draws=0 或 k=0 返回全零列表(仍完成全部校验, k=0 不消耗随机流),
        任何失败都不给出部分计数。计数为任意精度整数, 可直接交给
        serialize_metrics 并经 deserialize_metrics 精确往返。不修改入参
        与 weights_schedule。
    weighted_sample_schedule_stream_indices(items, weights_schedule, k, draws,
        seed=0, start=0)
        weighted_sample_schedule_indices 的按需逐轮入口: 返回一个可迭代
        对象, 调用方逐轮取得与批量入口完全一致的轮次(每轮一份按抽样先后
        排列的零基原始索引列表), 不必一次物化全部 draws 轮。全部参数与
        可行性校验都在创建时完成并当场抛出(结构、行长、窗口范围、权重
        类型与取值、每轮正权重可行性, draws=0 或 k=0 也不省略), 不会
        延迟到已经产出部分轮次之后; start 在迭代时按需跳过完整轮次,
        被跳过的第 j 轮同样按 weights_schedule[j] 的权重与抽样计划消耗
        同一条随机流。k=0 时每轮产出空列表且不消耗随机流, draws=0 返回
        不产出元素的可迭代对象。不修改入参与 weights_schedule。
    weighted_sample_schedule_stream(items, weights_schedule, k, draws,
        seed=0, start=0)
        与 weighted_sample_schedule_stream_indices 同规则(同一套创建时
        校验与 start 窗口语义), 但每轮按相同索引产出元素值列表, 与
        weighted_sample_schedule 逐轮对应。
    weighted_sample_k_schedule_indices(items, weights, k_schedule, draws,
        seed=0, start=0)
        按轮样本数计划的批量入口: k_schedule 是有限非文本序列, 成员均为
        非布尔非负整数且不超过 items 长度; 第 start+j 轮(零基)使用
        k_schedule[start+j] 作为该轮样本数, 轮内按固定 weights 加权无放回
        抽取。返回 draws 轮, 每轮是按抽样先后排列的零基原始索引; 每轮从
        全部位置重新开始, 重复值按位置区分。所有轮共享由 seed 初始化的
        一条随机流; start 只跳过完整轮次并消耗与从 0 生成时相同的随机流,
        样本数为零的轮次返回空列表且不消耗随机流。计划中各项都等于 k 时
        与 weighted_sample_many_indices 同参调用逐轮完全一致。校验在返回
        任何轮次前完成: k_schedule 结构或成员类型错误抛 TypeError; 成员
        为负或超过位置数、窗口超出计划范围、权重非法, 或任一轮样本数超过
        正权重位置数时抛 ValueError; draws=0 仍完成全部校验并返回空列表。
        不修改入参与 k_schedule。
    weighted_sample_k_schedule(items, weights, k_schedule, draws, seed=0,
        start=0)
        与 weighted_sample_k_schedule_indices 同规则(同一套校验顺序与
        异常类别), 但每轮按相同索引返回元素值列表, 两个入口逐轮逐项对应;
        计划中各项都等于 k 时与 weighted_sample_many 逐轮完全一致。
    weighted_sample_k_schedule_stream_indices(items, weights, k_schedule,
        draws, seed=0, start=0)
        weighted_sample_k_schedule_indices 的按需逐轮入口: 返回一个可迭代
        对象, 调用方逐轮取得与批量入口完全一致的轮次, 不必一次物化全部
        draws 轮。全部参数与可行性校验都在创建时完成并当场抛出, 不会延迟
        到已经产出部分轮次之后; start 在迭代时按需跳过完整轮次。
    weighted_sample_k_schedule_stream(items, weights, k_schedule, draws,
        seed=0, start=0)
        与 weighted_sample_k_schedule_stream_indices 同规则(同一套创建时
        校验与 start 窗口语义), 但每轮按相同索引产出元素值列表, 与
        weighted_sample_k_schedule 逐轮对应。
    weighted_sample_k_schedule_counts(items, weights, k_schedule, draws,
        seed=0, start=0)
        weighted_sample_k_schedule_indices 的批量频次入口: 接受与该入口
        相同的参数语义与固定校验顺序, 按同一随机流生成窗口内的轮次, 返回
        长度等于 items 的整数 list counts, counts[i] 是零基区间
        [start, start+draws) 中原始位置 i 被选中的次数(每轮无放回, 相等
        的元素值仍按不同位置分别累计)。结果等于把
        weighted_sample_k_schedule_indices 对应窗口的全部轮次按位置摊平
        计数。draws=0 返回全零列表(仍完成全部校验), 任何失败都不给出
        部分计数。计数为任意精度整数, 可直接交给 serialize_metrics 并经
        deserialize_metrics 精确往返。不修改入参与 k_schedule。
    weighted_sample_plan_indices(items, weights_schedule, k_schedule, draws,
        seed=0, start=0)
        按轮权重与样本数联合计划的批量入口: weights_schedule 与
        k_schedule 是等长的有限非文本序列, 前者每行与 items 等长, 后者
        成员均为非布尔非负整数且不超过 items 长度; 第 start+j 轮(零基)
        同时使用 weights_schedule[start+j] 的权重行与 k_schedule[start+j]
        的样本数, 在位置中按权重无放回抽取。返回 draws 轮, 每轮是按抽样
        先后排列的零基原始索引; 每轮从全部位置重新开始, 轮内无放回,
        重复值按位置区分, 轮间恢复全部位置。所有轮共享由 seed 初始化的
        一条随机流; start 只跳过完整轮次并消耗与从 0 生成时相同的随机流,
        结果与 start=0 的完整调用按零基区间 [start, start+draws) 切片
        逐项一致, 样本数为零的轮次返回空列表且不消耗随机流。权重各行
        相同且计划各项都等于 k 时与 weighted_sample_many_indices 同参
        完全一致。校验在返回任何轮次前完成: 两个计划或任一行结构非法、
        计划成员类型错误抛 TypeError; 行长度不等于 items、计划成员为负
        或超过位置数、两个计划不等长、窗口超出计划范围、负权重、NaN、
        无穷权重, 或任一轮样本数超过对应行正权重位置数时抛 ValueError;
        draws=0 仍完成全部校验并返回空列表。不修改入参与两个计划。
    weighted_sample_plan(items, weights_schedule, k_schedule, draws, seed=0,
        start=0)
        与 weighted_sample_plan_indices 同规则(同一套校验顺序与异常
        类别), 但每轮按相同索引返回元素值列表, 两个入口逐轮逐项对应。
    weighted_sample_plan_counts(items, weights_schedule, k_schedule, draws,
        seed=0, start=0)
        weighted_sample_plan_indices 的批量频次入口: 接受与该入口相同的
        参数语义与固定校验顺序, 按同一随机流(每轮同一权重行、同一样本数
        与同一抽样计划)生成窗口内的轮次, 返回长度等于 items 的整数 list
        counts, counts[i] 是零基区间 [start, start+draws) 中原始位置 i
        被选中的次数(每轮无放回, 相等的元素值仍按不同位置分别累计)。
        结果等于把 weighted_sample_plan_indices 对应窗口的全部轮次按
        位置摊平计数。draws=0 返回全零列表(仍完成全部校验), 任何失败
        都不给出部分计数。计数为任意精度整数, 可直接交给
        serialize_metrics 并经 deserialize_metrics 精确往返。不修改入参
        与两个计划。
    weighted_sample_k_schedule_checkpoint(items, weights, k_schedule,
        seed=0, start=0)
        创建按轮样本数计划采样会话的断点: 沿用 weighted_sample_k_schedule_
        indices 的全部规则与固定校验顺序(items、weights、k_schedule、
        seed、start; k_schedule 必须是有限非文本序列, 每项为非布尔非负
        整数且不超过 items 长度, 权重接受 int/float/Fraction/Decimal 并
        拒绝负数、NaN、无穷与错误结构, 任一轮样本数超过正权重位置数也
        拒绝), start 越过计划长度抛 ValueError; draws 恒按 0 处理, 创建
        时不产出轮次。校验通过后先完成 start 个完整轮次(被跳过的第 j 轮
        按 k_schedule[j] 的样本数消耗同一条由 seed 初始化的随机流, 样本数
        为零的轮次不消耗随机流), 再返回只含 JSON 原生值的状态映射; 状态
        绑定版本、kind、position、n、计划长度、items / weights /
        k_schedule 指纹、标签化 seed、抽样路径标记、随机流快照与完整性
        摘要, 可直接交给 serialize_metrics 落盘, 也可经
        deserialize_metrics 还原(甚至跨进程)后恢复。不修改入参与
        k_schedule。
    weighted_sample_k_schedule_resume_indices(items, weights, k_schedule,
        state, draws)
        按轮样本数计划会话的按索引恢复入口: 传入与创建断点时相同的
        items、weights、k_schedule 与状态, 返回 (索引轮次列表, 下一状态)。
        第一轮从断点位置开始, 逐轮等于一次性
        weighted_sample_k_schedule_indices 的零基区间 [pos, pos+draws);
        多次连续续接与一次性生成逐项相同, 恢复时无需从头重放随机流。
        draws 必须是非布尔非负整数(TypeError / ValueError), 恢复窗口超出
        计划范围抛 ValueError; draws=0 返回空轮次与位置、随机状态不变的
        状态副本, 样本数为零的轮次只推进 position 且不消耗随机流。状态
        不是映射抛 TypeError; 字段缺失或未知、版本或 kind 不支持、摘要或
        输入(items、weights、完整 k_schedule)不匹配、抽样路径标记不一致
        统一抛 ValueError, 且绝不产生部分轮次。不修改入参与状态。
    weighted_sample_k_schedule_resume(items, weights, k_schedule, state,
        draws)
        按轮样本数计划会话的按元素值恢复入口, 规则与
        weighted_sample_k_schedule_resume_indices 完全一致(同一套校验
        顺序与异常类别): 每轮按原始位置映射元素值(相同值的不同位置仍按
        位置区分), 返回的下一状态与按索引入口逐字段一致, 可互换续接,
        也可经 serialize_metrics / deserialize_metrics 往返后继续恢复。
    weighted_sample_plan_checkpoint(items, weights_schedule, k_schedule,
        seed=0, start=0)
        创建按轮权重与样本数联合计划采样会话的断点: 沿用
        weighted_sample_plan_indices 的全部规则与固定校验顺序(items、
        weights_schedule、k_schedule、seed、start; 两个计划均为有限非
        文本序列且等长, 每个权重行与 items 等长, k_schedule 每项为非
        布尔非负整数且不超过 items 长度, 权重接受 int/float/Fraction/
        Decimal 并拒绝负数、NaN、无穷与错误结构, 任一轮样本数超过对应行
        正权重位置数也拒绝), start 越过计划长度抛 ValueError; draws 恒按
        0 处理, 创建时不产出轮次。校验通过后先完成 start 个完整轮次(被
        跳过的第 j 轮按 weights_schedule[j] 的权重与 k_schedule[j] 的
        样本数消耗同一条由 seed 初始化的随机流, 样本数为零的轮次不消耗
        随机流), 再返回只含 JSON 原生值的状态映射; 状态绑定版本、kind、
        position、n、计划长度、items / 完整 weights_schedule / 完整
        k_schedule 指纹、标签化 seed、随机流快照与完整性摘要, 可直接
        交给 serialize_metrics 落盘, 也可经 deserialize_metrics 还原
        (甚至跨进程)后恢复。不修改入参与两个计划。
    weighted_sample_plan_resume_indices(items, weights_schedule, k_schedule,
        state, draws)
        联合计划会话的按索引恢复入口: 传入与创建断点时相同的 items、
        weights_schedule、k_schedule 与状态, 返回 (索引轮次列表, 下一
        状态)。第一轮从断点位置开始, 逐轮等于一次性
        weighted_sample_plan_indices 的零基区间 [pos, pos+draws);
        多次连续续接与一次性生成逐项相同, 恢复时无需从头重放随机流。
        draws 必须是非布尔非负整数(TypeError / ValueError), 恢复窗口
        超出计划范围抛 ValueError; draws=0 返回空轮次与位置、随机状态
        不变的状态副本, 样本数为零的轮次只推进 position 且不消耗随机流。
        状态不是映射抛 TypeError; 字段缺失或未知、版本或 kind 不支持、
        摘要或输入(items、完整 weights_schedule、完整 k_schedule)不
        匹配统一抛 ValueError, 且绝不产生部分轮次。不修改入参与状态。
    weighted_sample_plan_resume(items, weights_schedule, k_schedule, state,
        draws)
        联合计划会话的按元素值恢复入口, 规则与
        weighted_sample_plan_resume_indices 完全一致(同一套校验顺序
        与异常类别): 每轮按原始位置映射元素值(相同值的不同位置仍按位置
        区分), 返回的下一状态与按索引入口逐字段一致, 可互换续接,
        也可经 serialize_metrics / deserialize_metrics 往返后继续恢复。
    weighted_sample_schedule_checkpoint(items, weights_schedule, k, seed=0,
        start=0)
        创建按轮权重计划采样会话的断点: 沿用 weighted_sample_schedule_
        indices 的全部规则与固定校验顺序(items、weights_schedule、k、
        seed、start; schedule 必须是有限非文本序列, 每行与 items 等长,
        权重接受 int/float/Fraction/Decimal 并拒绝负数、NaN、无穷与错误
        结构, 任一行在 k>0 时正权重不足 k 个也拒绝), start 越过计划长度
        抛 ValueError; draws 恒按 0 处理, 创建时不产出轮次。校验通过后
        先完成 start 个完整轮次(被跳过的第 j 轮按 weights_schedule[j] 的
        权重与抽样计划消耗同一条由 seed 初始化的随机流, k=0 不消耗随机
        流), 再返回只含 JSON 原生值的状态映射; 状态绑定版本、kind、
        position、k/n、计划长度、items 指纹、完整 schedule 指纹、标签化
        seed、随机流快照与完整性摘要, 可直接交给 serialize_metrics 落盘,
        也可经 deserialize_metrics 还原(甚至跨进程)后恢复。不修改入参。
    weighted_sample_schedule_resume_indices(items, weights_schedule, k,
        state, draws)
        按轮权重计划会话的按索引恢复入口: 传入与创建断点时相同的 items、
        weights_schedule、k 与状态, 返回 (索引轮次列表, 下一状态)。第一
        轮从断点位置开始, 逐轮等于一次性 weighted_sample_schedule_indices
        的零基区间 [pos, pos+draws); 多次连续续接与一次性生成逐项相同,
        恢复时无需从头重放随机流。draws 必须是非布尔非负整数(TypeError /
        ValueError), 恢复窗口超出计划范围抛 ValueError; draws=0 返回空
        轮次与位置、随机状态不变的状态副本, k=0 时只推进 position 且不
        消耗随机流。状态不是映射抛 TypeError; 字段缺失或未知、版本不
        支持、摘要或输入(items、完整 schedule、k)不匹配统一抛 ValueError,
        且绝不产生部分轮次。不修改入参与状态。
    weighted_sample_schedule_resume(items, weights_schedule, k, state, draws)
        按轮权重计划会话的按元素值恢复入口, 规则与
        weighted_sample_schedule_resume_indices 完全一致(同一套校验顺序
        与异常类别): 每轮按原始位置映射元素值(相同值的不同位置仍按位置
        区分), 返回的下一状态与按索引入口逐字段一致, 可互换续接, 也可经
        serialize_metrics / deserialize_metrics 往返后继续恢复。
    weighted_sample_partition_indices(items, weights, group_sizes, seed=0)
        分组采样入口: 对 (items, weights) 做一次长度为
        sum(group_sizes) 的加权无放回抽样, 再按 group_sizes 把所得序列
        切成多个互不重叠的样本组, 返回按组排列的零基原始位置(每组一份
        按抽样先后排列的列表, 组内与组间位置都不重复)。items、weights、
        seed 沿用 weighted_sample_indices 的全部规则; group_sizes 是
        有限非文本序列, 成员均为非布尔非负整数。依次拼接各组逐项等于
        weighted_sample_indices(items, weights, sum(group_sizes), seed),
        零权重位置永不出现, 相同值的不同位置分别处理。结构或成员类型
        错误抛 TypeError; 长度不一致、负组大小、总组大小超过可用正权重
        位置数、负权重、NaN 或无穷权重抛 ValueError; 空计划、全零组大小
        与总量为零(总组大小也为零)在校验后返回对应数量的空组。不修改
        入参。
    weighted_sample_partition(items, weights, group_sizes, seed=0)
        weighted_sample_partition_indices 的元素值入口: 规则、校验顺序与
        异常类别完全一致, 每组按原始位置映射 items 元素, 两个入口逐组
        逐项对应。
    weighted_sample_partition_checkpoint(items, weights, group_sizes,
        seed=0, start=0)
        创建分组采样会话的断点: 沿用 weighted_sample_partition_indices
        的全部规则与固定校验顺序(items、weights、group_sizes、seed;
        group_sizes 成员为非布尔非负整数, 总组大小不超过正权重位置数,
        权重接受 int/float/Fraction/Decimal 并拒绝负数、NaN、无穷与错误
        结构), start 必须是非布尔非负整数且不超过组计划长度。校验通过后
        一次性抽出整条无放回位置序列并以 start 标记组边界, 返回只含 JSON
        原生值的状态映射; 状态绑定版本、kind、start(已完成组数)、n、组数
        与总组大小、items / weights / group_sizes 指纹、标签化 seed、抽样
        计划、整条组位置序列与完整性摘要, 可直接交给 serialize_metrics
        落盘, 也可经 deserialize_metrics 还原(甚至跨进程)后恢复。不修改
        入参。
    weighted_sample_partition_resume_indices(items, weights, group_sizes,
        state, draws)
        分组会话的按索引恢复入口: 传入与创建断点时相同的 items、weights、
        group_sizes 与状态, 返回 (索引分组列表, 下一状态)。第一批从断点
        start 开始, 逐组等于一次性 weighted_sample_partition_indices 的
        零基区间 [start, start+draws); 多次连续续接与一次性生成分组逐项
        相同, 恢复按状态携带的组位置序列切片, 无需从头重放随机流。
        draws 必须是非布尔非负整数(TypeError / ValueError), 恢复窗口超出
        组计划范围抛 ValueError; draws=0 返回空分组与 start 不变的状态
        副本。状态不是映射抛 TypeError; 字段缺失或未知、版本不支持、摘要
        或输入(items、weights、group_sizes)不匹配统一抛 ValueError, 且
        绝不产生部分分组。不修改入参与状态。
    weighted_sample_partition_resume(items, weights, group_sizes, state,
        draws)
        分组会话的按元素值恢复入口, 规则与
        weighted_sample_partition_resume_indices 完全一致(同一套校验顺序
        与异常类别): 每组按原始位置映射元素值(相同值的不同位置仍按位置
        区分), 返回的下一状态与按索引入口逐字段一致, 可互换续接, 也可经
        serialize_metrics / deserialize_metrics 往返后继续恢复。
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
    weighted_sample_stratified_indices(items, weights, strata, quotas,
        seed=0)
        分层配额采样入口: strata 与 items 等长, 每个位置保存非布尔非负
        整数分层编号; quotas 的下标对应分层编号, 成员为非布尔非负整数
        配额, 长度必须恰好等于最大编号加一。分层按编号升序依次处理, 第
        number 层在其成员位置中按权重比例无放回抽取 quotas[number] 个
        不同位置, 各层结果按编号升序拼接, 层内按抽样先后排列, 返回原始
        零基索引。所有层共享同一个由 seed 初始化的随机流, 零配额分层不
        消耗该流; 相同 (输入, quotas, seed) 唯一确定同一序列; 只有编号
        为零的单层时与 weighted_sample_indices(items, weights,
        quotas[0], seed) 逐项相同。零权重位置永不入选; 全部配额为零时
        返回空列表; 空 items 只接受空 strata 与空 quotas。结构或成员
        类型错误抛 TypeError; 长度不一致、编号越界、quotas 长度不等于
        最大编号加一、负配额、配额超过该层正权重位置数、负权重、NaN 或
        无穷权重抛 ValueError。全部校验在产生任何结果前完成, 不修改
        入参。
    weighted_sample_stratified(items, weights, strata, quotas, seed=0)
        weighted_sample_stratified_indices 的元素值入口: 规则、校验顺序
        与异常类别完全一致, 按相同索引返回元素值列表, 两个入口逐项对应
        (相同值的不同位置仍按位置独立处理)。
    weighted_sample_stratified_counts(items, weights, strata, quotas,
        seed=0)
        weighted_sample_stratified_indices 的频次入口: 接受相同的参数
        语义与固定校验顺序, 返回长度等于 items 的整数 list counts,
        counts[i] 在位置 i 被选中时为一、其余为零; 结果等于把索引入口
        同参数的结果按位置摊平计数。计数为任意精度整数, 可直接交给
        serialize_metrics 并经 deserialize_metrics 精确往返。不修改
        入参。
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


def weighted_sample_schedule_counts(
    items, weights_schedule, k, draws, seed=0, start=0
):
    """weighted_sample_schedule_indices 的批量频次入口: 直接按原始零基
    位置累计窗口内的选中次数, 免去调用方逐轮遍历。

    接受与 weighted_sample_schedule_indices 完全相同的 items、
    weights_schedule、k、draws、seed、start 语义与固定校验顺序, 按同一条
    由 seed 初始化的随机流先生成(并跳过)start 个完整轮次, 再生成 draws
    轮; 返回长度等于 items 的 list, counts[i] 即零基区间
    [start, start+draws) 内位置 i 被选中的总次数(每轮无放回, 同一位置每轮
    至多计一次; 相等的元素值仍按不同位置分别累计)。因此对相同输入, 本入口
    与逐轮调用 weighted_sample_schedule_indices 后再按位置摊平计数逐项
    一致 —— 同一随机流、每轮同一权重行与同一抽样计划; 首轮、后续轮次、
    相同种子以及 k=0 的轮次的随机流消耗都与对应索引入口逐项对齐, start
    只跳过前置完整轮次, 保持窗口切片语义。

    draws=0 或 k=0 返回全零列表(k=0 的轮次不消耗随机流), 但仍完成全部
    结构、权重与可行性校验; 任一行在 k>0 时正权重位置不足 k 个、行长不符、
    窗口越界、负权重、NaN 或无穷权重都在返回列表前抛 TypeError /
    ValueError。全部失败都不返回部分计数。计数为任意精度整数, 可直接交给
    serialize_metrics 并经 deserialize_metrics 精确往返。不修改入参与
    weights_schedule。
    """
    n = _validate_schedule_inputs(
        items, weights_schedule, k, draws, seed, start
    )

    counts = [0] * n
    # draws=0: 全部校验已在上面完成, 直接返回全零列表, 不消耗随机流。
    if draws == 0:
        return counts

    rng = random.Random(seed)
    # 与 weighted_sample_schedule_indices 完全相同的计划选择、跳过与生成
    # 节奏: 窗口 [0, start+draws) 内每一轮(含被跳过的轮次)都按自己那一行
    # 的权重选择抽样计划, 每轮复制一份权重, 绝不修改 schedule; k=0 的轮次
    # 不消耗随机流(_draw_indices_once 以 k=0 空转), draws=0 已提前返回
    # —— 计数入口与索引入口的随机流消耗因此逐项对齐。
    plans = [
        _select_sampling_plan(list(weights_schedule[j]), k)
        for j in range(start + draws)
    ]
    if k > 0:
        for j in range(start):
            planned_weights, use_exact = plans[j]
            _draw_indices_once(n, planned_weights, k, rng, use_exact)
    for j in range(start, start + draws):
        planned_weights, use_exact = plans[j]
        for position in _draw_indices_once(
            n, planned_weights, k, rng, use_exact
        ):
            counts[position] += 1
    return counts


def weighted_sample_schedule_stream_indices(
    items, weights_schedule, k, draws, seed=0, start=0
):
    """weighted_sample_schedule_indices 的按需逐轮入口。

    返回一个可迭代对象, 每次迭代产出一轮按抽样先后排列的零基原始索引
    列表, 共 draws 轮; 对相同输入和种子, 转成列表后与
    weighted_sample_schedule_indices(...) 的全部轮次完全一致(第 start+j
    轮使用 weights_schedule[start+j] 的权重行, 第一轮同样与
    weighted_sample_indices 对应行逐项相同)。每轮都从全部原始位置重新
    开始, 轮内不放回, 重复值按位置区分, 轮次之间允许再次选中同一位置。

    可选的 start(默认 0)与批量入口语义相同: 迭代时先从该 seed 对应的
    轮次流按需跳过 start 个完整轮次(被跳过的第 j 轮同样按
    weights_schedule[j] 的权重与抽样计划消耗同一条确定性随机流), 再逐轮
    产出 draws 轮; 转成列表后与 start=0 的完整结果按零基区间
    [start, start+draws) 切片逐项一致, start 不改变后续随机序列。

    与批量入口不同, 轮次在调用方消费时才逐轮生成, 长批次不必一次物化;
    但全部校验(items / weights_schedule / 每一行的结构与类型、行长、
    draws / start 类型与取值、窗口范围、权重 NaN / 无穷 / 负数、每一轮的
    正权重可行性)都在创建时完成 —— 非法输入在调用当场抛出稳定的
    TypeError / ValueError, 绝不会延迟到已经产出部分轮次之后; draws=0
    或 k=0 也不省略任何校验。draws=0 时返回不产出元素的迭代对象; k=0
    时每轮产出空列表且不消耗随机流。不修改入参与 weights_schedule。
    """
    n = _validate_schedule_inputs(
        items, weights_schedule, k, draws, seed, start
    )

    rng = random.Random(seed)
    # 与批量入口完全相同的计划选择: 窗口 [0, start+draws) 内每一轮(含被
    # 跳过的轮次)都按自己那一行的权重选择抽样计划, 每轮复制一份权重,
    # 绝不修改 schedule。draws=0 时 plans 覆盖 [0, start), 仅用于跳过,
    # 迭代器本身不产出任何元素。
    plans = [
        _select_sampling_plan(list(weights_schedule[j]), k)
        for j in range(start + draws)
    ]

    def _rounds():
        # 按需跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流。
        # k=0 的轮次不消耗随机流, draws=0 时跳过与否不影响空结果, 两种
        # 情形都无需空转 —— 与既有流式入口同一节奏。
        if k > 0 and draws > 0:
            for j in range(start):
                planned_weights, use_exact = plans[j]
                _draw_indices_once(n, planned_weights, k, rng, use_exact)
        for j in range(start, start + draws):
            planned_weights, use_exact = plans[j]
            yield _draw_indices_once(
                n, planned_weights, k, rng, use_exact
            )

    return _rounds()


def weighted_sample_schedule_stream(
    items, weights_schedule, k, draws, seed=0, start=0
):
    """weighted_sample_schedule 的按需逐轮入口, 规则与
    weighted_sample_schedule_stream_indices 完全一致(同一套创建时校验与
    start 窗口语义), 区别仅在于每轮按相同索引产出元素值列表; 与
    weighted_sample_schedule 的逐轮结果完全一致。
    """
    index_stream = weighted_sample_schedule_stream_indices(
        items, weights_schedule, k, draws, seed, start
    )
    return ([items[i] for i in round_indices] for round_indices in index_stream)


# ---------------------------------------------------------------------------
# 按轮样本数计划(固定权重, 每轮样本数不同)
# ---------------------------------------------------------------------------

def _validate_k_schedule_inputs(items, weights, k_schedule, draws, seed,
                                start):
    """按轮样本数计划入口共用的全部前置校验, 返回位置数 n。

    校验顺序固定: 先 items、weights、seed 的结构/类型(与既有采样入口
    同一套规则, TypeError), 再 k_schedule 的结构(有限非文本且长度可确定
    的序列)与每个成员的类型(非布尔整数, TypeError), 然后 draws、start
    (非布尔非负整数); 随后 weights 长度与 items 一致、每个计划成员落在
    [0, n] 内、窗口 [start, start+draws) 不超出计划范围(ValueError);
    接着权重元素类型(TypeError)与取值(ValueError)校验; 最后对计划的
    每个成员做正权重可行性检查(该轮样本数超过正权重位置数时抛
    ValueError)。全部校验在产生任何一轮之前完成, draws=0 也不例外;
    不修改入参。
    """
    # ---- 1. 结构与参数类型 (TypeError) ----
    if not _is_length_determinable_sequence(items):
        raise TypeError("items must be a length-determinable sequence")
    if not _is_length_determinable_sequence(weights):
        raise TypeError("weights must be a length-determinable sequence")
    if not isinstance(seed, _SEED_TYPES):
        raise TypeError("unsupported seed type: %s" % type(seed).__name__)
    if not _is_length_determinable_sequence(k_schedule):
        raise TypeError("k_schedule must be a length-determinable sequence")
    for member in k_schedule:
        if isinstance(member, bool) or not isinstance(member, int):
            raise TypeError(
                "k_schedule members must be non-boolean integers"
            )
    _validate_draws(draws)
    _validate_start(start)

    # ---- 2. 长度、计划成员取值与窗口范围 (ValueError) ----
    n = len(items)
    if len(weights) != n:
        raise ValueError("invalid sample size")
    for member in k_schedule:
        if member < 0 or member > n:
            raise ValueError("invalid sample size")
    if start + draws > len(k_schedule):
        raise ValueError("schedule window out of range")

    # ---- 3. 权重元素类型与取值 (TypeError / ValueError) ----
    _validate_weight_elements(weights)

    # ---- 4. 每一轮的正权重可行性 (ValueError) ----
    # 权重固定, 正权重位置数对每轮相同: 任一轮的样本数超过正权重位置数
    # 都在产生任何一轮之前确定抛 ValueError; 样本数为零的轮次始终合法。
    positive = _count_positive_weights(weights)
    for member in k_schedule:
        if member > positive:
            raise ValueError("no positive weight")
    return n


def weighted_sample_k_schedule_indices(
    items, weights, k_schedule, draws, seed=0, start=0
):
    """按轮样本数计划的批量入口: 固定权重, 每轮样本数由 k_schedule 给出。

    k_schedule 是有限非文本序列, 成员均为非布尔非负整数且不超过 items
    长度; 第 start+j 轮(零基)使用 k_schedule[start+j] 作为该轮样本数,
    轮内按 weights 加权无放回抽取。返回长度等于 draws 的外层 list, 每个
    元素是一轮按抽样先后排列的零基原始索引。每轮都从全部原始位置重新
    开始(同一轮内位置最多出现一次, 重复值按位置区分, 轮次之间允许再次
    选中同一位置); 所有轮次共享同一个由 seed 初始化的随机流。计划中各项
    都等于 k 时, 与 weighted_sample_many_indices(items, weights, k,
    draws, seed, start) 逐轮逐项一致。

    可选的 start(默认 0)表示先从该 seed 对应的轮次流开始跳过 start 个
    完整轮次 —— 被跳过的第 j 轮同样按 k_schedule[j] 的样本数消耗同一
    条确定性随机流, 不改变任何选择规则 —— 再生成 draws 轮; 结果与
    start=0 的完整调用按零基区间 [start, start+draws) 切片逐项一致。
    样本数为零的轮次返回空列表且不消耗随机流。

    全部校验在返回任何轮次前完成: items、weights、seed 沿用既有采样入口
    规则; draws、start 必须是非布尔非负整数; k_schedule 非长度可确定的
    非文本序列、或任一成员不是非布尔整数时抛 TypeError; 成员为负或超过
    位置数、窗口 [start, start+draws) 超出计划范围、负权重、NaN、无穷
    权重, 或任一轮样本数超过正权重位置数时抛 ValueError。draws=0 仍完成
    全部校验并返回空 list。seed=None 保留现有随机语义。不修改入参与
    k_schedule。
    """
    n = _validate_k_schedule_inputs(
        items, weights, k_schedule, draws, seed, start
    )

    # draws=0: 全部校验已在上面完成, 直接返回空结果, 不消耗随机流。
    if draws == 0:
        return []

    rng = random.Random(seed)
    # 复制到本地, 绝不修改入参; 窗口 [0, start+draws) 内每一轮(含被跳过
    # 的轮次)都按自己那一项的样本数选择抽样计划。样本数为零的轮次与既有
    # k=0 入口一样不消耗随机流; 样本数相同的轮次计划相同, 因此计划中各项
    # 都等于 k 时每轮的计划与 weighted_sample_many_indices 完全一致。
    pool_weights = list(weights)
    plans = [
        _select_sampling_plan(pool_weights, k_schedule[j])
        for j in range(start + draws)
    ]

    # 先跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流。样本数
    # 为零的轮次不消耗随机流, 无需空转 —— 与既有批量入口同一节奏。
    for j in range(start):
        if k_schedule[j] > 0:
            planned_weights, use_exact = plans[j]
            _draw_indices_once(
                n, planned_weights, k_schedule[j], rng, use_exact
            )

    rounds = []
    for j in range(start, start + draws):
        planned_weights, use_exact = plans[j]
        rounds.append(
            _draw_indices_once(
                n, planned_weights, k_schedule[j], rng, use_exact
            )
        )
    return rounds


def weighted_sample_k_schedule(
    items, weights, k_schedule, draws, seed=0, start=0
):
    """weighted_sample_k_schedule_indices 的元素值入口: 规则、校验顺序与
    异常类别完全一致, 区别仅在于每轮按相同索引返回元素值列表; 两个入口
    逐轮逐项对应(相同值的不同位置仍按位置独立处理)。计划中各项都等于 k
    时与 weighted_sample_many 同参调用逐轮完全一致。
    """
    rounds = weighted_sample_k_schedule_indices(
        items, weights, k_schedule, draws, seed, start
    )
    return [[items[i] for i in round_indices] for round_indices in rounds]


def weighted_sample_k_schedule_stream_indices(
    items, weights, k_schedule, draws, seed=0, start=0
):
    """weighted_sample_k_schedule_indices 的按需逐轮入口。

    返回一个可迭代对象, 每次迭代产出一轮按抽样先后排列的零基原始索引
    列表, 共 draws 轮; 对相同输入和种子, 转成列表后与
    weighted_sample_k_schedule_indices(...) 的全部轮次完全一致。每轮都
    从全部原始位置重新开始, 轮内不放回, 重复值按位置区分, 样本数为零的
    轮次产出空列表且不消耗随机流。

    可选的 start(默认 0)与批量入口语义相同: 迭代时先从该 seed 对应的
    轮次流按需跳过 start 个完整轮次(只消耗同一条确定性随机流), 再逐轮
    产出 draws 轮。

    与批量入口不同, 轮次在调用方消费时才逐轮生成, 长批次不必一次物化;
    但全部校验(结构、成员类型、取值、窗口范围、正权重可行性)都在创建时
    完成 —— 非法输入在调用当场抛出稳定的 TypeError / ValueError, 绝不会
    延迟到已经产出部分轮次之后。draws=0 时仍完成全部校验并返回不产出
    元素的迭代对象。不修改入参与 k_schedule。
    """
    n = _validate_k_schedule_inputs(
        items, weights, k_schedule, draws, seed, start
    )

    # 复制到本地, 绝不修改入参; 抽样计划与批量入口逐轮相同。
    pool_weights = list(weights)
    rng = random.Random(seed)
    plans = [
        _select_sampling_plan(pool_weights, k_schedule[j])
        for j in range(start + draws)
    ]

    def _rounds():
        # 按需跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流。
        # 样本数为零的轮次不消耗随机流, draws=0 时跳过与否不影响空结果,
        # 两种情形都无需空转。
        if draws > 0:
            for j in range(start):
                if k_schedule[j] > 0:
                    planned_weights, use_exact = plans[j]
                    _draw_indices_once(
                        n, planned_weights, k_schedule[j], rng, use_exact
                    )
            for j in range(start, start + draws):
                planned_weights, use_exact = plans[j]
                yield _draw_indices_once(
                    n, planned_weights, k_schedule[j], rng, use_exact
                )

    return _rounds()


def weighted_sample_k_schedule_stream(
    items, weights, k_schedule, draws, seed=0, start=0
):
    """weighted_sample_k_schedule 的按需逐轮入口, 规则与
    weighted_sample_k_schedule_stream_indices 完全一致(同一套创建时
    校验与 start 窗口语义), 区别仅在于每轮按相同索引产出元素值列表;
    与 weighted_sample_k_schedule 的逐轮结果完全一致。
    """
    index_stream = weighted_sample_k_schedule_stream_indices(
        items, weights, k_schedule, draws, seed, start
    )
    return ([items[i] for i in round_indices] for round_indices in index_stream)


def weighted_sample_k_schedule_counts(
    items, weights, k_schedule, draws, seed=0, start=0
):
    """weighted_sample_k_schedule_indices 的批量频次入口: 直接按原始零基
    位置累计窗口内的选中次数, 免去调用方逐轮遍历。

    接受与 weighted_sample_k_schedule_indices 完全相同的 items、weights、
    k_schedule、draws、seed、start 语义与固定校验顺序, 按同一条由 seed
    初始化的随机流先生成(并跳过)start 个完整轮次, 再生成 draws 轮;
    返回长度等于 items 的 list, counts[i] 即零基区间 [start, start+draws)
    内位置 i 被选中的总次数(每轮无放回, 同一位置每轮至多计一次; 相等的
    元素值仍按不同位置分别累计)。因此对相同输入, 本入口与逐轮调用
    weighted_sample_k_schedule_indices 后再按位置摊平计数逐项一致 ——
    首轮、后续轮次、相同种子以及样本数为零的轮次的随机流消耗都与对应
    索引入口逐项对齐。

    draws=0 返回全零列表(仍完成全部校验); 任一轮样本数超过正权重位置数
    时在返回列表前抛 ValueError。全部失败都不返回部分计数。计数为任意
    精度整数, 可直接交给 serialize_metrics 并经 deserialize_metrics
    精确往返。不修改入参与 k_schedule。
    """
    n = _validate_k_schedule_inputs(
        items, weights, k_schedule, draws, seed, start
    )

    counts = [0] * n
    # 与 weighted_sample_k_schedule_indices 完全相同的跳过与生成节奏:
    # 样本数为零的轮次不消耗随机流, draws=0 时跳过与否都不影响全零结果
    # —— 计数入口与索引入口的随机流消耗因此逐项对齐。
    if draws > 0:
        pool_weights = list(weights)
        rng = random.Random(seed)
        plans = [
            _select_sampling_plan(pool_weights, k_schedule[j])
            for j in range(start + draws)
        ]
        for j in range(start):
            if k_schedule[j] > 0:
                planned_weights, use_exact = plans[j]
                _draw_indices_once(
                    n, planned_weights, k_schedule[j], rng, use_exact
                )
        for j in range(start, start + draws):
            if k_schedule[j] > 0:
                planned_weights, use_exact = plans[j]
                for position in _draw_indices_once(
                    n, planned_weights, k_schedule[j], rng, use_exact
                ):
                    counts[position] += 1
    return counts


# ---------------------------------------------------------------------------
# 按轮权重与样本数联合计划(每轮权重行与样本数都不同)
# ---------------------------------------------------------------------------

def _validate_plan_inputs(items, weights_schedule, k_schedule, draws, seed,
                          start):
    """联合计划入口共用的全部前置校验, 返回位置数 n。

    校验顺序固定: 先 items、seed 的结构/类型(与既有采样入口同一套规则,
    TypeError), 再 weights_schedule 及其每一行的结构(非文本且长度可确定
    的序列, TypeError), 然后 k_schedule 的结构(有限非文本且长度可确定的
    序列)与每个成员的类型(非布尔整数, TypeError), 最后 draws、start
    (非布尔非负整数); 随后每一行长度与 items 一致、每个计划成员落在
    [0, n] 内、两个计划等长、窗口 [start, start+draws) 不超出计划范围
    (ValueError); 接着对每一行权重做与单轮入口完全相同的元素类型
    (TypeError)与取值(ValueError)校验; 最后对每一轮做正权重可行性检查
    (第 j 轮样本数 k_schedule[j] 超过第 j 行正权重位置数时抛 ValueError)。
    全部校验在产生任何一轮之前完成, draws=0 也不例外; 不修改入参。
    """
    # ---- 1. 结构与参数类型 (TypeError) ----
    if not _is_length_determinable_sequence(items):
        raise TypeError("items must be a length-determinable sequence")
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
    if not _is_length_determinable_sequence(k_schedule):
        raise TypeError("k_schedule must be a length-determinable sequence")
    for member in k_schedule:
        if isinstance(member, bool) or not isinstance(member, int):
            raise TypeError(
                "k_schedule members must be non-boolean integers"
            )
    _validate_draws(draws)
    _validate_start(start)

    # ---- 2. 行长度、计划成员取值、计划等长与窗口范围 (ValueError) ----
    n = len(items)
    for row in weights_schedule:
        if len(row) != n:
            raise ValueError("invalid sample size")
    for member in k_schedule:
        if member < 0 or member > n:
            raise ValueError("invalid sample size")
    if len(weights_schedule) != len(k_schedule):
        raise ValueError("schedule length mismatch")
    if start + draws > len(k_schedule):
        raise ValueError("schedule window out of range")

    # ---- 3. 每一行的权重元素类型与取值 (TypeError / ValueError) ----
    for row in weights_schedule:
        _validate_weight_elements(row)

    # ---- 4. 每一轮的正权重可行性 (ValueError) ----
    # 第 j 轮以 weights_schedule[j] 抽取 k_schedule[j] 个位置: 任一轮的
    # 样本数超过对应行正权重位置数都在产生任何一轮之前确定抛 ValueError;
    # 样本数为零的轮次始终合法。
    for j, row in enumerate(weights_schedule):
        if k_schedule[j] > _count_positive_weights(row):
            raise ValueError("no positive weight")
    return n


def weighted_sample_plan_indices(items, weights_schedule, k_schedule, draws,
                                 seed=0, start=0):
    """按轮权重与样本数联合计划的批量入口: 第 j 轮同时使用
    weights_schedule[start+j] 的权重行与 k_schedule[start+j] 的样本数。

    weights_schedule 是有限非文本序列, 成员均为与 items 等长的权重序列;
    k_schedule 是等长的有限非文本序列, 成员均为非布尔非负整数且不超过
    items 长度。返回长度等于 draws 的外层 list, 每个元素是一轮按抽样先后
    排列的零基原始索引。每轮都从全部原始位置重新开始(同一轮内位置最多
    出现一次, 重复值按位置区分, 轮次之间允许再次选中同一位置); 所有轮次
    共享同一个由 seed 初始化的随机流。权重各行相同且计划各项都等于 k 时,
    与 weighted_sample_many_indices 同参调用逐轮逐项一致; 仅 k_schedule
    各项都等于 k 时与 weighted_sample_schedule_indices 一致, 仅权重各行
    相同时与 weighted_sample_k_schedule_indices 一致。

    可选的 start(默认 0)表示先从该 seed 对应的轮次流开始跳过 start 个
    完整轮次 —— 被跳过的第 j 轮同样按 weights_schedule[j] 的权重与
    k_schedule[j] 的样本数消耗同一条确定性随机流, 不改变任何选择规则 ——
    再生成 draws 轮; 结果与 start=0 的完整调用按零基区间
    [start, start+draws) 切片逐项一致。样本数为零的轮次返回空列表且不
    消耗随机流。

    全部校验在返回任何轮次前完成: items、seed 沿用既有采样入口规则;
    draws、start 必须是非布尔非负整数; weights_schedule / k_schedule 非
    长度可确定的非文本序列、任一行不是同类序列、或任一计划成员不是非布尔
    整数时抛 TypeError; 行长度与 items 不一致、计划成员为负或超过位置数、
    两个计划不等长、窗口 [start, start+draws) 超出计划范围、负权重、
    NaN、无穷权重, 或任一轮样本数超过对应行正权重位置数时抛 ValueError。
    权重元素规则与既有入口相同(非布尔 int、有限非负 float、Fraction、
    Decimal, 可混合; 零权重永不被选中; 超大整数、Fraction、Decimal 全程
    不经过浮点)。draws=0 仍完成全部校验并返回空 list。seed=None 保留
    现有随机语义。不修改入参与两个计划。
    """
    n = _validate_plan_inputs(
        items, weights_schedule, k_schedule, draws, seed, start
    )

    # draws=0: 全部校验已在上面完成, 直接返回空结果, 不消耗随机流。
    if draws == 0:
        return []

    rng = random.Random(seed)
    # 窗口 [0, start+draws) 内每一轮(含被跳过的轮次)都按自己那一行的权重
    # 与自己那一项的样本数选择抽样计划: 每轮复制一份权重, 绝不修改两个
    # 计划; 被跳过的第 j 轮同样按第 j 轮的计划消耗随机流, 因此跳过 start
    # 个完整轮次与从 0 生成时消耗的随机流完全相同。
    plans = [
        _select_sampling_plan(list(weights_schedule[j]), k_schedule[j])
        for j in range(start + draws)
    ]

    # 先跳过 start 个完整轮次: 与完整序列消耗同一条确定性随机流。样本数
    # 为零的轮次不消耗随机流, 无需空转 —— 与既有批量入口同一节奏。
    for j in range(start):
        if k_schedule[j] > 0:
            planned_weights, use_exact = plans[j]
            _draw_indices_once(
                n, planned_weights, k_schedule[j], rng, use_exact
            )

    rounds = []
    for j in range(start, start + draws):
        planned_weights, use_exact = plans[j]
        rounds.append(
            _draw_indices_once(
                n, planned_weights, k_schedule[j], rng, use_exact
            )
        )
    return rounds


def weighted_sample_plan(items, weights_schedule, k_schedule, draws, seed=0,
                         start=0):
    """weighted_sample_plan_indices 的元素值入口: 规则、校验顺序与异常
    类别完全一致, 区别仅在于每轮按相同索引返回元素值列表; 两个入口逐轮
    逐项对应(相同值的不同位置仍按位置独立处理)。
    """
    rounds = weighted_sample_plan_indices(
        items, weights_schedule, k_schedule, draws, seed, start
    )
    return [[items[i] for i in round_indices] for round_indices in rounds]


def weighted_sample_plan_counts(items, weights_schedule, k_schedule, draws,
                                seed=0, start=0):
    """weighted_sample_plan_indices 的批量频次入口: 直接按原始零基位置
    累计窗口内的选中次数, 免去调用方逐轮遍历。

    接受与 weighted_sample_plan_indices 完全相同的 items、
    weights_schedule、k_schedule、draws、seed、start 语义与固定校验顺序,
    按同一条由 seed 初始化的随机流先生成(并跳过)start 个完整轮次, 再生成
    draws 轮; 返回长度等于 items 的 list, counts[i] 即零基区间
    [start, start+draws) 内位置 i 被选中的总次数(每轮无放回, 同一位置
    每轮至多计一次; 相等的元素值仍按不同位置分别累计)。因此对相同输入,
    本入口与逐轮调用 weighted_sample_plan_indices 后再按位置摊平计数逐项
    一致 —— 同一随机流、每轮同一权重行、同一样本数与同一抽样计划; 样本数
    为零的轮次的随机流消耗与对应索引入口逐项对齐。

    draws=0 返回全零列表(仍完成全部校验); 任一轮样本数超过对应行正权重
    位置数时在返回列表前抛 ValueError。全部失败都不返回部分计数。计数为
    任意精度整数, 可直接交给 serialize_metrics 并经 deserialize_metrics
    精确往返。不修改入参与两个计划。
    """
    n = _validate_plan_inputs(
        items, weights_schedule, k_schedule, draws, seed, start
    )

    counts = [0] * n
    # 与 weighted_sample_plan_indices 完全相同的跳过与生成节奏: 样本数为
    # 零的轮次不消耗随机流, draws=0 时跳过与否都不影响全零结果 —— 计数
    # 入口与索引入口的随机流消耗因此逐项对齐。
    if draws > 0:
        rng = random.Random(seed)
        plans = [
            _select_sampling_plan(list(weights_schedule[j]), k_schedule[j])
            for j in range(start + draws)
        ]
        for j in range(start):
            if k_schedule[j] > 0:
                planned_weights, use_exact = plans[j]
                _draw_indices_once(
                    n, planned_weights, k_schedule[j], rng, use_exact
                )
        for j in range(start, start + draws):
            if k_schedule[j] > 0:
                planned_weights, use_exact = plans[j]
                for position in _draw_indices_once(
                    n, planned_weights, k_schedule[j], rng, use_exact
                ):
                    counts[position] += 1
    return counts


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
# 可暂停 / 恢复的按轮权重计划采样会话
# ---------------------------------------------------------------------------

_SCHEDULE_CHECKPOINT_KIND = "schedule"


def _weights_schedule_fingerprint(weights_schedule):
    """对完整的按轮权重计划取指纹: 逐行逐位置规范化后整体 sha256。

    行号与行内位置都参与指纹, 因此调换两行(改变第 j 轮使用的权重)、增删
    行或改动任一行的任一权重都会改变指纹; 单个权重的规范化规则与
    _weights_fingerprint 完全一致(类型标签区分 1 与 1.0、Fraction、
    Decimal 等同值不同类型; Fraction、Decimal 与超大整数全程不经过浮点)。
    调用前 schedule 已通过 _validate_schedule_inputs 校验。
    """
    digest = hashlib.sha256()
    for row_index, row in enumerate(weights_schedule):
        for position, weight in enumerate(row):
            line = "%d:%s\n" % (
                row_index, _weight_fingerprint_text(position, weight)
            )
            digest.update(line.encode("utf-8"))
    return digest.hexdigest()


def _schedule_checkpoint_binding_digest(
    seed_tagged, position, k, n, schedule_length,
    items_digest, schedule_digest, rng_payload,
):
    """把按轮计划断点各字段绑定为一个防篡改摘要。

    与 _checkpoint_binding_digest 同一构造(serialize_metrics 规范化后
    sha256), 绑定标签 kind、position、k、n、计划长度、items 与完整
    schedule 的指纹、标签化 seed 与 RNG 快照: 任一字段被改动而不重算
    摘要时, 恢复都会在产出任何轮次前发现, 因此长批次交接无需从头重放
    随机流。
    """
    return _hash_text(serialize_metrics({
        "kind": _SCHEDULE_CHECKPOINT_KIND,
        "seed": seed_tagged,
        "position": position,
        "k": k,
        "n": n,
        "schedule_length": schedule_length,
        "items_digest": items_digest,
        "schedule_digest": schedule_digest,
        "rng": rng_payload,
    }))


def _prepare_validated_schedule_session(
    items, weights_schedule, k, seed, start
):
    """按轮计划断点入口共用的前置准备: 与 weighted_sample_schedule_indices
    一致的全部校验与跳轮。

    以 draws=0 复用 schedule 的全部前置校验(items、k、seed、schedule
    结构与每一行长度、权重取值、每一行正权重可行性、start 不越过计划
    长度), 因此创建断点不会产生任何轮次却仍完成全部校验; 随后把随机流
    推进到 "已完成 start 轮" 的位置 —— 被跳过的第 j 轮按
    weights_schedule[j] 自己的抽样计划消耗, k=0 的轮次不消耗随机流,
    与一次性批量入口的跳过节奏完全一致。返回 (n, rng); 每行权重都复制
    为本地计划, 绝不修改 items 与 weights_schedule。
    """
    n = _validate_schedule_inputs(
        items, weights_schedule, k, 0, seed, start
    )
    rng = random.Random(seed)
    # 只构造被跳过轮次的计划; 每行复制一份权重, 绝不修改 schedule。
    if k > 0:
        for j in range(start):
            planned_weights, use_exact = _select_sampling_plan(
                list(weights_schedule[j]), k
            )
            _draw_indices_once(n, planned_weights, k, rng, use_exact)
    return n, rng


def weighted_sample_schedule_checkpoint(
    items, weights_schedule, k, seed=0, start=0
):
    """创建按轮权重计划采样会话的断点(只含 JSON 原生值的状态映射)。

    校验沿用 weighted_sample_schedule_indices 的全部规则与固定顺序:
    items、k、seed 与既有采样入口一致; weights_schedule 必须是有限非
    文本且长度可确定的序列, 每个成员都是与 items 等长的同类序列;
    权重元素继续接受非布尔 int、有限非负 float、Fraction、Decimal(可
    混合, 超大整数、Fraction、Decimal 不经过浮点); 负数、NaN、无穷权重、
    错误结构或任一行在 k>0 时正权重位置不足 k 个一律拒绝。draws 恒按
    0 处理(本入口不产出轮次), start 必须是非布尔非负整数且不越过计划
    长度(start == 计划长度允许, 表示整批已完成)。全部校验在返回状态前
    完成, 失败不返回部分结果, 也不修改 items 与 weights_schedule。

    校验通过后先完成 start 个完整轮次(第 j 轮按 weights_schedule[j] 的
    权重与抽样计划消耗同一条由 seed 初始化的随机流, k=0 的轮次不消耗
    随机流), 再返回当前位置与只含 JSON 原生值的状态; 状态绑定版本、
    标签 kind、position、k/n、计划长度、items 指纹、完整 schedule 指纹、
    标签化 seed、随机流快照与完整性摘要, 可直接交给 serialize_metrics
    落盘, 也可经 deserialize_metrics 还原(甚至跨进程)后交给
    weighted_sample_schedule_resume_indices 恢复。
    """
    n, rng = _prepare_validated_schedule_session(
        items, weights_schedule, k, seed, start
    )
    seed_tagged = _seed_to_tagged_value(seed)
    rng_payload = _rng_state_to_jsonable(rng.getstate())
    items_digest = _items_fingerprint(items)
    schedule_digest = _weights_schedule_fingerprint(weights_schedule)
    schedule_length = len(weights_schedule)
    state = {
        "version": _CHECKPOINT_VERSION,
        "kind": _SCHEDULE_CHECKPOINT_KIND,
        "position": start,
        "k": k,
        "n": n,
        "schedule_length": schedule_length,
        "items_digest": items_digest,
        "schedule_digest": schedule_digest,
        "seed": seed_tagged,
        "rng": rng_payload,
    }
    state["digest"] = _schedule_checkpoint_binding_digest(
        seed_tagged, start, k, n, schedule_length,
        items_digest, schedule_digest, rng_payload,
    )
    return state


def _validate_schedule_checkpoint_state(state):
    """校验按轮计划断点状态本身的结构与版本, 返回规范化字段。

    调用前须已确认 state 是映射(否则 TypeError 在外层抛出)。字段缺失、
    未知(多余)字段、类型错误、非法取值、版本不支持、kind 不符等一切
    结构问题统一抛 ValueError。
    """
    required = ("version", "kind", "position", "k", "n", "schedule_length",
                "items_digest", "schedule_digest", "seed", "rng", "digest")
    if not all(key in state for key in required):
        raise ValueError("invalid checkpoint state: missing fields")
    if set(state) != set(required):
        raise ValueError("invalid checkpoint state: unexpected fields")

    version = state["version"]
    if (isinstance(version, bool) or not isinstance(version, int)
            or version != _CHECKPOINT_VERSION):
        raise ValueError("unsupported checkpoint version: %r" % (version,))
    if state["kind"] != _SCHEDULE_CHECKPOINT_KIND:
        raise ValueError("invalid checkpoint state: unexpected kind")
    position = state["position"]
    k = state["k"]
    n = state["n"]
    schedule_length = state["schedule_length"]
    for name, value in (("position", position), ("k", k), ("n", n),
                        ("schedule_length", schedule_length)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid checkpoint state: %s" % name)
    if k > n:
        raise ValueError("invalid checkpoint state: k exceeds n")
    for name in ("items_digest", "schedule_digest", "digest"):
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

    # 绑定摘要: 任何对字段的篡改(position、kind、计划长度、seed、RNG
    # 快照、指纹)若不附带重算的摘要, 都会在这里被发现 —— 因此恢复时
    # 不必从头重放随机流。
    expected_digest = _schedule_checkpoint_binding_digest(
        seed_payload, position, k, n, schedule_length,
        state["items_digest"], state["schedule_digest"], rng_payload,
    )
    if not hmac.compare_digest(expected_digest, state["digest"]):
        raise ValueError("invalid checkpoint state: digest mismatch")
    return (position, k, n, schedule_length, seed, rng_state, seed_payload)


def _resume_schedule_rounds_indices(items, weights_schedule, k, state, draws):
    """两个按轮计划恢复入口共用的已校验核心: 只产出索引轮次与下一状态。

    调用约定与 _resume_rounds_indices 相同: 外层已确认 state 是映射并
    校验过 draws。先用状态携带的 seed 按 weighted_sample_schedule_indices
    的固定顺序完成 items、weights_schedule、k、窗口 [position,
    position+draws) 的全部校验(恢复窗口超出计划范围在此以既有
    ValueError 拒绝), 再核对状态与当前输入的绑定(k/n、计划长度、items
    指纹、完整 schedule 指纹); 任一失败都在物化任何轮次之前抛出既有
    TypeError / ValueError, JSON / Decimal / random 层面的意外异常统一
    收敛为 ValueError。全部通过后直接从 RNG 快照续接, 每轮按该行的
    权重重建确定性抽样计划后抽样, 返回 (索引轮次, 下一状态); 不修改
    入参, 也不修改传入的状态映射。
    """
    (position, state_k, state_n, schedule_length, seed, rng_state,
     seed_payload) = _validate_schedule_checkpoint_state(state)

    # 与一次性批量入口同一套校验与窗口语义: draws/start 规则、行长度、
    # 权重取值与每一行可行性都在此确定; start=position、draws=draws 时
    # 窗口越界以 "schedule window out of range" 拒绝。
    n = _validate_schedule_inputs(
        items, weights_schedule, k, draws, seed, position
    )

    # 状态与当前采样输入的一致性: 计划长度先比, 再逐行核对完整指纹。
    if state_k != k or state_n != n:
        raise ValueError("checkpoint state does not match items/schedule/k")
    if schedule_length != len(weights_schedule):
        raise ValueError("checkpoint state does not match schedule")
    if state["items_digest"] != _items_fingerprint(items):
        raise ValueError("checkpoint state does not match items")
    if state["schedule_digest"] != _weights_schedule_fingerprint(
        weights_schedule
    ):
        raise ValueError("checkpoint state does not match weights schedule")

    # 全部校验通过后才物化轮次: 直接从快照状态继续。每轮的抽样计划由
    # (该行权重, k) 唯一确定, 与创建断点及一次性入口算出的计划逐轮相同,
    # 因此恢复结果与 weighted_sample_schedule_indices 的对应区间逐轮一致。
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
    for j in range(position, position + draws):
        planned_weights, use_exact = _select_sampling_plan(
            list(weights_schedule[j]), k
        )
        rounds.append(
            _draw_indices_once(n, planned_weights, k, rng, use_exact)
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
    next_state["digest"] = _schedule_checkpoint_binding_digest(
        seed_payload, next_position, k, n, schedule_length,
        state["items_digest"], state["schedule_digest"], next_rng_payload,
    )
    return rounds, next_state


def weighted_sample_schedule_resume_indices(
    items, weights_schedule, k, state, draws
):
    """从按轮权重计划断点继续产出索引轮次, 返回 (轮次列表, 下一状态)。

    第一轮从断点记录的位置开始; 逐轮结果与
    weighted_sample_schedule_indices(items, weights_schedule, k, draws,
    seed, start=position) 完全一致, 即等于一次性批量序列的零基区间
    [position, position+draws); 多次连续续接与一次性生成逐项相同,
    恢复时无需从头重放随机流。返回前完成与 schedule 批量入口一致的
    全部输入校验(含恢复窗口不超出计划范围), 并核对状态与 items、完整
    schedule、k 及 (seed, 位置, RNG 快照) 的自洽性: 状态不是映射抛
    TypeError; 字段缺失或未知、版本不支持、摘要或输入不匹配统一抛
    ValueError; items/weights_schedule/k/draws 的错误沿用既有
    TypeError / ValueError。所有失败都在任何轮次物化之前确定, 绝不返回
    部分轮次。draws=0 返回空轮次与位置不变的新状态; k=0 时每轮为空
    列表, 位置仍逐轮加一且不消耗随机流。状态可经 serialize_metrics /
    deserialize_metrics 往返后继续恢复。不修改入参, 也不修改传入的
    状态映射与 weights_schedule。
    """
    # 状态不是映射: TypeError(文档约定的明确分类)。映射前提下的一切
    # 结构/版本/摘要问题在 _validate_schedule_checkpoint_state 中统一为
    # ValueError。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    # draws 的类型/取值规则独立于状态, 先按既有规则校验(TypeError /
    # ValueError), 再解析状态。
    _validate_draws(draws)
    return _resume_schedule_rounds_indices(
        items, weights_schedule, k, state, draws
    )


def weighted_sample_schedule_resume(items, weights_schedule, k, state, draws):
    """按元素值从按轮权重计划断点继续, 返回 (元素值轮次列表, 下一状态)。

    校验顺序按恢复入口约定固定: 调用开始先按现有 schedule 入口完成
    items、weights_schedule、k 的结构、行长度、权重取值、范围与每一行
    正权重可行性校验(这部分与 seed 无关, 以合法种子 0 试跑; state 携带
    的 seed 其标签化编码随后随 state 一并校验), 再按现有恢复入口校验
    state 的映射类型、版本、字段集合、摘要、随机数状态以及 state 与当前
    输入的绑定(含恢复窗口范围), draws 必须是非布尔非负整数。状态不是
    映射抛 TypeError; 非法状态、版本不支持、状态与输入不匹配、正权重
    不足或恢复窗口超出计划范围等一律抛 ValueError; 其余输入错误沿用既有
    TypeError / ValueError。所有失败都在产生任何轮次之前确定,
    JSON / Decimal / random 的异常不会以其他类型泄漏。

    每轮返回元素值列表, 与 weighted_sample_schedule_resume_indices
    返回的每轮原始位置逐项对应(第 j 个值恰为 items[第 j 个索引]):
    相同值的不同位置分别消耗, 轮内不会出现重复位置。返回的下一状态与
    按索引入口产出的完全相同(position、RNG 快照、digest 一致), 只含
    JSON 原生值, 可直接再次传入本入口或按索引入口, 或经
    serialize_metrics / deserialize_metrics 往返后继续恢复。draws=0
    返回空轮次与位置、随机状态不变的状态副本; k=0 时生成 draws 个空
    列表并按轮数推进 position, 不消耗随机流。不修改入参, 也不修改传入
    的状态映射与 weights_schedule。
    """
    # 第一步: 先按现有 schedule 入口完成 items、weights_schedule、k 的
    # 结构、行长度、权重取值、范围与可行性校验(draws/start 以 0 试跑,
    # 窗口必然合法)。这些检查只用到 seed 的类型, 与 state 中 seed 的
    # 具体值无关; 因此即使 state 本身已损坏, 非法 items/schedule/k 仍
    # 优先以 schedule 入口的异常类别报告。
    _validate_schedule_inputs(items, weights_schedule, k, 0, 0, 0)

    # 第二步: 恢复入口的映射类型检查与 draws 规则(TypeError / ValueError)。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    _validate_draws(draws)

    # 第三步: 状态结构/版本/字段/摘要/RNG、state 与输入绑定(含从状态
    # 解出的 seed 再跑一次完整 schedule 校验与窗口检查), 全部通过后从
    # RNG 快照续接产出索引轮次。与按索引入口共用同一个已校验核心,
    # 因此轮次内容、下一状态、异常类别与其逐项一致。
    index_rounds, next_state = _resume_schedule_rounds_indices(
        items, weights_schedule, k, state, draws
    )
    # 按每轮原始位置逐项映射为元素值: 相同值的不同位置各自独立映射,
    # 轮内不重复位置这一性质随索引结果原样保留。只读取 items, 不修改入参。
    rounds = [[items[i] for i in round_indices] for round_indices in index_rounds]
    return rounds, next_state


# ---------------------------------------------------------------------------
# 可暂停 / 恢复的按轮样本数计划采样会话
# ---------------------------------------------------------------------------

_K_SCHEDULE_CHECKPOINT_KIND = "k_schedule"


def _k_schedule_fingerprint(k_schedule):
    """对完整的按轮样本数计划取指纹: 逐项带位置规范化后整体 sha256。

    项的零基下标与精确十进制值都参与指纹, 因此调换、增删或改动任一项都
    会改变指纹; 成员在调用前已通过 _validate_k_schedule_inputs 校验
    (非布尔非负整数), 超大整数也按精确十进制处理, 不经过浮点。
    """
    digest = hashlib.sha256()
    for index, member in enumerate(k_schedule):
        digest.update(
            ("%d:%s\n" % (index, _int_to_decimal_text(member))).encode(
                "utf-8"
            )
        )
    return digest.hexdigest()


def _k_schedule_checkpoint_binding_digest(
    seed_tagged, position, n, schedule_length, items_digest,
    weights_digest, k_schedule_digest, exact, rng_payload,
):
    """把按轮样本数计划断点各字段绑定为一个防篡改摘要。

    与 _checkpoint_binding_digest 同一构造(serialize_metrics 规范化后
    sha256), 绑定标签 kind、position、n、计划长度、items / weights /
    k_schedule 的指纹、抽样路径标记 exact、标签化 seed 与 RNG 快照:
    任一字段被改动而不重算摘要时, 恢复都会在产出任何轮次前发现, 因此
    长计划分段交接无需从头重放随机流。
    """
    return _hash_text(serialize_metrics({
        "kind": _K_SCHEDULE_CHECKPOINT_KIND,
        "seed": seed_tagged,
        "position": position,
        "n": n,
        "schedule_length": schedule_length,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "k_schedule_digest": k_schedule_digest,
        "exact": exact,
        "rng": rng_payload,
    }))


def _prepare_validated_k_schedule_session(items, weights, k_schedule, seed,
                                          start):
    """按轮样本数计划断点入口共用的前置准备: 与批量入口一致的校验与跳轮。

    以 draws=0 复用 k_schedule 的全部前置校验(items、weights、seed、
    k_schedule 结构与成员类型/取值、窗口范围、权重取值与每一轮的正权重
    可行性), 因此创建断点不产出任何轮次却仍完成全部校验; 随后把随机流
    推进到 "已完成 start 轮" 的位置 —— 被跳过的第 j 轮按 k_schedule[j]
    的样本数消耗同一条由 seed 初始化的随机流, 样本数为零的轮次不消耗
    随机流, 与一次性批量入口的跳过节奏完全一致。返回 (n, rng, use_exact):
    use_exact 是样本数为正的轮次共用的抽样路径标记(固定权重下所有正
    样本数轮次的抽样计划相同)。不修改入参与 k_schedule。
    """
    n = _validate_k_schedule_inputs(
        items, weights, k_schedule, 0, seed, start
    )
    pool_weights = list(weights)
    rng = random.Random(seed)
    # 抽样路径标记: 固定权重下所有正样本数轮次的计划相同(_select_sampling_
    # plan 对任意 k>0 给出同一结果), 以正样本数代表(取 1)求得的标记即代表
    # 全部正轮次; 全零计划下该标记不参与抽样, 仍记录以保持状态结构一致。
    _, use_exact = _select_sampling_plan(pool_weights, 1)
    for j in range(start):
        member = k_schedule[j]
        if member > 0:
            planned_weights, round_exact = _select_sampling_plan(
                pool_weights, member
            )
            _draw_indices_once(n, planned_weights, member, rng, round_exact)
    return n, rng, use_exact


def weighted_sample_k_schedule_checkpoint(items, weights, k_schedule,
                                          seed=0, start=0):
    """创建按轮样本数计划采样会话的断点(只含 JSON 原生值的状态映射)。

    校验沿用 weighted_sample_k_schedule_indices 的全部规则与固定顺序:
    items、weights、seed 与既有采样入口一致; k_schedule 必须是有限非
    文本且长度可确定的序列, 每个成员都是非布尔非负整数且不超过 items
    长度; 权重元素继续接受非布尔 int、有限非负 float、Fraction、
    Decimal(可混合, 超大整数、Fraction、Decimal 不经过浮点); 负数、
    NaN、无穷权重、错误结构或任一轮样本数超过正权重位置数一律拒绝。
    draws 恒按 0 处理(本入口不产出轮次), start 必须是非布尔非负整数
    且不越过计划长度(start == 计划长度允许, 表示整批已完成)。全部校验
    在返回状态前完成, 失败不返回部分结果, 也不修改入参与 k_schedule。

    校验通过后先完成 start 个完整轮次(第 j 轮按 k_schedule[j] 的样本数
    消耗同一条由 seed 初始化的随机流, 样本数为零的轮次不消耗随机流),
    再返回当前位置与只含 JSON 原生值的状态; 状态绑定版本、标签 kind、
    position、n、计划长度、items / weights / k_schedule 指纹、标签化
    seed、抽样路径标记、随机流快照与完整性摘要, 可直接交给
    serialize_metrics 落盘, 也可经 deserialize_metrics 还原(甚至跨
    进程)后交给 weighted_sample_k_schedule_resume_indices 恢复。
    """
    n, rng, use_exact = _prepare_validated_k_schedule_session(
        items, weights, k_schedule, seed, start
    )
    seed_tagged = _seed_to_tagged_value(seed)
    rng_payload = _rng_state_to_jsonable(rng.getstate())
    items_digest = _items_fingerprint(items)
    weights_digest = _weights_fingerprint(weights)
    k_schedule_digest = _k_schedule_fingerprint(k_schedule)
    schedule_length = len(k_schedule)
    state = {
        "version": _CHECKPOINT_VERSION,
        "kind": _K_SCHEDULE_CHECKPOINT_KIND,
        "position": start,
        "n": n,
        "schedule_length": schedule_length,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "k_schedule_digest": k_schedule_digest,
        "seed": seed_tagged,
        "exact": bool(use_exact),
        "rng": rng_payload,
    }
    state["digest"] = _k_schedule_checkpoint_binding_digest(
        seed_tagged, start, n, schedule_length, items_digest,
        weights_digest, k_schedule_digest, bool(use_exact), rng_payload,
    )
    return state


def _validate_k_schedule_checkpoint_state(state):
    """校验按轮样本数计划断点状态本身的结构与版本, 返回规范化字段。

    调用前须已确认 state 是映射(否则 TypeError 在外层抛出)。字段缺失、
    未知(多余)字段、类型错误、非法取值、版本不支持、kind 不符等一切
    结构问题统一抛 ValueError。
    """
    required = ("version", "kind", "position", "n", "schedule_length",
                "items_digest", "weights_digest", "k_schedule_digest",
                "seed", "exact", "rng", "digest")
    if not all(key in state for key in required):
        raise ValueError("invalid checkpoint state: missing fields")
    if set(state) != set(required):
        raise ValueError("invalid checkpoint state: unexpected fields")

    version = state["version"]
    if (isinstance(version, bool) or not isinstance(version, int)
            or version != _CHECKPOINT_VERSION):
        raise ValueError("unsupported checkpoint version: %r" % (version,))
    if state["kind"] != _K_SCHEDULE_CHECKPOINT_KIND:
        raise ValueError("invalid checkpoint state: unexpected kind")
    position = state["position"]
    n = state["n"]
    schedule_length = state["schedule_length"]
    for name, value in (("position", position), ("n", n),
                        ("schedule_length", schedule_length)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid checkpoint state: %s" % name)
    if not isinstance(state["exact"], bool):
        raise ValueError("invalid checkpoint state: exact")
    for name in ("items_digest", "weights_digest", "k_schedule_digest",
                 "digest"):
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

    # 绑定摘要: 任何对字段的篡改(position、kind、计划长度、抽样路径标记、
    # seed、RNG 快照、指纹)若不附带重算的摘要, 都会在这里被发现 —— 因此
    # 恢复时不必从头重放随机流。
    expected_digest = _k_schedule_checkpoint_binding_digest(
        seed_payload, position, n, schedule_length,
        state["items_digest"], state["weights_digest"],
        state["k_schedule_digest"], state["exact"], rng_payload,
    )
    if not hmac.compare_digest(expected_digest, state["digest"]):
        raise ValueError("invalid checkpoint state: digest mismatch")
    return (position, n, schedule_length, state["exact"], seed, rng_state,
            seed_payload)


def _resume_k_schedule_rounds_indices(items, weights, k_schedule, state,
                                      draws):
    """两个按轮样本数计划恢复入口共用的已校验核心: 只产出索引轮次与下一状态。

    调用约定与 _resume_rounds_indices 相同: 外层已确认 state 是映射并
    校验过 draws。先用状态携带的 seed 按 weighted_sample_k_schedule_
    indices 的固定顺序完成 items、weights、k_schedule、窗口
    [position, position+draws) 的全部校验(恢复窗口超出计划范围在此以
    既有 ValueError 拒绝), 再核对状态与当前输入的绑定(n、计划长度、
    items / weights / 完整 k_schedule 指纹)与抽样路径标记; 任一失败都
    在物化任何轮次之前抛出既有 TypeError / ValueError, JSON / Decimal /
    random 层面的意外异常统一收敛为 ValueError。全部通过后直接从 RNG
    快照续接, 样本数为正的轮次按固定权重重建确定性抽样计划后抽样,
    样本数为零的轮次产出空列表且不消耗随机流, 返回 (索引轮次, 下一
    状态); 不修改入参, 也不修改传入的状态映射与 k_schedule。
    """
    (position, state_n, schedule_length, use_exact, seed, rng_state,
     seed_payload) = _validate_k_schedule_checkpoint_state(state)

    # 与一次性批量入口同一套校验与窗口语义: draws/start 规则、计划成员
    # 取值、权重取值与每一轮可行性都在此确定; start=position、draws=draws
    # 时窗口越界以 "schedule window out of range" 拒绝。
    n = _validate_k_schedule_inputs(
        items, weights, k_schedule, draws, seed, position
    )

    # 状态与当前采样输入的一致性: 计划长度先比, 再逐项核对完整指纹。
    if state_n != n:
        raise ValueError("checkpoint state does not match items/weights")
    if schedule_length != len(k_schedule):
        raise ValueError("checkpoint state does not match k_schedule")
    if state["items_digest"] != _items_fingerprint(items):
        raise ValueError("checkpoint state does not match items")
    if state["weights_digest"] != _weights_fingerprint(weights):
        raise ValueError("checkpoint state does not match weights")
    if state["k_schedule_digest"] != _k_schedule_fingerprint(k_schedule):
        raise ValueError("checkpoint state does not match k_schedule")

    # 抽样路径标记必须与创建断点时一致: 固定权重下所有正样本数轮次共用
    # 同一计划, 以正样本数代表(取 1)重建并比对 exact 标志。RNG 快照与
    # (seed, position) 的绑定已由状态摘要保证未被篡改, 故恢复直接从快照
    # 继续, 无需从头重放。
    planned_weights, planned_exact = _select_sampling_plan(list(weights), 1)
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
    for j in range(position, position + draws):
        member = k_schedule[j]
        if member > 0:
            rounds.append(
                _draw_indices_once(
                    n, planned_weights, member, rng, planned_exact
                )
            )
        else:
            # 样本数为零的轮次返回空列表且不消耗随机流。
            rounds.append([])

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
    next_state["digest"] = _k_schedule_checkpoint_binding_digest(
        seed_payload, next_position, n, schedule_length,
        state["items_digest"], state["weights_digest"],
        state["k_schedule_digest"], planned_exact, next_rng_payload,
    )
    return rounds, next_state


def weighted_sample_k_schedule_resume_indices(items, weights, k_schedule,
                                              state, draws):
    """从按轮样本数计划断点继续产出索引轮次, 返回 (轮次列表, 下一状态)。

    第一轮从断点记录的位置开始; 逐轮结果与
    weighted_sample_k_schedule_indices(items, weights, k_schedule,
    draws, seed, start=position) 完全一致, 即等于一次性批量序列的零基
    区间 [position, position+draws); 多次连续续接与一次性生成逐项相同,
    恢复时无需从头重放随机流。返回前完成与 k_schedule 批量入口一致的
    全部输入校验(含恢复窗口不超出计划范围), 并核对状态与 items、
    weights、完整 k_schedule 及 (seed, 位置, RNG 快照) 的自洽性: 状态
    不是映射抛 TypeError; 字段缺失或未知、版本或 kind 不支持、摘要或
    输入不匹配、抽样路径标记不一致统一抛 ValueError;
    items/weights/k_schedule/draws 的错误沿用既有 TypeError /
    ValueError。所有失败都在任何轮次物化之前确定, 绝不返回部分轮次。
    draws=0 返回空轮次与位置不变的新状态; 样本数为零的轮次返回空列表,
    位置仍逐轮加一且不消耗随机流。状态可经 serialize_metrics /
    deserialize_metrics 往返后继续恢复。不修改入参, 也不修改传入的
    状态映射与 k_schedule。
    """
    # 状态不是映射: TypeError(文档约定的明确分类)。映射前提下的一切
    # 结构/版本/摘要问题在 _validate_k_schedule_checkpoint_state 中统一
    # 为 ValueError。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    # draws 的类型/取值规则独立于状态, 先按既有规则校验(TypeError /
    # ValueError), 再解析状态。
    _validate_draws(draws)
    return _resume_k_schedule_rounds_indices(
        items, weights, k_schedule, state, draws
    )


def weighted_sample_k_schedule_resume(items, weights, k_schedule, state,
                                      draws):
    """按元素值从按轮样本数计划断点继续, 返回 (元素值轮次列表, 下一状态)。

    校验顺序按恢复入口约定固定: 调用开始先按现有 k_schedule 入口完成
    items、weights、k_schedule 的结构、成员类型/取值、权重取值与每一轮
    正权重可行性校验(这部分与 seed 无关, 以合法种子 0 试跑; state 携带
    的 seed 其标签化编码随后随 state 一并校验), 再按现有恢复入口校验
    state 的映射类型、版本、kind、字段集合、摘要、随机数状态以及 state
    与当前输入的绑定(含恢复窗口范围与抽样路径标记), draws 必须是非布尔
    非负整数。状态不是映射抛 TypeError; 非法状态、版本或 kind 不支持、
    状态与输入不匹配、正权重不足或恢复窗口超出计划范围等一律抛
    ValueError; 其余输入错误沿用既有 TypeError / ValueError。所有失败
    都在产生任何轮次之前确定, JSON / Decimal / random 的异常不会以其他
    类型泄漏。

    每轮返回元素值列表, 与 weighted_sample_k_schedule_resume_indices
    返回的每轮原始位置逐项对应(第 j 个值恰为 items[第 j 个索引]):
    相同值的不同位置分别消耗, 轮内不会出现重复位置。返回的下一状态与
    按索引入口产出的完全相同(position、RNG 快照、digest 一致), 只含
    JSON 原生值, 可直接再次传入本入口或按索引入口, 或经
    serialize_metrics / deserialize_metrics 往返后继续恢复。draws=0
    返回空轮次与位置、随机状态不变的状态副本; 样本数为零的轮次生成
    空列表并按轮数推进 position, 不消耗随机流。不修改入参, 也不修改
    传入的状态映射与 k_schedule。
    """
    # 第一步: 先按现有 k_schedule 入口完成 items、weights、k_schedule 的
    # 结构、成员类型/取值、权重取值与可行性校验(draws/start 以 0 试跑,
    # 窗口必然合法)。这些检查只用到 seed 的类型, 与 state 中 seed 的具体
    # 值无关; 因此即使 state 本身已损坏, 非法 items/weights/k_schedule
    # 仍优先以 k_schedule 入口的异常类别报告。
    _validate_k_schedule_inputs(items, weights, k_schedule, 0, 0, 0)

    # 第二步: 恢复入口的映射类型检查与 draws 规则(TypeError / ValueError)。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    _validate_draws(draws)

    # 第三步: 状态结构/版本/kind/字段/摘要/RNG、state 与输入绑定(含从
    # 状态解出的 seed 再跑一次完整 k_schedule 校验与窗口检查)、抽样路径
    # 标记核对, 全部通过后从 RNG 快照续接产出索引轮次。与按索引入口共用
    # 同一个已校验核心, 因此轮次内容、下一状态、异常类别与其逐项一致。
    index_rounds, next_state = _resume_k_schedule_rounds_indices(
        items, weights, k_schedule, state, draws
    )
    # 按每轮原始位置逐项映射为元素值: 相同值的不同位置各自独立映射,
    # 轮内不重复位置这一性质随索引结果原样保留。只读取 items, 不修改入参。
    rounds = [[items[i] for i in round_indices] for round_indices in index_rounds]
    return rounds, next_state


# ---------------------------------------------------------------------------
# 可暂停 / 恢复的按轮权重与样本数联合计划采样会话
# ---------------------------------------------------------------------------

_PLAN_CHECKPOINT_KIND = "plan"


def _plan_checkpoint_binding_digest(
    seed_tagged, position, n, schedule_length, items_digest,
    schedule_digest, k_schedule_digest, rng_payload,
):
    """把联合计划断点各字段绑定为一个防篡改摘要。

    与 _checkpoint_binding_digest 同一构造(serialize_metrics 规范化后
    sha256), 绑定标签 kind、position、n、计划长度、items / 完整
    weights_schedule / 完整 k_schedule 的指纹、标签化 seed 与 RNG 快照:
    任一字段被改动而不重算摘要时, 恢复都会在产出任何轮次前发现, 因此
    长计划分段交接无需从头重放随机流。
    """
    return _hash_text(serialize_metrics({
        "kind": _PLAN_CHECKPOINT_KIND,
        "seed": seed_tagged,
        "position": position,
        "n": n,
        "schedule_length": schedule_length,
        "items_digest": items_digest,
        "schedule_digest": schedule_digest,
        "k_schedule_digest": k_schedule_digest,
        "rng": rng_payload,
    }))


def _prepare_validated_plan_session(items, weights_schedule, k_schedule,
                                    seed, start):
    """联合计划断点入口共用的前置准备: 与批量入口一致的校验与跳轮。

    以 draws=0 复用联合计划的全部前置校验(items、seed、两个计划的结构与
    成员类型/取值、计划等长、窗口范围、每一行权重取值与每一轮的正权重
    可行性), 因此创建断点不产出任何轮次却仍完成全部校验; 随后把随机流
    推进到 "已完成 start 轮" 的位置 —— 被跳过的第 j 轮按
    weights_schedule[j] 的权重与 k_schedule[j] 的样本数消耗同一条由
    seed 初始化的随机流, 样本数为零的轮次不消耗随机流, 与一次性批量入口
    的跳过节奏完全一致。返回 (n, rng); 每行权重都复制为本地计划, 绝不
    修改入参与两个计划。
    """
    n = _validate_plan_inputs(
        items, weights_schedule, k_schedule, 0, seed, start
    )
    rng = random.Random(seed)
    # 只构造被跳过轮次的计划; 每行复制一份权重, 绝不修改 schedule。
    for j in range(start):
        member = k_schedule[j]
        if member > 0:
            planned_weights, use_exact = _select_sampling_plan(
                list(weights_schedule[j]), member
            )
            _draw_indices_once(n, planned_weights, member, rng, use_exact)
    return n, rng


def weighted_sample_plan_checkpoint(items, weights_schedule, k_schedule,
                                    seed=0, start=0):
    """创建按轮权重与样本数联合计划采样会话的断点(只含 JSON 原生值的
    状态映射)。

    校验沿用 weighted_sample_plan_indices 的全部规则与固定顺序: items、
    seed 与既有采样入口一致; weights_schedule 必须是有限非文本且长度可
    确定的序列, 每个成员都是与 items 等长的同类序列; k_schedule 是等长
    的有限非文本序列, 每个成员都是非布尔非负整数且不超过 items 长度;
    权重元素继续接受非布尔 int、有限非负 float、Fraction、Decimal(可
    混合, 超大整数、Fraction、Decimal 不经过浮点); 负数、NaN、无穷权重、
    错误结构、两个计划不等长或任一轮样本数超过对应行正权重位置数一律
    拒绝。draws 恒按 0 处理(本入口不产出轮次), start 必须是非布尔非负
    整数且不越过计划长度(start == 计划长度允许, 表示整批已完成)。全部
    校验在返回状态前完成, 失败不返回部分结果, 也不修改入参与两个计划。

    校验通过后先完成 start 个完整轮次(第 j 轮按 weights_schedule[j] 的
    权重与 k_schedule[j] 的样本数消耗同一条由 seed 初始化的随机流,
    样本数为零的轮次不消耗随机流), 再返回当前位置与只含 JSON 原生值的
    状态; 状态绑定版本、标签 kind、position、n、计划长度、items / 完整
    weights_schedule / 完整 k_schedule 指纹、标签化 seed、随机流快照与
    完整性摘要, 可直接交给 serialize_metrics 落盘, 也可经
    deserialize_metrics 还原(甚至跨进程)后交给
    weighted_sample_plan_resume_indices 恢复。
    """
    n, rng = _prepare_validated_plan_session(
        items, weights_schedule, k_schedule, seed, start
    )
    seed_tagged = _seed_to_tagged_value(seed)
    rng_payload = _rng_state_to_jsonable(rng.getstate())
    items_digest = _items_fingerprint(items)
    schedule_digest = _weights_schedule_fingerprint(weights_schedule)
    k_schedule_digest = _k_schedule_fingerprint(k_schedule)
    schedule_length = len(k_schedule)
    state = {
        "version": _CHECKPOINT_VERSION,
        "kind": _PLAN_CHECKPOINT_KIND,
        "position": start,
        "n": n,
        "schedule_length": schedule_length,
        "items_digest": items_digest,
        "schedule_digest": schedule_digest,
        "k_schedule_digest": k_schedule_digest,
        "seed": seed_tagged,
        "rng": rng_payload,
    }
    state["digest"] = _plan_checkpoint_binding_digest(
        seed_tagged, start, n, schedule_length, items_digest,
        schedule_digest, k_schedule_digest, rng_payload,
    )
    return state


def _validate_plan_checkpoint_state(state):
    """校验联合计划断点状态本身的结构与版本, 返回规范化字段。

    调用前须已确认 state 是映射(否则 TypeError 在外层抛出)。字段缺失、
    未知(多余)字段、类型错误、非法取值、版本不支持、kind 不符等一切
    结构问题统一抛 ValueError。
    """
    required = ("version", "kind", "position", "n", "schedule_length",
                "items_digest", "schedule_digest", "k_schedule_digest",
                "seed", "rng", "digest")
    if not all(key in state for key in required):
        raise ValueError("invalid checkpoint state: missing fields")
    if set(state) != set(required):
        raise ValueError("invalid checkpoint state: unexpected fields")

    version = state["version"]
    if (isinstance(version, bool) or not isinstance(version, int)
            or version != _CHECKPOINT_VERSION):
        raise ValueError("unsupported checkpoint version: %r" % (version,))
    if state["kind"] != _PLAN_CHECKPOINT_KIND:
        raise ValueError("invalid checkpoint state: unexpected kind")
    position = state["position"]
    n = state["n"]
    schedule_length = state["schedule_length"]
    for name, value in (("position", position), ("n", n),
                        ("schedule_length", schedule_length)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid checkpoint state: %s" % name)
    for name in ("items_digest", "schedule_digest", "k_schedule_digest",
                 "digest"):
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

    # 绑定摘要: 任何对字段的篡改(position、kind、计划长度、seed、RNG
    # 快照、指纹)若不附带重算的摘要, 都会在这里被发现 —— 因此恢复时
    # 不必从头重放随机流。
    expected_digest = _plan_checkpoint_binding_digest(
        seed_payload, position, n, schedule_length,
        state["items_digest"], state["schedule_digest"],
        state["k_schedule_digest"], rng_payload,
    )
    if not hmac.compare_digest(expected_digest, state["digest"]):
        raise ValueError("invalid checkpoint state: digest mismatch")
    return (position, n, schedule_length, seed, rng_state, seed_payload)


def _resume_plan_rounds_indices(items, weights_schedule, k_schedule, state,
                                draws):
    """两个联合计划恢复入口共用的已校验核心: 只产出索引轮次与下一状态。

    调用约定与 _resume_rounds_indices 相同: 外层已确认 state 是映射并
    校验过 draws。先用状态携带的 seed 按 weighted_sample_plan_indices 的
    固定顺序完成 items、weights_schedule、k_schedule、窗口
    [position, position+draws) 的全部校验(恢复窗口超出计划范围在此以
    既有 ValueError 拒绝), 再核对状态与当前输入的绑定(n、计划长度、
    items 指纹、完整 weights_schedule 指纹、完整 k_schedule 指纹); 任一
    失败都在物化任何轮次之前抛出既有 TypeError / ValueError, JSON /
    Decimal / random 层面的意外异常统一收敛为 ValueError。全部通过后
    直接从 RNG 快照续接, 每轮按该行的权重与该轮的样本数重建确定性抽样
    计划后抽样, 样本数为零的轮次产出空列表且不消耗随机流, 返回
    (索引轮次, 下一状态); 不修改入参, 也不修改传入的状态映射与两个计划。
    """
    (position, state_n, schedule_length, seed, rng_state,
     seed_payload) = _validate_plan_checkpoint_state(state)

    # 与一次性批量入口同一套校验与窗口语义: draws/start 规则、行长度、
    # 计划等长、成员取值、权重取值与每一轮可行性都在此确定;
    # start=position、draws=draws 时窗口越界以 "schedule window out of
    # range" 拒绝。
    n = _validate_plan_inputs(
        items, weights_schedule, k_schedule, draws, seed, position
    )

    # 状态与当前采样输入的一致性: 计划长度先比, 再逐项核对完整指纹。
    if state_n != n:
        raise ValueError("checkpoint state does not match items/schedules")
    if schedule_length != len(k_schedule):
        raise ValueError("checkpoint state does not match schedules")
    if state["items_digest"] != _items_fingerprint(items):
        raise ValueError("checkpoint state does not match items")
    if state["schedule_digest"] != _weights_schedule_fingerprint(
        weights_schedule
    ):
        raise ValueError("checkpoint state does not match weights schedule")
    if state["k_schedule_digest"] != _k_schedule_fingerprint(k_schedule):
        raise ValueError("checkpoint state does not match k_schedule")

    # 全部校验通过后才物化轮次: 直接从快照状态继续。每轮的抽样计划由
    # (该行权重, 该轮样本数) 唯一确定, 与创建断点及一次性入口算出的计划
    # 逐轮相同, 因此恢复结果与 weighted_sample_plan_indices 的对应区间
    # 逐轮一致。RNG 快照与 (seed, position) 的绑定已由状态摘要保证未被
    # 篡改, 故恢复直接从快照继续, 无需从头重放。
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
    for j in range(position, position + draws):
        member = k_schedule[j]
        if member > 0:
            planned_weights, use_exact = _select_sampling_plan(
                list(weights_schedule[j]), member
            )
            rounds.append(
                _draw_indices_once(n, planned_weights, member, rng, use_exact)
            )
        else:
            # 样本数为零的轮次返回空列表且不消耗随机流。
            rounds.append([])

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
    next_state["digest"] = _plan_checkpoint_binding_digest(
        seed_payload, next_position, n, schedule_length,
        state["items_digest"], state["schedule_digest"],
        state["k_schedule_digest"], next_rng_payload,
    )
    return rounds, next_state


def weighted_sample_plan_resume_indices(items, weights_schedule, k_schedule,
                                        state, draws):
    """从联合计划断点继续产出索引轮次, 返回 (轮次列表, 下一状态)。

    第一轮从断点记录的位置开始; 逐轮结果与
    weighted_sample_plan_indices(items, weights_schedule, k_schedule,
    draws, seed, start=position) 完全一致, 即等于一次性批量序列的零基
    区间 [position, position+draws); 多次连续续接与一次性生成逐项相同,
    恢复时无需从头重放随机流。返回前完成与联合计划批量入口一致的全部
    输入校验(含恢复窗口不超出计划范围), 并核对状态与 items、完整
    weights_schedule、完整 k_schedule 及 (seed, 位置, RNG 快照) 的
    自洽性: 状态不是映射抛 TypeError; 字段缺失或未知、版本或 kind 不
    支持、摘要或输入不匹配统一抛 ValueError; items / weights_schedule /
    k_schedule / draws 的错误沿用既有 TypeError / ValueError。所有失败
    都在任何轮次物化之前确定, 绝不返回部分轮次。draws=0 返回空轮次与
    位置不变的新状态; 样本数为零的轮次返回空列表, 位置仍逐轮加一且不
    消耗随机流。状态可经 serialize_metrics / deserialize_metrics 往返后
    继续恢复。不修改入参, 也不修改传入的状态映射与两个计划。
    """
    # 状态不是映射: TypeError(文档约定的明确分类)。映射前提下的一切
    # 结构/版本/摘要问题在 _validate_plan_checkpoint_state 中统一为
    # ValueError。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    # draws 的类型/取值规则独立于状态, 先按既有规则校验(TypeError /
    # ValueError), 再解析状态。
    _validate_draws(draws)
    return _resume_plan_rounds_indices(
        items, weights_schedule, k_schedule, state, draws
    )


def weighted_sample_plan_resume(items, weights_schedule, k_schedule, state,
                                draws):
    """按元素值从联合计划断点继续, 返回 (元素值轮次列表, 下一状态)。

    校验顺序按恢复入口约定固定: 调用开始先按现有联合计划入口完成
    items、weights_schedule、k_schedule 的结构、成员类型/取值、计划等长、
    权重取值与每一轮正权重可行性校验(这部分与 seed 无关, 以合法种子 0
    试跑; state 携带的 seed 其标签化编码随后随 state 一并校验), 再按
    现有恢复入口校验 state 的映射类型、版本、kind、字段集合、摘要、
    随机数状态以及 state 与当前输入的绑定(含恢复窗口范围), draws 必须是
    非布尔非负整数。状态不是映射抛 TypeError; 非法状态、版本或 kind 不
    支持、状态与输入不匹配、正权重不足或恢复窗口超出计划范围等一律抛
    ValueError; 其余输入错误沿用既有 TypeError / ValueError。所有失败
    都在产生任何轮次之前确定, JSON / Decimal / random 的异常不会以其他
    类型泄漏。

    每轮返回元素值列表, 与 weighted_sample_plan_resume_indices 返回的
    每轮原始位置逐项对应(第 j 个值恰为 items[第 j 个索引]): 相同值的
    不同位置分别消耗, 轮内不会出现重复位置。返回的下一状态与按索引入口
    产出的完全相同(position、RNG 快照、digest 一致), 只含 JSON 原生值,
    可直接再次传入本入口或按索引入口, 或经 serialize_metrics /
    deserialize_metrics 往返后继续恢复。draws=0 返回空轮次与位置、随机
    状态不变的状态副本; 样本数为零的轮次生成空列表并按轮数推进
    position, 不消耗随机流。不修改入参, 也不修改传入的状态映射与两个
    计划。
    """
    # 第一步: 先按现有联合计划入口完成 items、weights_schedule、
    # k_schedule 的结构、成员类型/取值、权重取值与可行性校验(draws/start
    # 以 0 试跑, 窗口必然合法)。这些检查只用到 seed 的类型, 与 state 中
    # seed 的具体值无关; 因此即使 state 本身已损坏, 非法
    # items/weights_schedule/k_schedule 仍优先以联合计划入口的异常类别
    # 报告。
    _validate_plan_inputs(items, weights_schedule, k_schedule, 0, 0, 0)

    # 第二步: 恢复入口的映射类型检查与 draws 规则(TypeError / ValueError)。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    _validate_draws(draws)

    # 第三步: 状态结构/版本/kind/字段/摘要/RNG、state 与输入绑定(含从
    # 状态解出的 seed 再跑一次完整联合计划校验与窗口检查), 全部通过后从
    # RNG 快照续接产出索引轮次。与按索引入口共用同一个已校验核心, 因此
    # 轮次内容、下一状态、异常类别与其逐项一致。
    index_rounds, next_state = _resume_plan_rounds_indices(
        items, weights_schedule, k_schedule, state, draws
    )
    # 按每轮原始位置逐项映射为元素值: 相同值的不同位置各自独立映射,
    # 轮内不重复位置这一性质随索引结果原样保留。只读取 items, 不修改入参。
    rounds = [[items[i] for i in round_indices] for round_indices in index_rounds]
    return rounds, next_state


# ---------------------------------------------------------------------------
# 可暂停 / 恢复的分组采样会话
# ---------------------------------------------------------------------------

_PARTITION_CHECKPOINT_KIND = "partition"


def _validate_partition_inputs(items, weights, group_sizes, seed):
    """分组采样入口共用的全部前置校验, 返回 (n, group_sizes 的本地副本)。

    校验顺序固定: 先 items、weights、seed 的结构/类型(与既有采样入口同一
    套规则, TypeError), 再 group_sizes 的结构(有限非文本且长度可确定的
    序列)与每个成员的类型(非布尔整数, TypeError); 随后 weights 长度与
    items 一致、每个组成员非负(ValueError); 接着权重元素类型(TypeError)
    与取值(ValueError)校验; 最后校验组大小总和不超过正权重位置数
    (ValueError)。空计划、全零组大小及权重总量为零(总和为零且总组大小
    也为零)同样通过校验。全部校验在产生任何分组前完成, 不修改入参。
    """
    # ---- 1. 结构与参数类型 (TypeError) ----
    if not _is_length_determinable_sequence(items):
        raise TypeError("items must be a length-determinable sequence")
    if not _is_length_determinable_sequence(weights):
        raise TypeError("weights must be a length-determinable sequence")
    if not isinstance(seed, _SEED_TYPES):
        raise TypeError("unsupported seed type: %s" % type(seed).__name__)
    if not _is_length_determinable_sequence(group_sizes):
        raise TypeError("group_sizes must be a length-determinable sequence")
    groups = []
    for member in group_sizes:
        if isinstance(member, bool) or not isinstance(member, int):
            raise TypeError("group_sizes members must be non-boolean integers")
        groups.append(member)

    # ---- 2. 长度与组大小取值 (ValueError) ----
    n = len(items)
    if len(weights) != n:
        raise ValueError("invalid sample size")
    for member in groups:
        if member < 0:
            raise ValueError("group sizes must be non-negative")

    # ---- 3. 权重元素类型与取值 (TypeError / ValueError) ----
    _validate_weight_elements(weights)

    # ---- 4. 总组大小的正权重可行性 (ValueError) ----
    total = sum(groups)
    if total > _count_positive_weights(weights):
        raise ValueError("no positive weight")
    return n, groups


def _split_groups(sequence, groups):
    """把一次性序列按累计组大小切成多组(各组长度与 groups 逐项对应)。"""
    result = []
    cursor = 0
    for size in groups:
        result.append(sequence[cursor:cursor + size])
        cursor += size
    return result


def weighted_sample_partition_indices(items, weights, group_sizes, seed=0):
    """把一次加权无放回序列切成多个互不重叠的样本组, 返回各组原始索引。

    items、weights、seed 沿用 weighted_sample_indices 的全部规则: items、
    weights 是等长的有限非文本序列, 权重接受非布尔 int / 有限非负
    float / Fraction / Decimal(可混合, 超大整数、Fraction、Decimal 全程
    不经过浮点), 相同 (输入, seed) 唯一确定同一序列。group_sizes 是有限
    非文本序列, 成员均为非布尔非负整数。

    返回长度等于 len(group_sizes) 的外层 list: 第 j 组恰含 group_sizes[j]
    个按抽样先后排列的零基原始位置, 组内与组间都不重复(一次无放回抽样
    的连续切片); 依次拼接各组必须逐项等于
    weighted_sample_indices(items, weights, sum(group_sizes), seed),
    零权重位置永不出现。值的重复不影响位置的独立性。

    结构或成员类型错误(items、weights、group_sizes、seed、组成员或权重
    元素)抛 TypeError; 长度不一致、负组大小、总组大小超过可用正权重位置
    数、负权重、NaN 或无穷权重抛 ValueError。空计划返回空 list; 全零组
    大小返回对应数量的空 list; 权重总量为零且总组大小为零同样返回对应
    数量的空 list。全部校验在产生任何分组前完成, 不修改入参。
    """
    n, groups = _validate_partition_inputs(items, weights, group_sizes, seed)
    total = sum(groups)

    # 复制到本地, 绝不修改入参; total=0 时不构造抽样计划也不消耗随机流,
    # 与既有 k=0 入口的节奏一致。
    pool_weights = list(weights)
    rng = random.Random(seed)
    planned_weights, use_exact = _select_sampling_plan(pool_weights, total)
    sequence = _draw_indices_once(n, planned_weights, total, rng, use_exact)
    return _split_groups(sequence, groups)


def weighted_sample_partition(items, weights, group_sizes, seed=0):
    """weighted_sample_partition_indices 的元素值入口: 规则、校验顺序与
    异常类别完全一致, 区别仅在于每组按相同索引返回元素值列表; 两个入口
    逐组逐项对应(相同值的不同位置仍按位置独立处理)。"""
    groups = weighted_sample_partition_indices(
        items, weights, group_sizes, seed
    )
    return [[items[i] for i in group_indices] for group_indices in groups]


def _group_sizes_fingerprint(group_sizes):
    """对组大小计划取指纹: 逐项十进制规范化后整体 sha256。"""
    body = "\n".join(
        "%d:%s" % (index, _int_to_decimal_text(size))
        for index, size in enumerate(group_sizes)
    )
    return _hash_text(body)


def _partition_checkpoint_binding_digest(
    seed_tagged, start, n, groups_count, groups_total, groups_digest,
    items_digest, weights_digest, exact, sequence_payload,
):
    """把分组断点各字段绑定为一个防篡改摘要。

    与其他断点同一构造(serialize_metrics 规范化后 sha256), 绑定标签
    kind、start、n、组数与总组大小、group_sizes 指纹、items / weights
    指纹、标签化 seed、抽样计划与整条无放回位置序列: 任一字段被改动而
    不重算摘要时, 恢复都会在产出任何分组前发现。
    """
    return _hash_text(serialize_metrics({
        "kind": _PARTITION_CHECKPOINT_KIND,
        "seed": seed_tagged,
        "start": start,
        "n": n,
        "groups_count": groups_count,
        "groups_total": groups_total,
        "groups_digest": groups_digest,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "exact": exact,
        "sequence": sequence_payload,
    }))


def _weight_is_strictly_positive(weight):
    """已通过取值校验的单个权重是否严格为正(不经过浮点)。"""
    if isinstance(weight, int):
        return weight > 0
    if isinstance(weight, Decimal):
        return weight > 0
    return weight > 0


def weighted_sample_partition_checkpoint(
    items, weights, group_sizes, seed=0, start=0
):
    """创建分组采样会话的断点(只含 JSON 原生值的状态映射)。

    校验沿用 weighted_sample_partition_indices 的全部规则与固定顺序
    (items、weights、seed、group_sizes 的结构与成员类型; 长度一致、组
    大小非负、权重有限非负; 总组大小不超过正权重位置数), start 必须是
    非布尔非负整数且不超过 len(group_sizes)(start == 组数允许, 表示计划
    已全部消费)。全部校验在返回状态前完成, 失败不返回部分结果, 也不修改
    入参。

    校验通过后一次性抽出整条长度为 sum(group_sizes) 的无放回位置序列,
    start 只标记前 start 个组对应的位置边界(不消耗额外随机流 —— 整条
    序列只由一次加权无放回抽样产生)。返回的状态绑定版本、标签 kind、
    start(已完成组数)、n、组数与总组大小、group_sizes 指纹、items /
    weights 指纹、标签化 seed、抽样计划(exact)与整条组位置序列; 可直接
    交给 serialize_metrics 落盘, 也可经 deserialize_metrics 还原(甚至跨
    进程)后交给 weighted_sample_partition_resume_indices 恢复, 恢复时
    按组边界切片即可, 无需从头重放随机流。
    """
    n, groups = _validate_partition_inputs(items, weights, group_sizes, seed)
    _validate_start(start)
    if start > len(groups):
        raise ValueError("partition start out of range")

    total = sum(groups)
    pool_weights = list(weights)
    rng = random.Random(seed)
    planned_weights, use_exact = _select_sampling_plan(pool_weights, total)
    sequence = _draw_indices_once(n, planned_weights, total, rng, use_exact)

    seed_tagged = _seed_to_tagged_value(seed)
    items_digest = _items_fingerprint(items)
    weights_digest = _weights_fingerprint(weights)
    groups_digest = _group_sizes_fingerprint(groups)
    state = {
        "version": _CHECKPOINT_VERSION,
        "kind": _PARTITION_CHECKPOINT_KIND,
        "start": start,
        "n": n,
        "groups_count": len(groups),
        "groups_total": total,
        "groups_digest": groups_digest,
        "items_digest": items_digest,
        "weights_digest": weights_digest,
        "seed": seed_tagged,
        "exact": bool(use_exact),
        "sequence": list(sequence),
    }
    state["digest"] = _partition_checkpoint_binding_digest(
        seed_tagged, start, n, len(groups), total, groups_digest,
        items_digest, weights_digest, bool(use_exact), sequence,
    )
    return state


def _validate_partition_checkpoint_state(state):
    """校验分组断点状态本身的结构与版本, 返回规范化字段。

    调用前须已确认 state 是映射(否则 TypeError 在外层抛出)。字段缺失、
    未知(多余)字段、类型错误、非法取值、版本不支持、kind 不符等一切
    结构问题统一抛 ValueError。
    """
    required = ("version", "kind", "start", "n", "groups_count",
                "groups_total", "groups_digest", "items_digest",
                "weights_digest", "seed", "exact", "sequence", "digest")
    if not all(key in state for key in required):
        raise ValueError("invalid checkpoint state: missing fields")
    if set(state) != set(required):
        raise ValueError("invalid checkpoint state: unexpected fields")

    version = state["version"]
    if (isinstance(version, bool) or not isinstance(version, int)
            or version != _CHECKPOINT_VERSION):
        raise ValueError("unsupported checkpoint version: %r" % (version,))
    if state["kind"] != _PARTITION_CHECKPOINT_KIND:
        raise ValueError("invalid checkpoint state: unexpected kind")
    start = state["start"]
    n = state["n"]
    groups_count = state["groups_count"]
    groups_total = state["groups_total"]
    for name, value in (("start", start), ("n", n),
                        ("groups_count", groups_count),
                        ("groups_total", groups_total)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("invalid checkpoint state: %s" % name)
    if start > groups_count:
        raise ValueError("invalid checkpoint state: start exceeds groups")
    if not isinstance(state["exact"], bool):
        raise ValueError("invalid checkpoint state: exact")
    for name in ("groups_digest", "items_digest", "weights_digest",
                 "digest"):
        if not isinstance(state[name], str):
            raise ValueError("invalid checkpoint state: %s" % name)

    # 整条无放回位置序列必须是列表, 长度恰为总组大小, 成员为 [0, n) 内的
    # 非布尔整数且互不重复 —— 与其他断点对 RNG 快照的结构化范围校验同理,
    # 被篡改(即使重算了摘要)的越界或重复位置在这里统一抛 ValueError。
    sequence_payload = state["sequence"]
    if not isinstance(sequence_payload, list):
        raise ValueError("invalid checkpoint state: sequence")
    if len(sequence_payload) != groups_total:
        raise ValueError("invalid checkpoint state: sequence")
    seen = set()
    for member in sequence_payload:
        if (isinstance(member, bool) or not isinstance(member, int)
                or member < 0 or member >= n or member in seen):
            raise ValueError("invalid checkpoint state: sequence")
        seen.add(member)

    # 状态可能经 serialize_metrics + deserialize_metrics 还原: 其中的
    # Decimal 载荷(只可能出现在标签化 seed 中)先还原为等值 float, 再
    # 解码与核对摘要 —— 两条文本路径解析出的状态因此可互换恢复。
    seed_payload = _normalize_checkpoint_numbers(state["seed"])

    # 逆运算对内部结构问题统一抛 ValueError。
    seed = _tagged_value_to_seed(seed_payload)

    # 绑定摘要: 任何对字段的篡改若不附带重算的摘要, 都会在这里被发现。
    expected_digest = _partition_checkpoint_binding_digest(
        seed_payload, start, n, groups_count, groups_total,
        state["groups_digest"], state["items_digest"],
        state["weights_digest"], state["exact"], sequence_payload,
    )
    if not hmac.compare_digest(expected_digest, state["digest"]):
        raise ValueError("invalid checkpoint state: digest mismatch")
    return (start, n, groups_count, groups_total, state["exact"], seed,
            sequence_payload, seed_payload)


def _resume_partition_groups_indices(items, weights, group_sizes, state,
                                     draws):
    """两个分组恢复入口共用的已校验核心: 只产出索引分组与下一状态。

    调用约定: 外层已确认 state 是映射并校验过 draws。先校验状态本身的
    结构/版本/摘要, 再以状态携带的 seed 完成 items、weights、
    group_sizes 的采样入口校验; 然后核对状态与当前输入的绑定(n、组数与
    总组大小、group_sizes / items / weights 指纹、抽样计划)以及恢复窗口
    [start, start+draws) 不越过计划范围。任一失败都在物化任何分组之前
    抛出既有 TypeError / ValueError。全部通过后直接按组边界切分状态
    携带的位置序列(恢复无需从头重放随机流), 返回 (索引分组, 下一状态);
    不修改入参, 也不修改传入的状态映射。
    """
    (start, state_n, groups_count, groups_total, use_exact, seed,
     sequence_payload, seed_payload) = _validate_partition_checkpoint_state(
        state
    )

    # 与一次性分组入口同一套校验; groups 是 group_sizes 的本地副本。
    n, groups = _validate_partition_inputs(items, weights, group_sizes, seed)

    # 恢复窗口不得越过计划范围。
    if start + draws > len(groups):
        raise ValueError("partition resume window out of range")

    # 状态与当前采样输入的一致性: 组数与总组大小先比, 再核对指纹。
    if state_n != n or groups_count != len(groups) \
            or groups_total != sum(groups):
        raise ValueError(
            "checkpoint state does not match items/weights/group_sizes"
        )
    if state["groups_digest"] != _group_sizes_fingerprint(groups):
        raise ValueError("checkpoint state does not match group_sizes")
    if state["items_digest"] != _items_fingerprint(items):
        raise ValueError("checkpoint state does not match items")
    if state["weights_digest"] != _weights_fingerprint(weights):
        raise ValueError("checkpoint state does not match weights")

    # 抽样计划必须与创建断点时一致; 权重已逐位置指纹核对, 这里重建计划
    # 并比对 exact 标志。
    _planned_weights, planned_exact = _select_sampling_plan(
        list(weights), groups_total
    )
    if planned_exact != use_exact:
        raise ValueError("invalid checkpoint state: sampling plan mismatch")

    # 纵深防御: 状态中的每个位置都必须对应严格为正的权重 —— 与其他断点
    # 对 RNG 快照的结构化范围校验同理, 即使调用方重算了摘要, 把零权重
    # 位置塞进序列也在此统一拒绝(指纹已逐位置绑定 weights, 正常状态绝不
    # 触发)。
    for position in sequence_payload:
        if not _weight_is_strictly_positive(weights[position]):
            raise ValueError("invalid checkpoint state: sequence")

    # 全部校验通过后才物化分组: 按组边界切片状态序列, 结果与一次性
    # weighted_sample_partition_indices 的零基区间 [start, start+draws)
    # 逐项一致。
    begin = sum(groups[:start])
    end = sum(groups[:start + draws])
    partition = _split_groups(
        sequence_payload[begin:end], groups[start:start + draws]
    )

    next_state = dict(state)
    next_state["start"] = start + draws
    # 整条位置序列与抽样计划不变, 只推进 start; seed 载荷使用校验时规范
    # 化后的形式(经 deserialize_metrics 还原的状态其 Decimal 已回到等值
    # float), 下一状态因此与 JSON 原生状态链逐字段一致。
    next_state["seed"] = seed_payload
    # 摘要必须随 start 一并刷新, 否则链式再恢复时会因摘要失配而失败
    # (其余字段与原状态相同)。
    next_state["digest"] = _partition_checkpoint_binding_digest(
        seed_payload, start + draws, n, groups_count, groups_total,
        state["groups_digest"], state["items_digest"],
        state["weights_digest"], planned_exact, sequence_payload,
    )
    return partition, next_state


def weighted_sample_partition_resume_indices(
    items, weights, group_sizes, state, draws
):
    """从分组断点继续产出索引分组, 返回 (分组列表, 下一状态)。

    第一组从断点记录的 start(已完成组数)开始; 逐组结果与一次性
    weighted_sample_partition_indices(items, weights, group_sizes, seed)
    的零基区间 [start, start+draws) 完全一致; 多次连续续接与一次性生成
    逐项相同, 恢复时无需从头重放随机流(断点记录已消费的组位置前缀)。
    返回前完成与分组入口一致的全部输入校验(含恢复窗口不越过计划范围),
    并核对状态与 items、weights、group_sizes 及 (seed, start, 已消费位置
    前缀)的自洽性: 状态不是映射抛 TypeError; 字段缺失或未知、版本不
    支持、摘要或输入不匹配统一抛 ValueError; items/weights/group_sizes/
    draws 的错误沿用既有 TypeError / ValueError。所有失败都在任何分组
    物化之前确定, 绝不返回部分结果。draws=0 返回空分组与 start、已消费
    前缀不变的状态副本; 全零组大小的组在窗口内返回空列表。状态可经
    serialize_metrics / deserialize_metrics 往返后继续恢复。不修改入参,
    也不修改传入的状态映射。
    """
    # 状态不是映射: TypeError(文档约定的明确分类)。映射前提下的一切
    # 结构/版本/摘要问题统一为 ValueError。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    # draws 的类型/取值规则独立于状态, 先按既有规则校验(TypeError /
    # ValueError), 再解析状态。
    _validate_draws(draws)
    return _resume_partition_groups_indices(
        items, weights, group_sizes, state, draws
    )


def weighted_sample_partition_resume(
    items, weights, group_sizes, state, draws
):
    """按元素值从分组断点继续, 返回 (元素值分组列表, 下一状态)。

    校验顺序按恢复入口约定固定: 调用开始先按现有分组入口完成 items、
    weights、group_sizes 的结构、长度、成员类型、权重取值与正权重可行性
    校验(这部分与 seed 无关, 以状态携带的 seed 复核; state 携带的 seed
    其标签化编码随后随 state 一并校验), 再按现有恢复入口校验 state 的
    映射类型、版本、字段集合、摘要以及 state 与当前输入的绑定(含恢复
    窗口范围), draws 必须是非布尔非负整数。状态不是映射抛 TypeError;
    非法状态、版本不支持、状态与输入不匹配或恢复窗口超出计划范围等一律
    抛 ValueError; 其余输入错误沿用既有 TypeError / ValueError。所有
    失败都在产生任何分组之前确定。

    每组返回元素值列表, 与 weighted_sample_partition_resume_indices
    返回的每组原始位置逐项对应(第 j 个值恰为 items[第 j 个索引]):
    相同值的不同位置分别消耗。返回的下一状态与按索引入口产出的完全
    相同(start、已消费位置前缀、digest 一致), 只含 JSON 原生值, 可直接
    再次传入本入口或按索引入口, 或经 serialize_metrics /
    deserialize_metrics 往返后继续恢复。draws=0 返回空分组与 start、
    已消费前缀不变的状态副本。不修改入参, 也不修改传入的状态映射。
    """
    # 第一步: 先按现有分组入口完成 items、weights、group_sizes 的结构、
    # 长度、成员类型、权重取值与可行性校验(以合法种子 0 试跑; state 携带
    # 的 seed 其编码与类型在第三步随状态一并校验)。因此即使 state 本身
    # 已损坏, 非法 items/weights/group_sizes 仍优先以分组入口的异常类别
    # 报告。
    _validate_partition_inputs(items, weights, group_sizes, 0)

    # 第二步: 恢复入口的映射类型检查与 draws 规则(TypeError / ValueError)。
    if not isinstance(state, collections.abc.Mapping):
        raise TypeError("checkpoint state must be a mapping")
    _validate_draws(draws)

    # 第三步: 状态结构/版本/字段/摘要、state 与输入绑定(含从状态解出的
    # seed 再跑一次完整分组校验与窗口检查), 全部通过后续接产出索引分组。
    # 与按索引入口共用同一个已校验核心, 因此分组内容、下一状态、异常
    # 类别与其逐项一致。
    index_groups, next_state = _resume_partition_groups_indices(
        items, weights, group_sizes, state, draws
    )
    # 按每组原始位置逐项映射为元素值: 相同值的不同位置各自独立映射,
    # 组内不重复位置这一性质随索引结果原样保留。只读取 items, 不修改入参。
    groups = [
        [items[i] for i in group_indices] for group_indices in index_groups
    ]
    return groups, next_state


# ---------------------------------------------------------------------------
# 分层配额采样
# ---------------------------------------------------------------------------

def _validate_stratified_inputs(items, weights, strata, quotas, seed):
    """分层配额采样三个入口共用的全部前置校验。

    校验顺序固定: 先 items、weights、seed 的结构/类型(与既有采样入口同一
    套规则, TypeError), 再 strata、quotas 的结构(非文本且长度可确定的
    序列)与每个成员的类型(非布尔整数, TypeError); 随后 weights / strata
    长度与 items 一致、strata 编号非负、quotas 长度等于最大编号加一、
    配额非负(ValueError); 接着权重元素类型(TypeError)与取值(ValueError)
    校验; 最后按编号升序逐层校验配额不超过该层正权重位置数(ValueError)。
    空 items 只接受空 strata 与空 quotas; 全部配额为零同样通过校验。
    全部校验在产生任何结果前完成, 不修改入参。通过后返回
    (n, strata 编号副本, quotas 配额副本)。
    """
    # ---- 1. 结构与参数类型 (TypeError) ----
    if not _is_length_determinable_sequence(items):
        raise TypeError("items must be a length-determinable sequence")
    if not _is_length_determinable_sequence(weights):
        raise TypeError("weights must be a length-determinable sequence")
    if not isinstance(seed, _SEED_TYPES):
        raise TypeError("unsupported seed type: %s" % type(seed).__name__)
    if not _is_length_determinable_sequence(strata):
        raise TypeError("strata must be a length-determinable sequence")
    strata_numbers = []
    for member in strata:
        if isinstance(member, bool) or not isinstance(member, int):
            raise TypeError("strata members must be non-boolean integers")
        strata_numbers.append(member)
    if not _is_length_determinable_sequence(quotas):
        raise TypeError("quotas must be a length-determinable sequence")
    quota_values = []
    for member in quotas:
        if isinstance(member, bool) or not isinstance(member, int):
            raise TypeError("quotas members must be non-boolean integers")
        quota_values.append(member)

    # ---- 2. 长度与编号范围 (ValueError) ----
    n = len(items)
    if len(weights) != n:
        raise ValueError("invalid sample size")
    if len(strata_numbers) != n:
        raise ValueError("strata length must equal items length")
    for number in strata_numbers:
        if number < 0:
            raise ValueError("stratum number out of range")
    # quotas 的下标对应分层编号, 其长度必须恰好是最大编号加一 —— 空 items
    # 没有最大编号, 只接受空 quotas; 编号越界(大于等于 quotas 长度)与
    # quotas 尾部多余都体现为同一长度约束。
    top = max(strata_numbers) if strata_numbers else -1
    if len(quota_values) != top + 1:
        raise ValueError("quotas length must equal max stratum number plus one")
    for quota in quota_values:
        if quota < 0:
            raise ValueError("quotas must be non-negative")

    # ---- 3. 权重元素类型与取值 (TypeError / ValueError) ----
    _validate_weight_elements(weights)

    # ---- 4. 每层配额的正权重可行性 (ValueError) ----
    # 按编号升序逐层检查: 配额超过该层正权重位置数(含该层没有成员或成员
    # 权重全为零的情形)时确定抛 ValueError; 零配额分层恒可行。
    for number, quota in enumerate(quota_values):
        if quota > 0:
            layer_weights = [
                weights[i] for i in range(n) if strata_numbers[i] == number
            ]
            if quota > _count_positive_weights(layer_weights):
                raise ValueError("no positive weight")
    return n, strata_numbers, quota_values


def weighted_sample_stratified_indices(items, weights, strata, quotas, seed=0):
    """按分层配额做加权无放回抽样, 返回按层拼接的零基原始索引。

    items、weights、seed 沿用 weighted_sample_indices 的全部规则: items、
    weights 是等长的有限非文本序列, 权重接受非布尔 int / 有限非负
    float / Fraction / Decimal(可混合, 超大整数、Fraction、Decimal 全程
    不经过浮点)。strata 是与 items 等长的有限非文本序列, 每个位置保存
    非布尔非负整数分层编号; quotas 是有限非文本序列, 下标对应分层编号,
    成员为非布尔非负整数配额, 其长度必须恰好等于最大编号加一。

    分层按编号升序依次处理: 第 number 层在其成员位置中按权重比例无放回
    抽取 quotas[number] 个不同位置, 层内按抽样先后排列, 各层结果按编号
    升序依次拼接; 返回的均为原始零基索引, 相同值的不同位置仍按位置独立
    处理。所有层共享同一个由 seed 初始化的随机流, 零配额分层不消耗该流;
    相同 (输入, quotas, seed) 唯一确定同一序列。只有编号为零的单层时,
    结果与 weighted_sample_indices(items, weights, quotas[0], seed)
    逐项相同。零权重位置永不入选; 全部配额为零时返回空列表。

    结构或成员类型错误(items、weights、strata、quotas、seed 或权重元素)
    抛 TypeError; 长度不一致、编号越界、quotas 长度不等于最大编号加一、
    负配额、配额超过该层正权重位置数、负权重、NaN 或无穷权重抛
    ValueError。空 items 只接受空 strata 与空 quotas。全部校验在产生任何
    结果前完成, 不修改入参。
    """
    n, strata_numbers, quota_values = _validate_stratified_inputs(
        items, weights, strata, quotas, seed
    )

    # 复制到本地, 绝不修改入参; 各层按编号升序共享同一条随机流。
    local_weights = list(weights)
    rng = random.Random(seed)
    indices = []
    for number, quota in enumerate(quota_values):
        # 零配额分层不消耗随机流, 直接跳过 —— 与既有 k=0 入口的节奏一致。
        if quota == 0:
            continue
        # 层内位置池按原始零基索引升序保留; 每层独立选择抽样计划(单层
        # 编号为零时层权重即全量权重, 与 weighted_sample_indices 的计划、
        # 随机流消耗和结果逐项一致)。
        pool = [i for i in range(n) if strata_numbers[i] == number]
        pool_weights = [local_weights[i] for i in pool]
        planned_weights, use_exact = _select_sampling_plan(pool_weights, quota)
        indices.extend(
            _draw_indices_once_pool(pool, planned_weights, quota, rng, use_exact)
        )
    return indices


def weighted_sample_stratified(items, weights, strata, quotas, seed=0):
    """weighted_sample_stratified_indices 的元素值入口: 规则、校验顺序与
    异常类别完全一致, 区别仅在于按相同索引返回元素值列表; 两个入口逐项
    对应(相同值的不同位置仍按位置独立处理)。"""
    indices = weighted_sample_stratified_indices(
        items, weights, strata, quotas, seed
    )
    return [items[i] for i in indices]


def weighted_sample_stratified_counts(items, weights, strata, quotas, seed=0):
    """weighted_sample_stratified_indices 的频次入口: 接受与该入口完全
    相同的参数语义、固定校验顺序与异常类别, 按同一条由 seed 初始化的随机
    流完成同样的分层抽样, 返回长度等于 items 的整数 list counts,
    counts[i] 在位置 i 被选中时为一、其余为零(每个位置只属于一个分层,
    层内无放回, 同一位置至多计一次; 相等的元素值仍按不同位置分别累计)。
    结果等于把 weighted_sample_stratified_indices 同参数的结果按位置
    摊平计数, 随机流消耗逐项对齐。全部配额为零时返回全零列表(仍完成
    全部校验); 任何失败都不给出部分计数。计数为任意精度整数, 可直接
    交给 serialize_metrics 并经 deserialize_metrics 精确往返。不修改
    入参。
    """
    indices = weighted_sample_stratified_indices(
        items, weights, strata, quotas, seed
    )
    counts = [0] * len(items)
    for position in indices:
        counts[position] += 1
    return counts


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
