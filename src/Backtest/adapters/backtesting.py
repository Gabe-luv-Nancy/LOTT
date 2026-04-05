"""
BacktestingPyAdapter - Backtesting.py 框架适配器

特性:
- 简洁易用
- 内置优化功能
- 适合快速原型
- 交互式绘图
"""

import time
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List

from .base import BaseAdapter
from ..config import UniConfig
from ..data import UniData
from ..strategy import UniStrategy
from ..result import UniResult, Trade
from ..signal import Signal


class BacktestingPyAdapter(BaseAdapter):
    """
    Backtesting.py 适配器
    
    使用 backtesting.py 作为底层回测引擎
    """
    
    name = "backtesting.py"
    
    def __init__(self, config: UniConfig = None):
        super().__init__(config)
        self._backtest_instance = None
    
    def run(
        self,
        strategy: UniStrategy,
        data: UniData,
        config: UniConfig
    ) -> UniResult:
        """使用 Backtesting.py 运行回测"""
        self._validate_strategy(strategy)
        self._validate_data(data)
        
        # 检查 backtesting 是否可用
        try:
            from backtesting import Backtest as _Backtest
            from backtesting.lib import crossover
        except ImportError:
            raise ImportError(
                "backtesting 库未安装，请运行: pip install backtesting"
            )
        
        start_time = time.time()
        
        # 准备数据
        df = self._prepare_data(data)
        
        # 创建策略包装类
        strategy_class = self._create_strategy_class(strategy, config)
        
        # 配置回测
        self._backtest_instance = _Backtest(
            df,
            strategy_class,
            cash=config.initial_capital,
            commission=config.commission,
            exclusive_orders=config.exclusive_orders
        )
        
        # 运行回测
        results = self._backtest_instance.run()
        
        # 转换结果
        result = self._extract_results(results, start_time, config)
        
        return result
    
    def _prepare_data(self, data: UniData) -> pd.DataFrame:
        """准备数据，确保包含必需列"""
        df = data.df.copy()
        
        # 转换列名
        column_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and new_col not in df.columns:
                df.rename(columns={old_col: new_col}, inplace=True)
        
        # 检查必需列
        required = ['Open', 'High', 'Low', 'Close']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"数据缺少必需列: {missing}")
        
        # 确保 Volume 列存在
        if 'Volume' not in df.columns:
            df['Volume'] = 0
        
        return df
    
    def _create_strategy_class(self, uni_strategy: UniStrategy, config: UniConfig):
        """动态创建 Backtesting.py 策略类"""
        from backtesting import Strategy
        
        # 获取策略参数
        params_dict = uni_strategy.get_parameters()
        
        class _WrappedStrategy(Strategy):
            """包装后的策略类"""
            
            # 设置参数
            if params_dict:
                for key, value in params_dict.items():
                    locals()[key] = value
            
            def init(self):
                """初始化"""
                # 准备 UniData
                df = pd.DataFrame({
                    'Open': np.array(self.data.Open),
                    'High': np.array(self.data.High),
                    'Low': np.array(self.data.Low),
                    'Close': np.array(self.data.Close),
                    'Volume': np.array(self.data.Volume) if hasattr(self.data, 'Volume') else np.zeros(len(self.data.Close))
                })
                self._uni_data = UniData(df=df)
                self._uni_strategy = uni_strategy
                self._bar_idx = 0
                
                # 调用策略初始化
                self._uni_strategy.init(self._uni_data)
            
            def next(self):
                """每根K线调用"""
                # 调用统一策略的信号生成
                signals = self._uni_strategy.next(self._bar_idx)
                
                if signals:
                    # 处理单个信号或信号元组
                    if not isinstance(signals, (list, tuple)):
                        signals = [signals]
                    
                    for signal in signals:
                        if signal is None:
                            continue
                        
                        self._execute_signal(signal)
                
                self._bar_idx += 1
            
            def _execute_signal(self, signal: Signal):
                """执行信号"""
                if signal.action == Signal.BUY:
                    if signal.size <= 1.0:
                        self.buy(size=signal.size)
                    else:
                        self.buy(size=signal.size)
                elif signal.action == Signal.SELL:
                    if self.position:
                        if signal.size <= 1.0:
                            self.position.close(portion=signal.size)
                        else:
                            self.position.close()
                elif signal.action == Signal.CLOSE:
                    if self.position:
                        self.position.close()
                elif signal.action == Signal.SHORT:
                    if signal.size <= 1.0:
                        self.sell(size=signal.size)
                    else:
                        self.sell(size=signal.size)
                elif signal.action == Signal.COVER:
                    if self.position:
                        self.position.close()
        
        return _WrappedStrategy
    
    def _extract_results(
        self,
        results,
        start_time: float,
        config: UniConfig
    ) -> UniResult:
        """提取 Backtesting.py 结果"""
        duration_ms = (time.time() - start_time) * 1000
        
        result = UniResult()
        result.framework_used = self.name
        result.execution_time_ms = duration_ms
        
        # 从结果对象提取指标
        try:
            result.total_return = results['Return [%]'] / 100
            result.total_return_pct = results['Return [%]']
            result.annualized_return = results['Return (Ann.) [%]'] / 100
            result.sharpe_ratio = results['Sharpe Ratio'] or 0
            result.sortino_ratio = results['Sortino Ratio'] or 0
            result.max_drawdown = abs(results['Max. Drawdown [%]'] / 100)
            result.max_drawdown_pct = abs(results['Max. Drawdown [%]'])
            
            result.total_trades = int(results['# Trades'] or 0)
            result.win_rate = (results['Win Rate [%]'] or 0) / 100
            result.winning_trades = int(result.total_trades * result.win_rate)
            result.losing_trades = result.total_trades - result.winning_trades
            
            avg_win_pct = results['Avg Winning Trade [%]']
            avg_loss_pct = results['Avg Losing Trade [%]']
            result.avg_win = (avg_win_pct or 0) / 100
            result.avg_loss = abs((avg_loss_pct or 0) / 100)
            
            # 盈亏比
            if result.avg_loss > 0:
                result.profit_factor = result.avg_win / result.avg_loss
            else:
                result.profit_factor = float('inf') if result.avg_win > 0 else 0
            
            result.initial_capital = config.initial_capital
            result.final_capital = results['Equity Final [$]']
            result.data_points = result.total_trades * 2
            
            # 权益曲线
            if '_equity_curve' in results:
                equity_data = results['_equity_curve']
                if isinstance(equity_data, pd.DataFrame):
                    result.equity_curve = pd.Series(equity_data['Equity'].values)
        except Exception as e:
            print(f"警告: 提取结果时出错: {e}")
        
        return result
    
    def optimize(
        self,
        strategy: UniStrategy,
        data: UniData,
        config: UniConfig,
        param_grid: Dict,
        maximize: str = "Sharpe Ratio",
        constraint = None,
        max_trials: Optional[int] = None
    ) -> UniResult:
        """使用 Backtesting.py 内置优化"""
        try:
            from backtesting import Backtest as _Backtest
        except ImportError:
            raise ImportError("backtesting 库未安装")
        
        start_time = time.time()
        
        df = self._prepare_data(data)
        strategy_class = self._create_strategy_class(strategy, config)
        
        bt = _Backtest(
            df,
            strategy_class,
            cash=config.initial_capital,
            commission=config.commission,
            exclusive_orders=config.exclusive_orders
        )
        
        # 运行优化
        max_tries = max_trials or 10000
        
        results = bt.optimize(
            **param_grid,
            maximize=maximize,
            max_tries=max_tries,
            constraint=constraint,
            return_optimization=False
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        result = self._extract_results(results, start_time, config)
        result.execution_time_ms = duration_ms
        
        # 尝试获取最优参数
        if hasattr(results, '_strategy'):
            result.optimized_params = {}
        
        return result
    
    def normalize_result(self, native_result: Any) -> UniResult:
        """转换原生结果"""
        return native_result
    
    def plot(self, result: UniResult, **kwargs):
        """绘图"""
        if self._backtest_instance:
            self._backtest_instance.plot(**kwargs)
        else:
            print("请先运行回测后再绘图")