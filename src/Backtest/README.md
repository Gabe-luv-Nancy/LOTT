# Backtest 模块 - 统一回测框架

> **模块名称:** UniBacktest  
> **设计理念:** 模块化、可替换、统一接口  
> **创建时间:** 2026-02-18

---

## 目录

1. [概述](#1-概述)
2. [架构设计](#2-架构设计)
3. [核心特性](#3-核心特性)
4. [快速开始](#4-快速开始)
5. [核心组件](#5-核心组件)
6. [适配器系统](#6-适配器系统)
7. [使用指南](#7-使用指南)
8. [接口规范](#8-接口规范)
9. [实现状态与路线图](#9-实现状态与路线图)
10. [技术依赖](#10-技术依赖)

---

## 1. 概述

### 1.1 设计目标

UniBacktest 模块旨在为 LOTT 项目提供一套**统一接口、可替换底层框架**的回测系统。核心设计目标包括：

| 目标 | 说明 |
|------|------|
| **框架无关** | 用户代码与底层回测引擎解耦，可无缝切换 VectorBT、Backtrader、Backtesting.py 等 |
| **统一接口** | 提供一致的配置、数据、策略、结果格式，降低学习成本 |
| **模块化扩展** | 通过适配器模式支持任意回测框架的接入 |
| **链式调用** | 流式 API 设计，代码简洁易读 |
| **标准化结果** | 统一的绩效指标输出，便于比较和分析 |

### 1.2 适用场景

- 策略原型验证与快速迭代
- 多框架回测结果对比
- 参数优化与网格搜索
- 策略库的统一管理与调度

---

## 2. 架构设计

### 2.1 分层架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户代码层                              │
│          (策略定义 + 统一调用接口)                            │
├─────────────────────────────────────────────────────────────┤
│                    BacktestLayer                            │
│              (统一入口 + 策略适配 + 结果归一化)               │
├───────────────┬───────────────┬───────────────┬─────────────┤
│   VectorBT    │   Backtrader  │ backtesting.  │   (扩展)    │
│   Adapter     │   Adapter     │ py Adapter    │  Adapter    │
├───────────────┴───────────────┴───────────────┴─────────────┤
│                    底层回测框架                              │
│         (vectorbt / backtrader / backtesting.py)           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目录结构

```
src/Backtest/
├── __init__.py              # 模块入口，导出公共 API
├── config.py                # UniConfig - 统一配置
├── data.py                  # UniData - 统一数据格式
├── signal.py                # Signal - 统一信号格式
├── result.py                # UniResult - 统一结果格式
├── strategy.py              # UniStrategy - 策略基类
├── backtest.py              # BacktestLayer - 主入口类
├── adapters/                # 适配器子模块
│   ├── __init__.py          # 适配器导出
│   ├── base.py              # BaseAdapter - 适配器基类
│   ├── vectorbt.py          # VectorBT 适配器
│   ├── backtrader.py        # Backtrader 适配器
│   └── backtesting.py       # Backtesting.py 适配器
├── examples/                # 使用示例
│   └── usage.py
└── README.md                # 本文档
```

---

## 3. 核心特性

### 3.1 多框架支持

| 框架 | 类型 | 特点 | 适用场景 |
|------|------|------|----------|
| **VectorBT** | 矢量化 | 极速执行、批量处理 | 参数扫描、高频策略验证 |
| **Backtrader** | 事件驱动 | 成熟稳定、功能丰富 | 复杂策略、实盘模拟过渡 |
| **Backtesting.py** | 轻量级 | 简洁易用、交互友好 | 快速原型、策略演示 |

### 3.2 统一接口

- **统一配置**: `UniConfig` 封装所有回测参数
- **统一数据**: `UniData` 标准化 OHLCV 数据结构
- **统一信号**: `Signal` 标准化交易指令格式
- **统一结果**: `UniResult` 标准化绩效指标输出

### 3.3 链式调用

支持流式 API，代码更简洁：

```python
result = (
    BacktestLayer(framework="vectorbt")
    .set_data(data)
    .set_strategy(strategy)
    .run()
)
```

---

## 4. 快速开始

### 4.1 安装依赖

```bash
pip install vectorbt backtrader backtesting
```

### 4.2 最简示例

```python
from backtest import BacktestLayer, UniData, UniStrategy, Signal

# 准备数据
data = UniData.from_dataframe(df, symbol="BTC/USDT")

# 定义策略
class MyStrategy(UniStrategy):
    def next(self, bar_idx):
        # 策略逻辑
        return Signal.buy(size=0.5)

# 运行回测
result = BacktestLayer().set_data(data).set_strategy(MyStrategy()).run()
print(result.summary())
```

---

## 5. 核心组件

### 5.1 BacktestLayer（回测入口类）

**文件**: `backtest.py`

**职责**: 统一回测入口，协调各组件完成回测流程

**核心方法规范**:

| 方法 | 输入 | 输出 | 说明 |
|------|------|------|------|
| `__init__(framework, config)` | 框架名称, 配置对象 | 实例 | 初始化回测引擎 |
| `set_data(data)` | UniData | self | 设置回测数据 |
| `set_strategy(strategy)` | UniStrategy | self | 设置策略实例 |
| `run(**kwargs)` | 可选参数 | UniResult | 执行回测 |
| `optimize(param_grid, maximize, **kwargs)` | 参数网格, 优化目标 | UniResult | 参数优化 |
| `plot(result, **kwargs)` | UniResult | None | 可视化结果 |
| `switch_framework(framework)` | 框架名称 | bool | 切换底层框架 |
| `get_available_engines()` | - | List[str] | 获取可用框架列表 |

### 5.2 UniConfig（统一配置）

**文件**: `config.py`

**职责**: 封装回测所需的所有配置参数

**属性规范**:

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `initial_capital` | float | 100000.0 | 初始资金 |
| `commission` | float | 0.0003 | 手续费率（按成交金额比例） |
| `slippage` | float | 0.0001 | 滑点（按价格比例） |
| `risk_free_rate` | float | 0.02 | 无风险利率（年化） |
| `framework` | str | "vectorbt" | 底层框架选择 |
| `enable_optimize` | bool | False | 是否启用参数优化模式 |
| `max_position_size` | float | 1.0 | 最大持仓比例 |
| `allow_short` | bool | False | 是否允许做空 |

**接口需求**:

```python
class UniConfig:
    def __init__(self, **kwargs): ...
    def to_dict(self) -> dict: ...
    def validate(self) -> bool: ...
    @classmethod
    def from_dict(cls, d: dict) -> 'UniConfig': ...
```

### 5.3 UniData（统一数据格式）

**文件**: `data.py`

**职责**: 标准化 OHLCV 数据结构，提供统一的数据访问接口

**属性规范**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `df` | DataFrame | 内部数据存储 |
| `symbol` | str | 交易品种标识 |
| `timeframe` | str | 时间周期（如 "1d", "1h"） |
| `open` | np.ndarray | 开盘价序列 |
| `high` | np.ndarray | 最高价序列 |
| `low` | np.ndarray | 最低价序列 |
| `close` | np.ndarray | 收盘价序列 |
| `volume` | np.ndarray | 成交量序列 |
| `datetime` | np.ndarray | 时间戳序列 |

**接口需求**:

```python
class UniData:
    @classmethod
    def from_dataframe(cls, df, symbol: str, timeframe: str) -> 'UniData': ...
    
    @classmethod
    def from_csv(cls, path: str, symbol: str, **kwargs) -> 'UniData': ...
    
    def __len__(self) -> int: ...
    def validate(self) -> bool: ...
    def get_bar(self, idx: int) -> dict: ...
    def to_dataframe(self) -> DataFrame: ...
```

### 5.4 UniStrategy（策略基类）

**文件**: `strategy.py`

**职责**: 定义策略接口规范，用户需继承并实现核心逻辑

**必须实现的方法**:

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `init(self, data: UniData)` | 初始化阶段，预计算指标 | None |
| `next(self, bar_idx: int)` | 信号生成，每根 K 线调用一次 | Optional[Signal] 或 Tuple[Signal, ...] |

**可选回调方法**:

| 方法 | 触发时机 |
|------|----------|
| `on_bar(self, data, bar_idx)` | 每 K 线回调 |
| `on_order_filled(self, order)` | 订单成交回调 |
| `on_order_rejected(self, order)` | 订单拒绝回调 |
| `on_train(self, data)` | 训练模式回调（ML 策略） |

**接口需求**:

```python
class UniStrategy(ABC):
    name: str = "BaseStrategy"
    
    @abstractmethod
    def init(self, data: UniData) -> None: ...
    
    @abstractmethod
    def next(self, bar_idx: int) -> Optional[Signal]: ...
    
    def get_params(self) -> dict: ...
    def set_params(self, **params) -> None: ...
```

### 5.5 Signal（统一信号格式）

**文件**: `signal.py`

**职责**: 标准化交易信号，统一不同框架的订单类型

**信号类型定义**:

| 动作 | 常量 | 说明 |
|------|------|------|
| `buy` | BUY | 买入/做多 |
| `sell` | SELL | 卖出 |
| `close` | CLOSE | 平仓 |
| `short` | SHORT | 做空 |
| `cover` | COVER | 平空 |

**属性规范**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `action` | str | 信号动作类型 |
| `size` | float | 仓位大小（比例或绝对值） |
| `limit_price` | Optional[float] | 限价单价格 |
| `stop_price` | Optional[float] | 止损单价格 |
| `order_type` | str | 订单类型（market/limit/stop） |
| `metadata` | dict | 扩展元数据 |

**接口需求**:

```python
class Signal:
    @classmethod
    def buy(cls, size: float, **kwargs) -> 'Signal': ...
    
    @classmethod
    def sell(cls, size: float, **kwargs) -> 'Signal': ...
    
    @classmethod
    def close(cls, size: float = 1.0, **kwargs) -> 'Signal': ...
    
    @classmethod
    def short(cls, size: float, **kwargs) -> 'Signal': ...
    
    @classmethod
    def cover(cls, size: float = 1.0, **kwargs) -> 'Signal': ...
    
    def to_dict(self) -> dict: ...
```

### 5.6 UniResult（统一结果格式）

**文件**: `result.py`

**职责**: 标准化回测结果，提供统一的绩效指标

**绩效指标规范**:

| 类别 | 属性 | 类型 | 说明 |
|------|------|------|------|
| **收益指标** | `total_return_pct` | float | 总收益率（%） |
| | `annualized_return` | float | 年化收益率（%） |
| | `cumulative_return` | float | 累计收益率 |
| **风险指标** | `sharpe_ratio` | float | 夏普比率 |
| | `sortino_ratio` | float | 索提诺比率 |
| | `max_drawdown_pct` | float | 最大回撤（%） |
| | `volatility` | float | 年化波动率 |
| | `calmar_ratio` | float | 卡玛比率 |
| **交易统计** | `total_trades` | int | 总交易次数 |
| | `win_rate` | float | 胜率（%） |
| | `profit_factor` | float | 盈亏比 |
| | `avg_trade_duration` | float | 平均持仓时间 |
| | `max_consecutive_wins` | int | 最大连续盈利次数 |
| | `max_consecutive_losses` | int | 最大连续亏损次数 |
| **曲线数据** | `equity_curve` | np.ndarray | 权益曲线 |
| | `drawdown_curve` | np.ndarray | 回撤曲线 |
| | `trade_records` | List[Trade] | 交易记录列表 |

**接口需求**:

```python
class UniResult:
    def summary(self) -> str: ...
    def to_dict(self) -> dict: ...
    def get_equity_curve(self) -> np.ndarray: ...
    def get_trade_records(self) -> List['Trade']: ...
    def plot(self, **kwargs) -> None: ...
```

---

## 6. 适配器系统

### 6.1 适配器架构

适配器是模块化设计的核心，负责将统一接口转换为底层框架的特定调用。

```
┌─────────────────────────────────────────┐
│            BaseAdapter (抽象基类)        │
├─────────────────────────────────────────┤
│  + load_data(data: UniData) -> Any      │
│  + wrap_strategy(strategy) -> Callable  │
│  + run(config: UniConfig) -> Dict       │
│  + get_results() -> Dict                │
│  + normalize_result(raw) -> UniResult   │
└─────────────────────────────────────────┘
                    △
                    │ 继承
        ┌───────────┼───────────┐
        │           │           │
┌───────┴───┐ ┌─────┴─────┐ ┌───┴───────┐
│ VectorBT  │ │Backtrader │ │Backtesting │
│ Adapter   │ │ Adapter   │ │.py Adapter │
└───────────┘ └───────────┘ └───────────┘
```

### 6.2 BaseAdapter 接口规范

**文件**: `adapters/base.py`

```python
class BaseAdapter(ABC):
    """适配器基类，定义所有适配器必须实现的接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass
    
    @property
    @abstractmethod
    def framework_version(self) -> str:
        """底层框架版本"""
        pass
    
    @abstractmethod
    def load_data(self, data: UniData) -> Any:
        """加载并转换数据为框架特定格式"""
        pass
    
    @abstractmethod
    def wrap_strategy(self, strategy: UniStrategy) -> Callable:
        """将统一策略包装为框架特定策略"""
        pass
    
    @abstractmethod
    def run(self, config: UniConfig) -> Dict:
        """执行回测，返回原始结果"""
        pass
    
    @abstractmethod
    def normalize_result(self, raw_result: Dict) -> UniResult:
        """将框架特定结果转换为统一格式"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查底层框架是否可用"""
        pass
```

### 6.3 内置适配器说明

| 适配器 | 类名 | 特殊处理 |
|--------|------|----------|
| VectorBT | `VectorBTAdapter` | 矢量化信号数组、Portfolio 模式 |
| Backtrader | `BacktraderAdapter` | Cerebro 引擎、Strategy 类包装 |
| Backtesting.py | `BacktestingPyAdapter` | Strategy 类包装、信号回调转换 |

### 6.4 开发自定义适配器

**步骤**:

1. 继承 `BaseAdapter` 类
2. 实现所有抽象方法
3. 在 `adapters/__init__.py` 中注册
4. 在 `BacktestLayer` 中添加框架映射

**自定义适配器模板**:

```python
from backtest.adapters.base import BaseAdapter

class MyCustomAdapter(BaseAdapter):
    @property
    def name(self) -> str:
        return "my_custom_framework"
    
    def load_data(self, data: UniData) -> Any:
        # 转换数据格式
        pass
    
    def wrap_strategy(self, strategy: UniStrategy) -> Callable:
        # 包装策略
        pass
    
    def run(self, config: UniConfig) -> Dict:
        # 执行回测
        pass
    
    def normalize_result(self, raw_result: Dict) -> UniResult:
        # 结果归一化
        pass
    
    def is_available(self) -> bool:
        # 检查依赖
        pass
```

---

## 7. 使用指南

### 7.1 链式调用

```python
from backtest import BacktestLayer, UniConfig, UniData, UniStrategy, Signal

result = (
    BacktestLayer(framework="vectorbt")
    .set_data(data)
    .set_strategy(MyStrategy())
    .run()
)
```

### 7.2 配置对象模式

```python
config = UniConfig(
    initial_capital=500000,
    commission=0.001,
    slippage=0.0005,
    framework="backtrader"
)

bt = BacktestLayer(config=config)
result = bt.set_data(data).set_strategy(strategy).run()
```

### 7.3 框架切换

```python
bt = BacktestLayer()

# 使用 VectorBT
result_vbt = bt.switch_framework("vectorbt").run()

# 切换到 Backtrader
result_bt = bt.switch_framework("backtrader").run()

# 比较结果
print(f"VectorBT Sharpe: {result_vbt.sharpe_ratio}")
print(f"Backtrader Sharpe: {result_bt.sharpe_ratio}")
```

### 7.4 参数优化

```python
opt_result = (
    BacktestLayer(framework="vectorbt")
    .set_data(data)
    .set_strategy(SMACrossover())
    .optimize(
        param_grid={
            'fast': [5, 10, 15, 20],
            'slow': [20, 30, 40, 50]
        },
        maximize="Sharpe Ratio",
        method="grid"  # 或 "random", "bayesian"
    )
)

print(f"最佳参数: {opt_result.best_params}")
```

### 7.5 完整示例

```python
import pandas as pd
import numpy as np
from backtest import (
    BacktestLayer, UniConfig, UniData, 
    UniStrategy, Signal
)

# 1. 准备数据
dates = pd.date_range('2024-01-01', periods=252, freq='D')
np.random.seed(42)
prices = 100 + np.cumsum(np.random.randn(252) * 0.02)

df = pd.DataFrame({
    'open': prices + np.random.randn(252) * 0.5,
    'high': prices + np.abs(np.random.randn(252)) * 0.5 + 1,
    'low': prices - np.abs(np.random.randn(252)) * 0.5 - 1,
    'close': prices,
    'volume': np.random.randint(10000, 100000, 252)
}, index=dates)

data = UniData.from_dataframe(df, symbol="BTC/USDT", timeframe="1d")

# 2. 定义策略
class SMACrossover(UniStrategy):
    name = "SMACrossover"
    
    def __init__(self, fast: int = 10, slow: int = 30):
        super().__init__()
        self.fast = fast
        self.slow = slow
    
    def init(self, data: UniData):
        close_series = pd.Series(data.close)
        self.ma_fast = close_series.rolling(self.fast).mean()
        self.ma_slow = close_series.rolling(self.slow).mean()
    
    def next(self, bar_idx: int):
        if bar_idx < self.slow:
            return None
        
        if self.ma_fast.iloc[bar_idx] > self.ma_slow.iloc[bar_idx]:
            return Signal.buy(size=0.5)
        else:
            return Signal.close(size=1.0)

# 3. 运行回测
config = UniConfig(
    initial_capital=100000,
    commission=0.001,
    framework="vectorbt"
)

result = (
    BacktestLayer(config=config)
    .set_data(data)
    .set_strategy(SMACrossover(fast=10, slow=30))
    .run()
)

# 4. 输出结果
print(result.summary())
```

---

## 8. 接口规范

### 8.1 对外接口（用户使用）

```python
# 主要导出 - 用户面向的接口
from backtest import (
    # 核心类
    BacktestLayer,     # 回测主入口
    UniConfig,         # 配置类
    UniData,           # 数据类
    UniStrategy,       # 策略基类
    Signal,            # 信号类
    UniResult,         # 结果类
    Trade,             # 交易记录类
    
    # 工厂函数
    create_backtest,   # 快速创建回测实例
    
    # 辅助函数
    get_available_frameworks,  # 获取可用框架列表
    compare_results,           # 比较多个回测结果
)
```

### 8.2 对内接口（适配器开发）

```python
# 适配器开发接口
from backtest.adapters import (
    BaseAdapter,            # 适配器基类
    AdapterRegistry,        # 适配器注册表
    VectorBTAdapter,        # VectorBT 适配器
    BacktraderAdapter,      # Backtrader 适配器
    BacktestingPyAdapter,   # Backtesting.py 适配器
)

# 内部工具函数
from backtest.adapters.utils import (
    normalize_signals,      # 信号归一化
    convert_dataframe,      # 数据格式转换
    calculate_metrics,      # 指标计算
)
```

---

## 9. 实现状态与路线图

### 9.1 已完成功能

| 组件 | 状态 | 说明 |
|------|------|------|
| BacktestLayer | ✅ 完成 | 主入口类已实现 |
| UniConfig | ✅ 完成 | 配置类已实现 |
| UniData | ✅ 完成 | 数据类已实现 |
| UniStrategy | ✅ 完成 | 策略基类已实现 |
| Signal | ✅ 完成 | 信号类已实现 |
| UniResult | ✅ 完成 | 结果类已实现 |
| VectorBT 适配器 | ✅ 完成 | 基本功能已实现 |
| Backtrader 适配器 | ✅ 完成 | 核心功能完成 |
| Backtesting.py 适配器 | ✅ 完成 | 核心功能完成 |

### 9.2 待开发功能

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 多资产组合回测 | 高 | 支持多品种同时回测 |
| 高级订单类型 | 高 | 止损止盈、冰山订单、条件单 |
| 并行回测 | 中 | 多策略/多参数并行执行 |
| 回测报告生成 | 中 | 自动生成 PDF/HTML 报告 |
| 数据缓存机制 | 中 | 提升大数据量回测性能 |
| 实盘接口对接 | 低 | 对接实盘交易接口 |
| 风险指标扩展 | 低 | VaR、CVaR 等高级指标 |
| 完整单元测试 | 高 | 覆盖所有核心组件 |

---

## 10. 技术依赖

### 10.1 运行环境

- **Python 版本**: >= 3.8
- **操作系统**: Windows / Linux / macOS

### 10.2 核心依赖

| 包名 | 版本要求 | 说明 |
|------|----------|------|
| pandas | >= 1.3.0 | 数据处理 |
| numpy | >= 1.20.0 | 数值计算 |

### 10.3 回测框架依赖（按需安装）

| 框架 | 包名 | 版本要求 |
|------|------|----------|
| VectorBT | vectorbt | >= 0.25.0 |
| Backtrader | backtrader | >= 1.9.76 |
| Backtesting.py | backtesting | >= 0.3.3 |

### 10.4 安装命令

```bash
# 核心依赖
pip install pandas numpy

# 按需安装回测框架
pip install vectorbt        # VectorBT
pip install backtrader      # Backtrader
pip install backtesting     # Backtesting.py
```

---

## 附录

### A. 错误码定义

| 错误码 | 说明 |
|--------|------|
| E001 | 数据格式无效 |
| E002 | 策略初始化失败 |
| E003 | 框架不可用 |
| E004 | 参数优化失败 |
| E005 | 回测执行异常 |

### B. 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0.0 | 2026-02-18 | 初始版本，支持三大框架 |
| 1.1.0 | 2026-03-07 | 文档整合，接口规范完善 |

---

**相关文档**:
- [适配器子模块文档](./adapters/README.md)
- [使用示例](./examples/usage.py)