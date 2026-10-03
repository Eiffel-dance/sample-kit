# Sample Kit

A dependency-free Python reference implementation for data, weighted-sampling, metrics.

Run with: python3 demo.py
Tests: python3 -m unittest discover -s tests -v

## Scope

实现可复现的加权无放回采样与指标序列化工具。相同种子和输入必须得到相同序列；零权重、负权重、重复项和空有效样本必须按公开规则处理；指标输出中的超大整数始终保持精确十进制，不能经过浮点转换。公开函数、参数校验和异常类型应当可由独立数值脚本直接验证。

单轮排除入口：`weighted_sample_excluding_indices(items, weights, k, excluded=(), seed=0)` 在完成与现有采样入口一致的校验后，按集合语义排除 `excluded` 中的原始零基位置（重复与排列顺序不影响结果），再在剩余位置中按权重比例无放回抽取 `k` 个不同位置并返回原始索引；`weighted_sample_excluding` 按相同索引返回元素值。被排除位置即使权重为正也绝不出现，未排除的零权重仍永不入选；`excluded` 为空时与现有单轮入口逐项相同。`excluded` 结构或成员类型错误抛 TypeError，越界位置、有效正权重不足等抛 ValueError，全部校验在产生任何结果前完成。

长批次支持可暂停/恢复的采样会话：`weighted_sample_checkpoint(items, weights, k, seed=0, start=0)` 返回只含 JSON 原生值(版本、当前位置、items/weights 指纹、标签化 seed、RNG 快照与绑定摘要)的状态映射，可直接交给 `serialize_metrics` 或落盘；`weighted_sample_resume_indices(items, weights, k, state, draws)` 从断点续接，返回 `(索引轮次, 下一状态)`，逐轮等于批量入口的对应零基区间，恢复时无需从头重放随机流；`weighted_sample_resume(items, weights, k, state, draws)` 为按元素值恢复入口，每轮返回与索引轮次逐项对应的元素值列表(相同值的不同位置分别消耗)，下一状态与按索引入口完全相同、可互换续接。

`deserialize_metrics(text)` 是 `serialize_metrics` 的逆入口：把指标序列化文本还原为可继续计算的 Python 数据树(null/布尔/字符串/数组/对象分别还原为 None/bool/str/list/dict，对象成员名保持文本形式与次序)。数字解析完全绕开浮点：无小数点或指数标记的数字还原为任意精度 int，带小数点或指数标记的有限数字还原为 Decimal(保留正负号、刻度、指数与负零)；超长整数与极端指数在解释器整数转文本限制较低时仍精确成功。NaN/Infinity/-Infinity、语法错误、重复对象成员名及无法保持精度的数字统一抛 ValueError，非 str 输入抛 TypeError。还原后的数据可直接再交给 `serialize_metrics`(整数与 Decimal 的十进制内容保持精确)，也可直接消费 checkpoint 状态文本并交给恢复入口续接。
