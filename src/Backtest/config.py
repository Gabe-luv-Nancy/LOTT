"""
UniConfig - 统一配置参数

Dataclass: BacktestConfig
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class Framework(Enum):
    """支持的回测框架"""
    VECTORBT = "vectorbt"
    BACKTRADER = "backtrader"
    BACKTESTING_PY = "backtesting.py"


@dataclass
class UniConfig:
    """
    统一回测配置
    
    Attributes:
        # === 通用配置 ===
        initial_capital: 初始资金
        commission: 手续费率
        slippage: 滑点
        risk_free_rate: 无风险利率 (用于夏普计算)
        
        # === 数据配置 ===
        data_source: 数据源类型 ("local", "api")
        data_path: 数据路径
        symbol: 交易品种
        timeframe: 时间周期 ("1d", "1h", "15m", etc.)
        start_date: 开始日期
        end_date: 结束日期
        
        # === 回测配置 ===
        framework: 底层框架选择
        benchmark: 基准代码
        exclusive_orders: 互斥订单
        margin: 杠杆/保证金倍数
        
        # === 优化配置 ===
        optimize: 是否参数优化
        optimization_metric: 优化目标指标
        max_trials: 最大试验次数
    """
    
    # === 通用配置 ===
    initial_capital: float = 100000.0
    commission: float = 0.0003
    slippage: float = 0.0001
    risk_free_rate: float = 0.02
    
    # === 数据配置 ===
    data_source: str = "local"
    data_path: Optional[str] = None
    symbol: str = "BTC/USDT"
    timeframe: str = "1d"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # === 回测配置 ===
    framework: str = "vectorbt"
    benchmark: Optional[str] = None
    exclusive_orders: bool = False
    margin: float = 1.0
    
    # === 优化配置 ===
    optimize: bool = False
    optimization_metric: str = "Sharpe Ratio"
    max_trials: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "initial_capital": self.initial_capital,
            "commission": self.commission,
            "slippage": self.slippage,
            "risk_free_rate": self.risk_free_rate,
            "data_source": self.data_source,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "framework": self.framework,
            "optimize": self.optimize,
            "optimization_metric": self.optimization_metric,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UniConfig":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def validate(self) -> bool:
        """
        验证配置参数有效性
        
        Returns:
            bool: 配置是否有效
            
        Raises:
            ValueError: 参数无效时抛出
        """
        if self.initial_capital <= 0:
            raise ValueError("初始资金必须大于0")
        
        if not 0 <= self.commission <= 1:
            raise ValueError("手续费率必须在 0-1 之间")
        
        if not 0 <= self.slippage <= 1:
            raise ValueError("滑点必须在 0-1 之间")
        
        valid_frameworks = ["vectorbt", "backtrader", "backtesting.py"]
        if self.framework not in valid_frameworks:
            raise ValueError(f"不支持的框架: {self.framework}，可选: {valid_frameworks}")
        
        return True
    
    def __post_init__(self):
        """初始化后验证"""
        # 确保 framework 是字符串
        if isinstance(self.framework, Framework):
            self.framework = self.framework.value
