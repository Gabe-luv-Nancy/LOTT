#!/usr/bin/env python3
"""
UniBacktest 简单测试脚本

验证框架基本功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import pandas as pd
import numpy as np


def test_import():
    """测试模块导入"""
    print("测试 1: 模块导入...")
    try:
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
        print("  ✓ 所有模块导入成功")
        return True
    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        return False


def test_config():
    """测试配置类"""
    print("\n测试 2: 配置类...")
    from src.Backtest import UniConfig
    
    try:
        # 默认配置
        config1 = UniConfig()
        assert config1.initial_capital == 100000.0
        assert config1.framework == "vectorbt"
        
        # 自定义配置
        config2 = UniConfig(
            initial_capital=500000,
            commission=0.001,
            slippage=0.0005
        )
        assert config2.initial_capital == 500000
        
        # 验证
        config2.validate()
        
        # 转换字典
        d = config2.to_dict()
        assert 'initial_capital' in d
        
        print("  ✓ 配置类测试通过")
        return True
    except Exception as e:
        print(f"  ✗ 配置类测试失败: {e}")
        return False


def test_data():
    """测试数据类"""
    print("\n测试 3: 数据类...")
    from src.Backtest import UniData
    
    try:
        # 创建测试数据
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices = 100 + np.cumsum(np.random.randn(100))
        
        df = pd.DataFrame({
            'Open': prices * 1.01,
            'High': prices * 1.02,
            'Low': prices * 0.99,
            'Close': prices,
            'Volume': np.random.randint(1000, 10000, 100).astype(float)
        }, index=dates)
        
        # 创建 UniData
        data = UniData.from_dataframe(df, symbol="TEST/USDT", timeframe="1d")
        
        # 测试属性
        assert len(data) == 100
        assert data.symbol == "TEST/USDT"
        assert not data.empty
        assert len(data.close) == 100
        
        # 测试验证
        data.validate()
        
        # 测试 get_bar
        bar = data.get_bar(50)
        assert 'close' in bar
        assert 'open' in bar
        
        # 测试切片
        sliced = data.slice(0, 50)
        assert len(sliced) == 50
        
        print("  ✓ 数据类测试通过")
        return True
    except Exception as e:
        print(f"  ✗ 数据类测试失败: {e}")
        return False


def test_signal():
    """测试信号类"""
    print("\n测试 4: 信号类...")
    from src.Backtest import Signal
    
    try:
        # 创建各种信号
        buy_signal = Signal.buy(size=0.5)
        assert buy_signal.action == "buy"
        assert buy_signal.size == 0.5
        
        sell_signal = Signal.sell(size=0.3, tag="止盈")
        assert sell_signal.action == "sell"
        assert sell_signal.tag == "止盈"
        
        close_signal = Signal.close()
        assert close_signal.action == "close"
        
        short_signal = Signal.short(size=0.5)
        assert short_signal.action == "short"
        
        cover_signal = Signal.cover()
        assert cover_signal.action == "cover"
        
        # 测试限价单
        limit_buy = Signal.buy(size=1.0, limit_price=100.0, order_type='limit')
        assert limit_buy.limit_price == 100.0
        assert limit_buy.order_type == 'limit'
        
        # 测试字典转换
        d = buy_signal.to_dict()
        assert d['action'] == 'buy'
        
        print("  ✓ 信号类测试通过")
        return True
    except Exception as e:
        print(f"  ✗ 信号类测试失败: {e}")
        return False


def test_strategy():
    """测试策略类"""
    print("\n测试 5: 策略类...")
    from src.Backtest import UniStrategy, UniData, Signal
    import pandas as pd
    import numpy as np
    
    try:
        # 定义测试策略
        class TestStrategy(UniStrategy):
            name = "TestStrategy"
            
            def __init__(self, period: int = 10):
                super().__init__()
                self.period = period
                self._params = {'period': period}
                self._ma = None
            
            def init(self, data: UniData):
                close_series = pd.Series(data.close)
                self._ma = close_series.rolling(self.period).mean().values
            
            def next(self, bar_idx: int):
                if bar_idx < self.period:
                    return None
                if np.isnan(self._ma[bar_idx]):
                    return None
                if data.close[bar_idx] > self._ma[bar_idx]:
                    return Signal.buy(size=0.5)
                return None
        
        strategy = TestStrategy(period=10)
        
        # 测试属性
        assert strategy.name == "TestStrategy"
        assert strategy.get_parameters() == {'period': 10}
        
        # 测试参数设置
        strategy.set_parameters(period=20)
        assert strategy.get_parameter('period') == 20
        
        print("  ✓ 策略类测试通过")
        return True
    except Exception as e:
        print(f"  ✗ 策略类测试失败: {e}")
        return False


def test_result():
    """测试结果类"""
    print("\n测试 6: 结果类...")
    from src.Backtest import UniResult, Trade
    import pandas as pd
    
    try:
        # 创建结果
        result = UniResult()
        result.framework_used = "test"
        result.total_return_pct = 15.5
        result.sharpe_ratio = 1.5
        result.max_drawdown_pct = 5.0
        result.total_trades = 50
        result.win_rate = 0.6
        result.profit_factor = 1.8
        result.execution_time_ms = 100
        
        # 测试摘要
        summary = result.summary()
        assert "15.5" in summary
        assert "1.5" in summary
        
        # 测试字典转换
        d = result.to_dict()
        assert 'performance' in d
        assert 'trading_stats' in d
        
        # 测试 Trade 类
        trade = Trade(
            entry_date=pd.Timestamp('2024-01-01'),
            entry_price=100.0,
            exit_date=pd.Timestamp('2024-01-05'),
            exit_price=105.0,
            pnl=5.0,
            pnl_pct=0.05,
            size=1.0,
            direction='long',
            duration=5
        )
        trade_dict = trade.to_dict()
        assert trade_dict['pnl'] == 5.0
        
        print("  ✓ 结果类测试通过")
        return True
    except Exception as e:
        print(f"  ✗ 结果类测试失败: {e}")
        return False


def test_backtest_layer():
    """测试回测入口类"""
    print("\n测试 7: 回测入口类...")
    from src.Backtest import BacktestLayer, UniConfig
    
    try:
        # 测试可用框架列表 (静态属性)
        assert "vectorbt" in BacktestLayer.FRAMEWORK_VECTORBT
        assert "backtrader" in BacktestLayer.FRAMEWORK_BACKTRADER
        assert "backtesting.py" in BacktestLayer.FRAMEWORK_BACKTESTING_PY
        print("  ✓ 框架常量定义正确")
        
        # 测试自定义配置
        config = UniConfig(initial_capital=200000)
        assert config.initial_capital == 200000
        print("  ✓ 自定义配置测试通过")
        
        # 测试实例化 (可能因框架未安装而失败)
        try:
            bt = BacktestLayer()
            engines = bt.get_available_engines()
            assert "vectorbt" in engines
            print("  ✓ 回测实例创建成功")
        except ImportError as e:
            print(f"  ⚠ 框架未安装，跳过实例化测试: {str(e)[:50]}...")
        
        print("  ✓ 回测入口类测试通过")
        return True
    except Exception as e:
        print(f"  ✗ 回测入口类测试失败: {e}")
        return False


def test_helper_functions():
    """测试辅助函数"""
    print("\n测试 8: 辅助函数...")
    from src.Backtest import get_available_frameworks, compare_results, UniResult
    import pandas as pd
    
    try:
        # 测试获取可用框架
        frameworks = get_available_frameworks()
        assert len(frameworks) == 3
        assert "vectorbt" in frameworks
        
        # 测试结果比较
        result1 = UniResult()
        result1.framework_used = "vectorbt"
        result1.total_return_pct = 10.0
        result1.sharpe_ratio = 1.0
        result1.max_drawdown_pct = 5.0
        result1.win_rate = 0.5
        result1.total_trades = 100
        result1.profit_factor = 1.5
        result1.execution_time_ms = 100
        
        result2 = UniResult()
        result2.framework_used = "backtrader"
        result2.total_return_pct = 12.0
        result2.sharpe_ratio = 1.2
        result2.max_drawdown_pct = 4.0
        result2.win_rate = 0.55
        result2.total_trades = 80
        result2.profit_factor = 1.6
        result2.execution_time_ms = 150
        
        df = compare_results({
            'vectorbt': result1,
            'backtrader': result2
        })
        
        assert len(df) == 2
        assert 'Framework' in df.columns
        assert 'Sharpe Ratio' in df.columns
        
        print("  ✓ 辅助函数测试通过")
        return True
    except Exception as e:
        print(f"  ✗ 辅助函数测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("UniBacktest 单元测试")
    print("=" * 60)
    
    results = []
    
    # 运行测试
    results.append(("模块导入", test_import()))
    results.append(("配置类", test_config()))
    results.append(("数据类", test_data()))
    results.append(("信号类", test_signal()))
    results.append(("策略类", test_strategy()))
    results.append(("结果类", test_result()))
    results.append(("回测入口类", test_backtest_layer()))
    results.append(("辅助函数", test_helper_functions()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
    else:
        print("\n⚠️ 部分测试失败")
    
    print("=" * 60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)