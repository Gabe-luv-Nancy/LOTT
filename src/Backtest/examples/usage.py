#!/usr/bin/env python3
"""
UniBacktest 完整使用示例

演示统一回测框架的各项功能:
1. 基本使用
2. 框架切换
3. 参数优化
4. 自定义配置
5. 结果比较
6. 多种策略示例
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pandas as pd
import numpy as np

# 导入回测模块
from src.Backtest import (
    BacktestLayer,
    UniStrategy,
    UniData,
    Signal,
    UniConfig,
    UniResult,
    Trade,
    get_available_frameworks,
    compare_results
)


# ============================================================
# 数据准备
# ============================================================

def create_sample_data(seed: int = 42, periods: int = 252) -> UniData:
    """
    创建示例数据
    
    Args:
        seed: 随机种子
        periods: 数据周期数
        
    Returns:
        UniData: 统一格式数据
    """
    np.random.seed(seed)
    
    dates = pd.date_range('2024-01-01', periods=periods, freq='D')
    
    # 生成带趋势的价格序列
    trend = np.linspace(0, 20, periods)
    noise = np.cumsum(np.random.randn(periods) * 1.5)
    prices = 100 + trend + noise
    
    # 生成 OHLCV 数据
    df = pd.DataFrame({
        'Open': prices * (1 + np.random.randn(periods) * 0.005),
        'High': prices * (1 + np.abs(np.random.randn(periods)) * 0.01 + 0.005),
        'Low': prices * (1 - np.abs(np.random.randn(periods)) * 0.01 - 0.005),
        'Close': prices,
        'Volume': np.random.randint(100000, 1000000, periods).astype(float)
    }, index=dates)
    
    return UniData.from_dataframe(df, symbol="BTC/USDT", timeframe="1d")


# ============================================================
# 策略定义
# ============================================================

class SMACrossoverStrategy(UniStrategy):
    """
    双均线交叉策略
    
    当快速均线上穿慢速均线时买入
    当快速均线下穿慢速均线时卖出
    """
    
    name = "SMA Crossover"
    version = "1.0.0"
    author = "UniBacktest"
    description = "经典双均线交叉策略"
    
    def __init__(self, fast: int = 10, slow: int = 30):
        super().__init__()
        self.fast = fast
        self.slow = slow
        self._params = {'fast': fast, 'slow': slow}
        self._ma_fast = None
        self._ma_slow = None
    
    def init(self, data: UniData):
        """预计算均线指标"""
        close_series = pd.Series(data.close)
        self._ma_fast = close_series.rolling(self.fast).mean().values
        self._ma_slow = close_series.rolling(self.slow).mean().values
    
    def next(self, bar_idx: int):
        """信号生成逻辑"""
        if bar_idx < self.slow:
            return None
        
        if np.isnan(self._ma_fast[bar_idx]) or np.isnan(self._ma_slow[bar_idx]):
            return None
        
        # 金叉买入
        if self._ma_fast[bar_idx] > self._ma_slow[bar_idx]:
            if bar_idx > 0 and self._ma_fast[bar_idx-1] <= self._ma_slow[bar_idx-1]:
                return Signal.buy(size=0.8, tag="金叉买入")
        # 死叉卖出
        elif self._ma_fast[bar_idx] < self._ma_slow[bar_idx]:
            if bar_idx > 0 and self._ma_fast[bar_idx-1] >= self._ma_slow[bar_idx-1]:
                return Signal.close(size=1.0, tag="死叉平仓")
        
        return None


class RSIStrategy(UniStrategy):
    """
    RSI 超买超卖策略
    
    RSI < 30 超卖区买入
    RSI > 70 超买区卖出
    """
    
    name = "RSI Strategy"
    version = "1.0.0"
    
    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        super().__init__()
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self._params = {'period': period, 'oversold': oversold, 'overbought': overbought}
        self._rsi = None
    
    def _calculate_rsi(self, prices: np.ndarray, period: int) -> np.ndarray:
        """计算 RSI 指标"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.zeros(len(prices))
        avg_loss = np.zeros(len(prices))
        
        # 初始平均值
        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])
        
        # 平滑计算
        for i in range(period + 1, len(prices)):
            avg_gain[i] = (avg_gain[i-1] * (period - 1) + gains[i-1]) / period
            avg_loss[i] = (avg_loss[i-1] * (period - 1) + losses[i-1]) / period
        
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 0)
        rsi = 100 - (100 / (1 + rs))
        rsi[:period] = 50  # 填充初始值
        
        return rsi
    
    def init(self, data: UniData):
        """预计算 RSI 指标"""
        self._rsi = self._calculate_rsi(data.close, self.period)
    
    def next(self, bar_idx: int):
        """信号生成逻辑"""
        if bar_idx < self.period + 1:
            return None
        
        current_rsi = self._rsi[bar_idx]
        
        # 超卖区买入
        if current_rsi < self.oversold:
            return Signal.buy(size=0.5, tag=f"RSI超卖({current_rsi:.1f})")
        
        # 超买区卖出
        if current_rsi > self.overbought:
            return Signal.close(size=1.0, tag=f"RSI超买({current_rsi:.1f})")
        
        return None


class BollingerBandsStrategy(UniStrategy):
    """
    布林带策略
    
    价格触及下轨买入
    价格触及上轨卖出
    """
    
    name = "Bollinger Bands"
    version = "1.0.0"
    
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__()
        self.period = period
        self.std_dev = std_dev
        self._params = {'period': period, 'std_dev': std_dev}
        self._upper = None
        self._lower = None
        self._middle = None
    
    def init(self, data: UniData):
        """预计算布林带"""
        close_series = pd.Series(data.close)
        self._middle = close_series.rolling(self.period).mean().values
        std = close_series.rolling(self.period).std().values
        self._upper = self._middle + self.std_dev * std
        self._lower = self._middle - self.std_dev * std
    
    def next(self, bar_idx: int):
        """信号生成逻辑"""
        if bar_idx < self.period:
            return None
        
        # 触及下轨买入
        if self._lower[bar_idx] > 0:
            return Signal.buy(size=0.6, tag="触及下轨")
        
        # 触及上轨卖出
        if self._upper[bar_idx] > 0:
            return Signal.close(size=1.0, tag="触及上轨")
        
        return None


# ============================================================
# 示例函数
# ============================================================

def demo_basic():
    """基本使用演示"""
    print("\n" + "=" * 60)
    print("=== 1. 基本使用演示 ===")
    print("=" * 60)
    
    # 1. 准备数据
    data = create_sample_data()
    print(f"\n[数据信息]")
    print(f"  品种: {data.symbol}")
    print(f"  周期: {data.timeframe}")
    print(f"  K线数: {len(data)}")
    print(f"  时间范围: {data.index[0]} ~ {data.index[-1]}")
    
    # 2. 创建策略
    strategy = SMACrossoverStrategy(fast=10, slow=30)
    print(f"\n[策略信息]")
    print(f"  名称: {strategy.name}")
    print(f"  参数: {strategy.get_parameters()}")
    
    # 3. 运行回测
    print(f"\n[运行回测]")
    result = (
        BacktestLayer(framework="vectorbt")
        .set_data(data)
        .set_strategy(strategy)
        .run()
    )
    
    # 4. 输出结果
    print(result.summary())
    
    return result


def demo_framework_switch():
    """框架切换演示"""
    print("\n" + "=" * 60)
    print("=== 2. 框架切换演示 ===")
    print("=" * 60)
    
    data = create_sample_data()
    strategy = SMACrossoverStrategy(fast=10, slow=30)
    
    # 查看可用框架
    print(f"\n可用框架: {get_available_frameworks()}")
    
    results = {}
    bt = BacktestLayer()
    
    # 遍历所有框架
    for framework in bt.get_available_engines():
        print(f"\n{'─' * 40}")
        print(f"测试框架: {framework}")
        print(f"{'─' * 40}")
        
        try:
            bt.switch_framework(framework)
            result = (
                bt
                .set_data(data)
                .set_strategy(strategy)
                .run()
            )
            results[framework] = result
            print(f"  ✓ 回测成功")
            print(f"  总收益: {result.total_return_pct:.2f}%")
            print(f"  夏普比率: {result.sharpe_ratio:.2f}")
        except ImportError as e:
            print(f"  ✗ 框架未安装: {e}")
            results[framework] = None
        except Exception as e:
            print(f"  ✗ 回测失败: {e}")
            results[framework] = None
    
    # 比较结果
    valid_results = {k: v for k, v in results.items() if v is not None}
    if len(valid_results) > 1:
        print(f"\n{'=' * 40}")
        print("框架对比:")
        print(compare_results(results).to_string(index=False))
    
    return results


def demo_optimization():
    """参数优化演示"""
    print("\n" + "=" * 60)
    print("=== 3. 参数优化演示 ===")
    print("=" * 60)
    
    data = create_sample_data()
    strategy = SMACrossoverStrategy()
    
    # 定义参数网格
    param_grid = {
        'fast': [5, 10, 15],
        'slow': [20, 30, 40]
    }
    
    print(f"\n[优化配置]")
    print(f"  参数网格: {param_grid}")
    print(f"  总试验次数: {3 * 3} = 9")
    print(f"  优化目标: Sharpe Ratio")
    
    print(f"\n[开始优化]")
    try:
        result = (
            BacktestLayer(framework="vectorbt")
            .set_data(data)
            .set_strategy(strategy)
            .optimize(
                param_grid=param_grid,
                maximize="Sharpe Ratio"
            )
        )
        
        print(f"\n[优化结果]")
        print(f"  最优夏普比率: {result.sharpe_ratio:.3f}")
        print(f"  总收益率: {result.total_return_pct:.2f}%")
        if hasattr(result, 'optimized_params'):
            print(f"  最优参数: {result.optimized_params}")
    except Exception as e:
        print(f"  优化失败: {e}")
        result = None
    
    return result


def demo_custom_config():
    """自定义配置演示"""
    print("\n" + "=" * 60)
    print("=== 4. 自定义配置演示 ===")
    print("=" * 60)
    
    # 创建自定义配置
    config = UniConfig(
        initial_capital=500000,      # 50万初始资金
        commission=0.001,            # 0.1% 手续费
        slippage=0.0005,             # 0.05% 滑点
        risk_free_rate=0.03,         # 3% 无风险利率
        framework="vectorbt",
        symbol="ETH/USDT"
    )
    
    print(f"\n[配置信息]")
    print(f"  初始资金: {config.initial_capital:,.0f}")
    print(f"  手续费率: {config.commission:.4f}")
    print(f"  滑点: {config.slippage:.4f}")
    print(f"  无风险利率: {config.risk_free_rate:.2%}")
    
    # 验证配置
    try:
        config.validate()
        print(f"  ✓ 配置验证通过")
    except ValueError as e:
        print(f"  ✗ 配置验证失败: {e}")
        return None
    
    data = create_sample_data()
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    
    result = (
        BacktestLayer(config=config)
        .set_data(data)
        .set_strategy(strategy)
        .run()
    )
    
    print(f"\n[回测结果]")
    print(f"  最终资金: {result.final_capital:,.0f}")
    print(f"  总收益: {result.total_return_pct:.2f}%")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    
    return result


def demo_multiple_strategies():
    """多策略对比演示"""
    print("\n" + "=" * 60)
    print("=== 5. 多策略对比演示 ===")
    print("=" * 60)
    
    data = create_sample_data()
    
    # 定义多个策略
    strategies = {
        'SMA Crossover': SMACrossoverStrategy(fast=10, slow=30),
        'RSI Strategy': RSIStrategy(period=14),
    }
    
    results = {}
    
    for name, strategy in strategies.items():
        print(f"\n{'─' * 40}")
        print(f"策略: {name}")
        print(f"{'─' * 40}")
        
        try:
            result = (
                BacktestLayer(framework="vectorbt")
                .set_data(data)
                .set_strategy(strategy)
                .run()
            )
            results[name] = result
            print(f"  总收益: {result.total_return_pct:.2f}%")
            print(f"  夏普比率: {result.sharpe_ratio:.2f}")
            print(f"  最大回撤: {result.max_drawdown_pct:.2f}%")
            print(f"  交易次数: {result.total_trades}")
        except Exception as e:
            print(f"  回测失败: {e}")
            results[name] = None
    
    # 比较结果
    print(f"\n{'=' * 40}")
    print("策略对比汇总:")
    print(compare_results(results).to_string(index=False))
    
    return results


def demo_data_operations():
    """数据操作演示"""
    print("\n" + "=" * 60)
    print("=== 6. 数据操作演示 ===")
    print("=" * 60)
    
    data = create_sample_data()
    
    print(f"\n[基本信息]")
    print(f"  数据形状: {data.shape}")
    print(f"  数据长度: {len(data)}")
    print(f"  是否为空: {data.empty}")
    
    print(f"\n[数据预览]")
    print(data.head())
    
    print(f"\n[单条K线数据]")
    bar = data.get_bar(100)
    for key, value in bar.items():
        print(f"  {key}: {value}")
    
    print(f"\n[数据切片]")
    sliced = data.slice(0, 50)
    print(f"  原始长度: {len(data)}")
    print(f"  切片后长度: {len(sliced)}")
    
    print(f"\n[数据验证]")
    try:
        data.validate()
        print(f"  ✓ 数据验证通过")
    except ValueError as e:
        print(f"  ✗ 数据验证失败: {e}")
    
    return data


def demo_signal_types():
    """信号类型演示"""
    print("\n" + "=" * 60)
    print("=== 7. 信号类型演示 ===")
    print("=" * 60)
    
    # 创建各种信号
    signals = {
        '买入信号': Signal.buy(size=0.5),
        '卖出信号': Signal.sell(size=0.3),
        '平仓信号': Signal.close(size=1.0),
        '做空信号': Signal.short(size=0.5),
        '平空信号': Signal.cover(size=1.0),
        '限价买入': Signal.buy(size=1.0, limit_price=100.0, order_type='limit'),
        '止损卖出': Signal.sell(size=1.0, stop_price=90.0, order_type='stop'),
    }
    
    for name, signal in signals.items():
        print(f"\n[{name}]")
        print(f"  动作: {signal.action}")
        print(f"  仓位: {signal.size}")
        print(f"  订单类型: {signal.order_type}")
        if signal.limit_price:
            print(f"  限价: {signal.limit_price}")
        if signal.stop_price:
            print(f"  止损价: {signal.stop_price}")
        print(f"  字典格式: {signal.to_dict()}")
    
    return signals


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数"""
    print("\n" + "#" * 60)
    print("# UniBacktest 统一回测框架 - 完整示例")
    print("# 版本: 1.1.0")
    print("#" * 60)
    
    # 运行所有演示
    demo_basic()
    demo_framework_switch()
    demo_optimization()
    demo_custom_config()
    demo_multiple_strategies()
    demo_data_operations()
    demo_signal_types()
    
    print("\n" + "#" * 60)
    print("# 所有演示完成!")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    main()