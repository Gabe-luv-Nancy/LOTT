"""
VectorBTAdapter - VectorBT 框架适配器

特性:
- 矢量化回测，极速执行
- 便于参数扫描
- 内置绘图功能
"""

import time
import vectorbt as vbt
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from .base import BaseAdapter
from ..config import UniConfig
from ..data import UniData
from ..strategy import UniStrategy
from ..result import UniResult, Trade
from ..signal import Signal


class VectorBTAdapter(BaseAdapter):
    """
    VectorBT 适配器
    
    使用 VectorBT 作为底层回测引擎
    """
    
    name = "vectorbt"
    
    def run(
        self,
        strategy: UniStrategy,
        data: UniData,
        config: UniConfig
    ) -> UniResult:
        """使用 VectorBT 运行回测"""
        self._validate_strategy(strategy)
        self._validate_data(data)
        
        start_time = time.time()
        
        # 准备数据
        close = data.close
        
        # 生成信号
        entries, exits = self._generate_signals(strategy, close, config)
        
        # 运行回测
        pf = vbt.Portfolio.from_signals(
            close,
            entries=entries,
            exits=exits,
            init_cash=config.initial_capital,
            commission=config.commission,
            slippage=config.slippage,
            freq='D'  # 默认日线
        )
        
        # 提取结果
        result = self.normalize_result(pf, start_time, config)
        
        return result
    
    def _generate_signals(
        self,
        strategy: UniStrategy,
        close: np.ndarray,
        config: UniConfig
    ):
        """生成交易信号"""
        # 创建 UniData 对象供策略使用
        data = UniData(
            df=pd.DataFrame({'Close': close}),
            symbol=config.symbol,
            timeframe=config.timeframe
        )
        
        # 初始化策略
        strategy.init(data)
        
        # 生成信号
        entries = np.zeros(len(close), dtype=bool)
        exits = np.zeros(len(close), dtype=bool)
        
        for i in range(len(close)):
            signals = strategy.next(i)
            if signals:
                for signal in signals:
                    if signal is None:
                        continue
                    if signal.action == Signal.BUY:
                        entries[i] = True
                    elif signal.action == Signal.SELL or signal.action == Signal.CLOSE:
                        exits[i] = True
        
        return entries, exits
    
    def normalize_result(
        self,
        pf: vbt.Portfolio,
        start_time: float,
        config: UniConfig
    ) -> UniResult:
        """转换 VectorBT 结果为统一格式"""
        duration_ms = (time.time() - start_time) * 1000
        
        result = UniResult()
        result.framework_used = self.name
        result.execution_time_ms = duration_ms
        
        # 获取统计信息
        stats = pf.stats()
        
        result.total_return = stats['Total Return [%]'] / 100
        result.total_return_pct = stats['Total Return [%]']
        result.annualized_return = stats['Yearly Return [%]'] / 100
        result.sharpe_ratio = stats['Sharpe Ratio'] or 0
        result.sortino_ratio = stats['Sortino Ratio'] or 0
        result.max_drawdown = abs(stats['Max Drawdown [%]'] / 100)
        result.max_drawdown_pct = abs(stats['Max Drawdown [%]'])
        result.win_rate = stats['Win Rate [%]'] / 100
        
        # 计算盈亏比
        avg_win = stats['Avg Winning Trade [%]'] / 100
        avg_loss = abs(stats['Avg Losing Trade [%]'] / 100)
        if avg_loss > 0:
            result.profit_factor = avg_win / avg_loss
        else:
            result.profit_factor = float('inf')
        
        result.total_trades = int(stats['Total Trades'])
        result.winning_trades = int(stats['Total Trades'] * result.win_rate)
        result.losing_trades = int(stats['Total Trades'] * (1 - result.win_rate))
        result.avg_win = avg_win
        result.avg_loss = avg_loss
        
        # 权益曲线
        result.equity_curve = pf.value().vbt.to_series()
        result.data_points = len(result.equity_curve)
        
        # 初始/最终资金
        result.initial_capital = config.initial_capital
        result.final_capital = pf.value().iloc[-1]
        
        return result
    
    def optimize(
        self,
        strategy: UniStrategy,
        data: UniData,
        config: UniConfig,
        param_grid: Dict,
        maximize: str = "Sharpe Ratio",
        constraint = None,
        max_trials: int = None
    ) -> UniResult:
        """使用 VectorBT 内置优化"""
        import time
        
        start_time = time.time()
        
        # 准备数据
        close = data.close
        
        # 创建 UniData
        uni_data = UniData(
            df=pd.DataFrame({'Close': close}),
            symbol=config.symbol,
            timeframe=config.timeframe
        )
        
        # 定义优化的信号生成函数
        def optimized_signals(close, **params):
            strategy.set_parameters(**params)
            strategy.init(uni_data)
            
            entries = np.zeros(len(close), dtype=bool)
            exits = np.zeros(len(close), dtype=bool)
            
            for i in range(len(close)):
                signals = strategy.next(i)
                if signals:
                    for signal in signals:
                        if signal is None:
                            continue
                        if signal.action == Signal.BUY:
                            entries[i] = True
                        elif signal.action in [Signal.SELL, Signal.CLOSE]:
                            exits[i] = True
            
            return entries, exits
        
        # 运行优化
        pf = vbt.Portfolio.from_signals(
            close,
            init_cash=config.initial_capital,
            commission=config.commission,
            slippage=config.slippage,
            freq='D'
        )
        
        # VectorBT 参数扫描
        results = pf.optimize(
            **param_grid,
            objective=maximize,
            **config.__dict__
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = self.normalize_result(results, start_time, config)
        result.execution_time_ms = duration_ms
        
        return result
    
    def plot(self, result: UniResult, **kwargs):
        """绘图"""
        if result.equity_curve is not None:
            result.equity_curve.vbt.plot(**kwargs)
