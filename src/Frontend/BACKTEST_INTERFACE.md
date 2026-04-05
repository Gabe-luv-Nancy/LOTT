# 回测接口数据结构定义

## 一、概述

本文档定义 Frontend 回测可视化面板（图层3）与 Backtest 引擎之间的数据接口。
Frontend 不直接依赖 Backtest 模块，而是通过标准化数据结构 `BacktestResult` 接收回测结果。

## 二、核心数据结构

### BacktestResult

```python
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np

@dataclass
class BacktestResult:
    """回测结果数据包"""
    
    # 必需字段
    dates: list                          # 日期序列 (List[datetime])
    prices: np.ndarray                   # 价格序列 (1D array)
    positions: np.ndarray                # 持仓序列 (1D array, 正=多头 负=空头)
    returns: np.ndarray                  # 策略收益率序列 (1D array)
    trades: List['Trade']                # 交易记录列表
    
    # 可选字段
    benchmark_returns: Optional[np.ndarray] = None  # 基准收益率
    strategy_name: str = ""              # 策略名称
    symbol: str = ""                     # 交易品种
    initial_capital: float = 1000000.0   # 初始资金
    
    # 统计摘要（由 BacktestPanel 自动计算，也可预填）
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    win_rate: float = 0.0
```

### Trade

```python
@dataclass
class Trade:
    """单笔交易记录"""
    
    datetime: datetime                   # 交易时间
    direction: str                       # 'BUY' | 'SELL'
    price: float                         # 成交价格
    volume: float                        # 成交数量
    
    # 可选
    pnl: float = 0.0                     # 盈亏
    commission: float = 0.0              # 手续费
    strategy: str = ""                   # 策略名称
    order_id: str = ""                   # 订单ID
```

## 三、数据流向

```
┌─────────────────┐   BacktestResult    ┌─────────────────┐
│  Backtest 引擎   │ ──────────────────→ │  BacktestPanel  │
│  (src/Backtest)  │                     │  (Frontend)     │
└─────────────────┘                     └────────┬────────┘
                                                 │
                               ┌─────────────────┼─────────────────┐
                               │                 │                 │
                        ┌──────▼──────┐  ┌───────▼──────┐  ┌──────▼──────┐
                        │ PriceChart  │  │PositionChart │  │ ReturnChart │
                        │ 价格+交易标记│  │ 持仓柱状图    │  │ 累计收益曲线 │
                        └─────────────┘  └──────────────┘  └─────────────┘
                                                                    │
                                                            ┌───────▼──────┐
                                                            │  TradeList   │
                                                            │  交易明细表   │
                                                            └──────────────┘
```

## 四、使用示例

### 4.1 从 Backtest 引擎获取结果并可视化

```python
from src.Backtest import BacktestEngine
from Frontend.panels.backtest import BacktestPanel, BacktestResult, Trade
from Frontend.run_frontend import quick_backtest

# 1. 运行回测
engine = BacktestEngine(config)
engine.run()
raw_result = engine.get_result()

# 2. 转换为 Frontend 数据结构
result = BacktestResult(
    dates=raw_result['dates'],
    prices=raw_result['prices'],
    positions=raw_result['positions'],
    returns=raw_result['returns'],
    trades=[
        Trade(
            datetime=t['datetime'],
            direction=t['direction'],
            price=t['price'],
            volume=t['volume'],
            pnl=t.get('pnl', 0.0),
        )
        for t in raw_result['trades']
    ],
    strategy_name='金ETF策略',
    symbol='AU2406',
)

# 3. 可视化
quick_backtest(result)
```

### 4.2 组件级使用

```python
# 只使用 PriceChart
from Frontend.panels.backtest import PriceChart

chart = PriceChart()
chart.set_prices(dates, prices)
chart.add_trade_markers(trades)
chart.show()

# 只使用 ReturnChart
from Frontend.panels.backtest import ReturnChart

chart = ReturnChart()
chart.set_returns(dates, returns, benchmark_returns)
chart.show()
```

## 五、面板内部信号

```python
# BacktestPanel 内部信号流
BacktestPanel.load_result(result)
    → PriceChart.set_data(dates, prices, trades)
    → PositionChart.set_data(dates, positions)
    → ReturnChart.set_data(dates, returns, benchmark)
    → TradeList.set_trades(trades)

# 交易选中联动
TradeList.sigTradeSelected → PriceChart.highlight_trade(trade)
PriceChart.sigTradeClicked → TradeList.select_trade(trade)
```

## 六、ReturnChart 计算逻辑

```python
# 累计收益率
cumulative_returns = (1 + returns).cumprod() - 1

# 最大回撤
rolling_max = (1 + cumulative_returns).cummax()
drawdown = (1 + cumulative_returns) / rolling_max - 1
max_drawdown = drawdown.min()

# 基准对比（如提供）
benchmark_cumulative = (1 + benchmark_returns).cumprod() - 1
```
