"""
BacktestLayer - 统一回测入口类

用户通过此类调用回测，无需关心底层框架
"""

from typing import Optional, Dict, Any, Type
import pandas as pd
import numpy as np
from .config import UniConfig, Framework
from .data import UniData
from .strategy import UniStrategy
from .result import UniResult
from .adapters import (
    BaseAdapter,
    VectorBTAdapter,
    BacktraderAdapter,
    BacktestingPyAdapter
)


class BacktestLayer:
    """
    统一回测入口类
    
    链式调用设计，支持切换底层框架
    
    Attributes:
        FRAMEWORK_VECTORBT: VectorBT 框架常量
        FRAMEWORK_BACKTRADER: Backtrader 框架常量
        FRAMEWORK_BACKTESTING_PY: Backtesting.py 框架常量
    """
    
    FRAMEWORK_VECTORBT = "vectorbt"
    FRAMEWORK_BACKTRADER = "backtrader"
    FRAMEWORK_BACKTESTING_PY = "backtesting.py"
    
    def __init__(
        self,
        config: Optional[UniConfig] = None,
        framework: str = "vectorbt"
    ):
        """
        初始化回测层
        
        Args:
            config: 统一配置对象
            framework: 底层框架选择
        """
        self.config = config or UniConfig(framework=framework)
        self.framework = framework
        self._data: Optional[UniData] = None
        self._strategy: Optional[UniStrategy] = None
        self._result: Optional[UniResult] = None
        
        # 加载对应 Adapter
        self._adapter = self._load_adapter()
    
    # === 核心API ===
    
    def set_data(self, data: UniData) -> "BacktestLayer":
        """
        设置回测数据
        
        Args:
            data: 统一格式的历史数据
            
        Returns:
            self (支持链式调用)
        """
        self._data = data
        return self
    
    def set_strategy(self, strategy: UniStrategy) -> "BacktestLayer":
        """
        设置策略
        
        Args:
            strategy: 策略对象
            
        Returns:
            self (支持链式调用)
        """
        self._strategy = strategy
        return self
    
    def run(self, **kwargs) -> UniResult:
        """
        执行回测
        
        Returns:
            UniResult: 标准化回测结果
        """
        # 参数验证
        self._validate()
        
        # 调用 Adapter 执行回测
        raw_result = self._adapter.run(
            data=self._data,
            strategy=self._strategy,
            config=self.config,
            **kwargs
        )
        
        # 缓存结果
        self._result = raw_result
        
        return raw_result
    
    def optimize(
        self,
        param_grid: Dict[str, Any],
        maximize: str = "Sharpe Ratio",
        constraint = None,
        max_trials: Optional[int] = None,
        **kwargs
    ) -> UniResult:
        """
        参数优化
        
        Args:
            param_grid: 参数网格 {'fast': [10, 20, 30], 'slow': [50, 60]}
            maximize: 优化目标指标
            constraint: 参数约束函数
            max_trials: 最大试验次数
            
        Returns:
            UniResult: 最优结果
        """
        self._validate()
        
        return self._adapter.optimize(
            data=self._data,
            strategy=self._strategy,
            config=self.config,
            param_grid=param_grid,
            maximize=maximize,
            constraint=constraint,
            max_trials=max_trials,
            **kwargs
        )
    
    def plot(self, result: Optional[UniResult] = None, **kwargs) -> None:
        """
        可视化回测结果
        
        Args:
            result: 回测结果 (可选，默认使用最近一次结果)
            **kwargs: 绘图参数
        """
        result = result or self._result
        if result is None:
            raise ValueError("没有可绘图的结果，请先运行回测")
        
        self._adapter.plot(result, **kwargs)
    
    # === 辅助方法 ===
    
    def summary(self) -> str:
        """
        打印回测摘要
        
        Returns:
            str: 摘要字符串
        """
        if self._result:
            return self._result.summary()
        return "No result yet. Run backtest first."
    
    def switch_framework(self, framework: str) -> bool:
        """
        切换底层框架
        
        Args:
            framework: 框架名称
            
        Returns:
            bool: 切换是否成功
        """
        if framework not in [self.FRAMEWORK_VECTORBT, self.FRAMEWORK_BACKTRADER, self.FRAMEWORK_BACKTESTING_PY]:
            raise ValueError(f"不支持的框架: {framework}")
        
        self.framework = framework
        self.config.framework = framework
        self._adapter = self._load_adapter()
        
        print(f"[BacktestLayer] ✓ 已切换到: {framework}")
        return True
    
    def get_available_engines(self) -> list:
        """获取所有可用框架"""
        return [
            self.FRAMEWORK_VECTORBT,
            self.FRAMEWORK_BACKTRADER,
            self.FRAMEWORK_BACKTESTING_PY
        ]
    
    def get_framework_info(self) -> Dict[str, Any]:
        """获取当前框架信息"""
        return {
            "current": self.framework,
            "available": self.get_available_engines(),
            "config": self.config.to_dict()
        }
    
    # === 私有方法 ===
    
    def _load_adapter(self) -> BaseAdapter:
        """加载框架适配器"""
        adapters = {
            self.FRAMEWORK_VECTORBT: VectorBTAdapter,
            self.FRAMEWORK_BACKTRADER: BacktraderAdapter,
            self.FRAMEWORK_BACKTESTING_PY: BacktestingPyAdapter,
        }
        
        adapter_class = adapters.get(self.framework)
        
        if adapter_class is None:
            raise ImportError(
                f"框架 '{self.framework}' 未安装或不可用。"
                f"请安装对应依赖: pip install {self.framework.replace('.py', '')}"
            )
        
        return adapter_class(self.config)
    
    def _validate(self) -> None:
        """参数验证"""
        if self._data is None:
            raise ValueError("数据未设置，请先调用 set_data()")
        
        if self._strategy is None:
            raise ValueError("策略未设置，请先调用 set_strategy()")
        
        if self._data.empty:
            raise ValueError("数据为空")


# === 工厂函数 ===

def create_backtest(
    config: Optional[UniConfig] = None,
    framework: str = "vectorbt"
) -> BacktestLayer:
    """
    创建回测实例的工厂函数
    
    Args:
        config: 统一配置对象
        framework: 底层框架
        
    Returns:
        BacktestLayer 实例
    """
    return BacktestLayer(config=config, framework=framework)


# === 辅助函数 ===

def get_available_frameworks() -> list:
    """
    获取所有可用的回测框架列表
    
    Returns:
        list: 框架名称列表
    """
    return [
        BacktestLayer.FRAMEWORK_VECTORBT,
        BacktestLayer.FRAMEWORK_BACKTRADER,
        BacktestLayer.FRAMEWORK_BACKTESTING_PY
    ]


def compare_results(results: dict) -> pd.DataFrame:
    """
    比较多个回测结果
    
    Args:
        results: 字典，key为框架名称，value为UniResult对象
        
    Returns:
        pd.DataFrame: 比较表格
    """
    comparison_data = []
    
    for framework, result in results.items():
        if result is None:
            continue
        
        comparison_data.append({
            'Framework': framework,
            'Total Return (%)': result.total_return_pct,
            'Annualized Return (%)': result.annualized_return * 100 if result.annualized_return else 0,
            'Sharpe Ratio': result.sharpe_ratio,
            'Max Drawdown (%)': result.max_drawdown_pct,
            'Win Rate (%)': result.win_rate * 100 if result.win_rate else 0,
            'Total Trades': result.total_trades,
            'Profit Factor': result.profit_factor,
            'Execution Time (ms)': result.execution_time_ms
        })
    
    return pd.DataFrame(comparison_data)


# === 使用示例 ===

def example():
    """使用示例"""
    from .data import UniData
    from .strategy import UniStrategy
    from .signal import Signal
    
    # 1. 创建数据
    import pandas as pd
    import numpy as np
    
    dates = pd.date_range('2024-01-01', periods=252)
    data = UniData.from_dataframe(
        pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(252)),
            'open': 100 + np.cumsum(np.random.randn(252)),
            'high': 100 + np.cumsum(np.random.randn(252)) + 1,
            'low': 100 + np.cumsum(np.random.randn(252)) - 1,
            'volume': np.random.randint(1000, 10000, 252)
        }),
        symbol="BTC/USDT"
    )
    
    # 2. 定义策略
    class MyStrategy(UniStrategy):
        name = "MyCustomStrategy"
        
        def init(self, data):
            self.ma_fast = data.close.rolling(10).mean()
            self.ma_slow = data.close.rolling(30).mean()
        
        def next(self, bar_idx):
            if self.ma_fast[bar_idx] > self.ma_slow[bar_idx]:
                return Signal.buy(size=0.5)
            elif self.ma_fast[bar_idx] < self.ma_slow[bar_idx]:
                return Signal.close(size=1.0)
            return None
    
    # 3. 创建回测并运行
    result = (
        BacktestLayer(framework="vectorbt")
        .set_data(data)
        .set_strategy(MyStrategy())
        .run()
    )
    
    print(result.summary())
    
    return result
