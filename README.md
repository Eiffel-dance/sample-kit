# Sample Kit

A dependency-free Python reference implementation for data, weighted-sampling, metrics.

Run with: python3 demo.py
Tests: python3 -m unittest discover -s tests -v

## Scope

实现可复现的加权无放回采样与指标序列化工具。相同种子和输入必须得到相同序列；零权重、负权重、重复项和空有效样本必须按公开规则处理；指标输出中的超大整数始终保持精确十进制，不能经过浮点转换。公开函数、参数校验和异常类型应当可由独立数值脚本直接验证。

长批次支持可暂停/恢复的采样会话：`weighted_sample_checkpoint(items, weights, k, seed=0, start=0)` 返回只含 JSON 原生值(版本、当前位置、items/weights 指纹、标签化 seed、RNG 快照与绑定摘要)的状态映射，可直接交给 `serialize_metrics` 或落盘；`weighted_sample_resume_indices(items, weights, k, state, draws)` 从断点续接，返回 `(索引轮次, 下一状态)`，逐轮等于批量入口的对应零基区间，恢复时无需从头重放随机流。
