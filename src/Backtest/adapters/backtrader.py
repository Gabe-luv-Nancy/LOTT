"""
BacktraderAdapter - Backtrader 框架适配器

特性:
- 成熟稳定，功能丰富
- 支持多种数据源
- 内置分析器完善
- 事件驱动架构
"""

import time
import backtrader as bt
import pandas as pd
from typing import Dict, Any

from .base import BaseAdapter
from ..config import UniConfig
from ..data import UniData
from ..strategy import UniStrategy
from ..result import UniResult


class BacktraderAdapter(BaseAdapter):
    """
    Backtrader 适配器
    
    使用 Backtrader 作为底层回测引擎
    """
    
    name = "backtrader"
    
    def run(
        self,
        strategy: UniStrategy,
        data: UniData,
        config: UniConfig
    ) -> UniResult:
        """使用 Backtrader 运行回测"""
        self._validate_strategy(strategy)
        self._validate_data(data)
        
        start_time = time.time()
        
        # 创建 Cerebro 引擎
        cerebro = bt.Cerebro()
        
        # 设置初始资金
        cerebro.broker.setcash(config.initial_capital)
        
        # 设置手续费
        cerebro.broker.setcommission(commission=config.commission)
        
        # 设置滑点
        if config.slippage > 0:
            cerebro.broker.set_slippage_perc(perc=config.slippage)
        
        # 准备数据
        data_feed = self._prepare_data(data)
        cerebro.adddata(data_feed)
        
        # 添加策略
        strategy_params = strategy.get_parameters()
        cerebro.addstrategy(
            _BacktraderStrategyWrapper,
            uni_strategy=strategy,
            uni_config=config,
            **strategy_params
        )
        
        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', riskfreerate=config.risk_free_rate)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='max_drawdown')
        
        # 运行回测
        results = cerebro.run()
        
        # 提取结果
        bt_result = results[0]
        result = self._extract_results(bt_result, start_time, config)
        
        return result
    
    def _prepare_data(self, data: UniData) -> bt.feeds.PandasData:
        """将 UniData 转换为 Backtrader 数据源"""
        df = data.df.copy()
        
        # 确保有 datetime 列
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'Timestamp' in df.columns:
                df['datetime'] = pd.to_datetime(df['Timestamp'])
                df.set_index('datetime', inplace=True)
            else:
                df['datetime'] = pd.date_range(start='2000-01-01', periods=len(df))
                df.set_index('datetime', inplace=True)
        
        return bt.feeds.PandasData(
            dataname=df,
            datetime=None,
            open='Open',
            high='High',
            low='Low',
            close='Close',
            volume='Volume',
            openinterest=-1
        )
    
    def _extract_results(
        self,
        bt_result,
        start_time: float,
        config: UniConfig
    ) -> UniResult:
        """提取 Backtrader 结果"""
        duration_ms = (time.time() - start_time) * 1000
        
        result = UniResult()
        result.framework_used = self.name
        result.execution_time_ms = duration_ms
        
        # 获取分析器结果
        sharpe = bt_result.analyzers.sharpe.get_analysis()
        drawdown = bt_result.analyzers.drawdown.get_analysis()
        returns = bt_result.analyzers.returns.get_analysis()
        
        # 计算绩效指标
        final_value = bt_result.broker.getvalue()
        initial_cash = config.initial_capital
        
        result.initial_capital = initial_cash
        result.final_capital = final_value
        result.total_return = (final_value - initial_cash) / initial_cash
        result.total_return_pct = result.total_return * 100
        
        result.sharpe_ratio = sharpe.get('sharpe', 0) or 0
        result.max_drawdown = drawdown.get('max', {}).get('drawdown', 0) or 0
        result.max_drawdown_pct = result.max_drawdown * 100
        
        # 年化收益率 (简化)
        result.annualized_return = result.total_return
        
        # 权益曲线
        equity = bt_result.analyzers.returns.get_analysis()
        result.equity_curve = pd.Series(equity)
        result.data_points = len(result.equity_curve)
        
        return result
    
    def normalize_result(self, native_result: Any) -> UniResult:
        """转换原生结果"""
        return native_result
    
    def plot(self, result: UniResult, **kwargs):
        """绘图"""
        print("请使用 cerebro.plot() 进行 Backtrader 绘图")


class _BacktraderStrategyWrapper(bt.Strategy):
    """Backtrader 策略包装器"""
    
    params = (
        ('uni_strategy', None),
        ('uni_config', None),
    )
    
    def __init__(self):
        self._bar_idx = 0
        self._signals = []
    
    def notify_order(self, order):
        """订单通知回调"""
        if order.status in [order.Completed]:
            if self.p.uni_strategy:
                self.p.uni_strategy.on_order_filled(order)
        elif order.status in [order.Rejected, order.Canceled]:
            if self.p.uni_strategy:
                self.p.uni_strategy.on_order_rejected(order)
    
    def next(self):
        """每根K线调用"""
        if not self.p.uni_strategy:
            return
        
        signals = self.p.uni_strategy.next(self._bar_idx)
        
        if signals:
            # 处理单个信号或信号元组
            if not isinstance(signals, (list, tuple)):
                signals = [signals]
            
            for signal in signals:
                if signal is None:
                    continue
                
                if signal.action == 'buy':
                    size = signal.size
                    if size <= 1.0:  # 比例仓位
                        cash = self.broker.getcash()
                        price = self.data.close[0]
                        size = int((cash * size) / price)
                    self.buy(size=size)
                elif signal.action == 'sell':
                    size = signal.size
                    if size <= 1.0:
                        position = self.position.size
                        size = int(position * size)
                    self.sell(size=size)
                elif signal.action == 'close':
                    self.close()
                elif signal.action == 'short':
                    size = signal.size
                    if size <= 1.0:
                        cash = self.broker.getcash()
                        price = self.data.close[0]
                        size = int((cash * size) / price)
                    self.sell(size=size)
                elif signal.action == 'cover':
                    self.close()
        
        self._bar_idx += 1
