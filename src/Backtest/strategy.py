"""
UniStrategy - 统一策略接口

抽象基类: UniStrategy
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict, Any, List
from .data import UniData
from .signal import Signal


class UniStrategy(ABC):
    """
    策略抽象基类
    
    子类只需实现核心逻辑，框架差异由 Adapter 处理
    
    Attributes:
        name: 策略名称
        version: 版本号
        author: 作者
        description: 描述
    """
    
    name: str = "BaseStrategy"
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化策略
        
        Args:
            config: 策略配置参数字典
        """
        self.config = config or {}
        self._indicators: Dict[str, Any] = {}
        self._params: Dict[str, Any] = {}
        
        # 初始化参数
        self._init_params()
    
    def _init_params(self):
        """初始化参数 (子类可覆盖)"""
        pass
    
    # === 核心接口 (必须实现) ===
    
    @abstractmethod
    def init(self, data: UniData) -> None:
        """
        初始化阶段 - 计算指标
        
        在回测开始前调用，用于预计算指标
        
        Args:
            data: 统一格式的历史数据
        """
        pass
    
    @abstractmethod
    def next(self, bar_idx: int) -> Optional[Signal]:
        """
        信号生成 - 返回当前bar的订单信号
        
        Args:
            bar_idx: 当前K线索引
            
        Returns:
            Signal 对象或 None
            - Signal.buy(size=0.5)
            - Signal.sell(size=0.3)
            - Signal.close(size=1.0)
            - None (无操作)
        """
        pass
    
    # === 可选接口 (框架特定优化) ===
    
    def on_bar(self, data: UniData, bar_idx: int) -> None:
        """每根K线回调 (可选)"""
        pass
    
    def on_order_filled(self, order: Any) -> None:
        """订单成交回调 (可选)"""
        pass
    
    def on_order_rejected(self, order: Any) -> None:
        """订单拒绝回调 (可选)"""
        pass
    
    def on_train(self, data: UniData) -> None:
        """训练模式回调 (可选，用于ML策略)"""
        pass
    
    # === 参数管理 ===
    
    def get_parameters(self) -> Dict[str, Any]:
        """获取可优化参数"""
        return self._params
    
    def set_parameters(self, **params) -> None:
        """设置参数"""
        self._params.update(params)
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """获取单个参数"""
        return self._params.get(key, default)
    
    def set_parameter(self, key: str, value: Any) -> None:
        """设置单个参数"""
        self._params[key] = value
    
    # === 指标管理 ===
    
    def set_indicator(self, name: str, value: Any) -> None:
        """设置指标"""
        self._indicators[name] = value
    
    def get_indicator(self, name: str) -> Any:
        """获取指标"""
        return self._indicators.get(name)
    
    # === 策略信息 ===
    
    def info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "parameters": self._params
        }
    
    def __str__(self) -> str:
        return f"{self.name} v{self.version}"
