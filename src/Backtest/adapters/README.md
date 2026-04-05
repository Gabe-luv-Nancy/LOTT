# Backtest Adapters 子模块文档

## 模块概述

Adapters 子模块提供多个回测框架的适配器实现，将不同的第三方回测框架统一到 LOTT 的回测接口中。

## 文件结构

```
adapters/
├── __init__.py       # 模块入口，导出所有适配器
├── base.py           # 适配器基类
├── vectorbt.py       # VectorBT 适配器
├── backtrader.py     # Backtrader 适配器
└── backtesting.py    # Backtesting.py 适配器
```

## 核心组件说明

### 1. base.py（适配器基类）

**类**: `BaseAdapter`

**功能**: 定义所有适配器的统一接口

**主要方法**:

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `load_data(data)` | 加载数据 | Any |
| `run(strategy, data)` | 执行回测 | Dict |
| `get_results()` | 获取结果 | Dict |

### 2. vectorbt.py（VectorBT 适配器）

**类**: `VectorBTAdapter`

**功能**: 适配 VectorBT 向量化回测框架

**特点**:
- 向量化计算，速度快
- 支持 Portfolio 管理
- 内置技术指标

### 3. backtrader.py（Backtrader 适配器）

**类**: `BacktraderAdapter`

**功能**: 适配 Backtrader 事件驱动回测框架

**特点**:
- 事件驱动架构
- 丰富的指标库
- 支持多数据源

### 4. backtesting.py（Backtesting.py 适配器）

**类**: `BacktestingPyAdapter`

**功能**: 适配 Backtesting.py 轻量级回测框架

**特点**:
- 轻量级设计
- 简洁的 API
- 快速原型开发

## 使用示例

```python
from backtest.adapters import VectorBTAdapter

# 创建适配器
adapter = VectorBTAdapter()

# 加载数据
adapter.load_data(data)

# 运行回测
results = adapter.run(strategy)

# 获取结果
metrics = adapter.get_results()
```

## 技术框架

- **VectorBT**: >= 0.25.0
- **Backtrader**: >= 1.9.76
- **Backtesting.py**: >= 0.3.3