"""
UniSignal - 标准化信号格式

Dataclass: Signal
"""

from dataclasses import dataclass, field
from typing import Optional, Literal


@dataclass
class Signal:
    """
    统一信号格式
    
    Attributes:
        action: 信号动作 ('buy', 'sell', 'close', 'short', 'cover')
        size: 仓位比例 (0.0-1.0) 或 绝对手数
        limit_price: 限价单价格
        stop_price: 止损/止盈价格
        order_type: 订单类型 ('market', 'limit', 'stop', 'stop_limit')
        ttl: 订单有效期 (bar数), 0=当日有效
        tag: 订单标签
    """
    
    action: str
    size: float = 1.0
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    order_type: str = "market"
    ttl: int = 0
    tag: str = ""
    
    # === 动作常量 ===
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"
    SHORT = "short"
    COVER = "cover"
    
    # === 订单类型常量 ===
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    
    @classmethod
    def buy(cls, size: float = 1.0, **kwargs) -> "Signal":
        """买入信号"""
        return cls(action=cls.BUY, size=size, **kwargs)
    
    @classmethod
    def sell(cls, size: float = 1.0, **kwargs) -> "Signal":
        """卖出信号"""
        return cls(action=cls.SELL, size=size, **kwargs)
    
    @classmethod
    def close(cls, size: float = 1.0, **kwargs) -> "Signal":
        """平仓信号"""
        return cls(action=cls.CLOSE, size=size, **kwargs)
    
    @classmethod
    def short(cls, size: float = 1.0, **kwargs) -> "Signal":
        """做空信号"""
        return cls(action=cls.SHORT, size=size, **kwargs)
    
    @classmethod
    def cover(cls, size: float = 1.0, **kwargs) -> "Signal":
        """平空信号"""
        return cls(action=cls.COVER, size=size, **kwargs)
    
    def is_long(self) -> bool:
        """是否多头"""
        return self.action in [self.BUY, self.COVER]
    
    def is_short(self) -> bool:
        """是否空头"""
        return self.action in [self.SELL, self.SHORT]
    
    def is_close(self) -> bool:
        """是否平仓"""
        return self.action == self.CLOSE
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "action": self.action,
            "size": self.size,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "order_type": self.order_type,
            "ttl": self.ttl,
            "tag": self.tag
        }
