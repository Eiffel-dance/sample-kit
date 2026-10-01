# Sample Kit

A dependency-free Python reference implementation for data, weighted-sampling, metrics.

Run with: python3 demo.py
Tests: python3 -m unittest discover -s tests -v

## Scope

实现可复现的加权无放回采样与指标序列化工具。相同种子和输入必须得到相同序列；零权重、负权重、重复项和空有效样本必须按公开规则处理；指标输出中的超大整数始终保持精确十进制，不能经过浮点转换。公开函数、参数校验和异常类型应当可由独立数值脚本直接验证。
