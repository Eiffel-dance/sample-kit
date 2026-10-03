# Sample Kit

A dependency-free Python reference implementation for data, weighted-sampling, metrics.

Run with: python3 demo.py
Tests: python3 -m unittest discover -s tests -v

## Scope

实现可复现的加权无放回采样与指标序列化工具。相同种子和输入必须得到相同序列；零权重、负权重、重复项和空有效样本必须按公开规则处理；指标输出中的超大整数始终保持精确十进制，不能经过浮点转换。公开函数、参数校验和异常类型应当可由独立数值脚本直接验证。

长批次支持可暂停/恢复的采样会话：`weighted_sample_checkpoint(items, weights, k, seed=0, start=0)` 返回只含 JSON 原生值(版本、当前位置、items/weights 指纹、标签化 seed、RNG 快照与绑定摘要)的状态映射，可直接交给 `serialize_metrics` 或落盘；`weighted_sample_resume_indices(items, weights, k, state, draws)` 从断点续接，返回 `(索引轮次, 下一状态)`，逐轮等于批量入口的对应零基区间，恢复时无需从头重放随机流；`weighted_sample_resume(items, weights, k, state, draws)` 为按元素值恢复入口，每轮返回与索引轮次逐项对应的元素值列表(相同值的不同位置分别消耗)，下一状态与按索引入口完全相同、可互换续接。

`deserialize_metrics(text)` 是 `serialize_metrics` 的逆方向入口：把指标序列化文本(或任何合法 JSON 文本，含 checkpoint 状态文本)还原为可继续计算的 Python 数据树。数字解析完全绕开浮点——无小数点/指数标记的整数还原为任意精度 int(不受运行时整数转文本位数限制)，带小数点或指数标记的有限数字还原为 Decimal 并保留正负号、刻度、指数与负零；参数只接受 str(其他类型 TypeError)，NaN/Infinity/语法错误/重复对象成员名/无法保持精度的数字统一 ValueError，出错不返回部分结果。
