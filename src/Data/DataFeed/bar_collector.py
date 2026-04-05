"""
BarCollector - K线合成器

将 Tick 数据合成 K 线，支持多种周期：
- 1m: 1分钟
- 5m: 5分钟
- 15m: 15分钟
- 1h: 1小时
- 1d: 日线
"""

from typing import Optional
from datetime import datetime
import logging

from vnpy.trader.object import TickData, BarData
from vnpy.trader.constant import Interval


class BarCollector:
    """
    K线收集器
    
    根据 Tick 数据实时合成 K 线。
    """

    def __init__(self, interval: str = "1m"):
        """初始化合成器
        
        Args:
            interval: K 线周期 ("1m", "5m", "15m", "1h", "1d")
        """
        self.interval = interval
        self.logger = logging.getLogger(f"{__name__}.{interval}")
        
        # 当前 K 线
        self.current_bar: Optional[BarData] = None
        
        # 上一根完成的 K 线 (用于去重)
        self.last_bar_time: Optional[datetime] = None

    def update_tick(self, tick: TickData) -> Optional[BarData]:
        """更新并返回完整的 K 线
        
        根据 Tick 数据更新当前 K 线，
        如果有新 K 线生成则返回上一根完成的 K 线。
        
        Args:
            tick: Tick 数据
            
        Returns:
            完成的 K 线，未完成返回 None
        """
        # 确定当前 K 线时间
        bar_time = self._get_bar_time(tick.datetime)
        
        # 新 K 线开始
        if self.current_bar is None or bar_time > self.current_bar.datetime:
            # 保存上一根 K 线
            finished_bar = self.current_bar
            
            # 创建新 K 线
            self.current_bar = BarData(
                symbol=tick.symbol,
                exchange=tick.exchange,
                datetime=bar_time,
                interval=self._get_interval_enum(),
                open_price=tick.last_price,
                high_price=tick.last_price,
                low_price=tick.last_price,
                close_price=tick.last_price,
                volume=tick.volume,
                turnover=tick.last_price * tick.volume,
                open_interest=tick.open_interest,
                gateway_name=tick.gateway_name,
            )
            
            # 避免重复返回
            if finished_bar and finished_bar.datetime == self.last_bar_time:
                return None
            
            if finished_bar:
                self.last_bar_time = finished_bar.datetime
                return finished_bar
        
        # 更新当前 K 线
        self._update_current_bar(tick)
        
        return None

    def _update_current_bar(self, tick: TickData) -> None:
        """更新当前 K 线
        
        Args:
            tick: Tick 数据
        """
        if self.current_bar is None:
            return
        
        # 更新价格
        self.current_bar.high_price = max(
            self.current_bar.high_price, 
            tick.last_price
        )
        self.current_bar.low_price = min(
            self.current_bar.low_price, 
            tick.last_price
        )
        self.current_bar.close_price = tick.last_price
        
        # 更新成交量 (累加)
        self.current_bar.volume += tick.volume
        
        # 更新成交额
        self.current_bar.turnover += tick.last_price * tick.volume
        
        # 更新持仓量 (取最新)
        if tick.open_interest:
            self.current_bar.open_interest = tick.open_interest

    def _get_bar_time(self, dt: datetime) -> datetime:
        """获取 K 线时间边界
        
        Args:
            dt: 当前时间
            
        Returns:
            K 线开始时间
        """
        if self.interval == "1m":
            # 分钟对齐
            return dt.replace(second=0, microsecond=0)
        
        elif self.interval == "5m":
            # 5分钟对齐
            minute = (dt.minute // 5) * 5
            return dt.replace(minute=minute, second=0, microsecond=0)
        
        elif self.interval == "15m":
            # 15分钟对齐
            minute = (dt.minute // 15) * 15
            return dt.replace(minute=minute, second=0, microsecond=0)
        
        elif self.interval == "1h":
            # 小时对齐
            return dt.replace(minute=0, second=0, microsecond=0)
        
        elif self.interval == "1d":
            # 日对齐 (取交易日概念，这里简化为0点)
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 默认返回分钟对齐
        return dt.replace(second=0, microsecond=0)

    def _get_interval_enum(self) -> Interval:
        """获取 vnpy Interval 枚举
        
        Returns:
            Interval 枚举值
        """
        interval_map = {
            "1m": Interval.MINUTE,
            "5m": Interval.MINUTE,
            "15m": Interval.MINUTE,
            "1h": Interval.HOUR,
            "1d": Interval.DAILY,
        }
        return interval_map.get(self.interval, Interval.MINUTE)

    def reset(self) -> None:
        """重置合成器"""
        self.current_bar = None
        self.last_bar_time = None
        self.logger.debug("BarCollector 已重置")

    def get_current_bar(self) -> Optional[BarData]:
        """获取当前 K 线 (未完成)
        
        Returns:
            当前 K 线，未开始返回 None
        """
        return self.current_bar


class MultiIntervalBarCollector:
    """
    多周期 K 线收集器
    
    同时管理多个周期的 K 线合成。
    """

    def __init__(self, intervals: list[str] = None):
        """初始化
        
        Args:
            intervals: K 线周期列表，默认支持所有周期
        """
        if intervals is None:
            intervals = ["1m", "5m", "15m", "1h", "1d"]
        
        self.intervals = intervals
        self.collectors: dict[str, BarCollector] = {}
        
        # 初始化各周期合成器
        for interval in intervals:
            self.collectors[interval] = BarCollector(interval)

    def update_tick(self, tick: TickData) -> dict[str, Optional[BarData]]:
        """更新所有周期的 K 线
        
        Args:
            tick: Tick 数据
            
        Returns:
            各周期完成的 K 线 {interval: BarData or None}
        """
        result = {}
        for interval, collector in self.collectors.items():
            bar = collector.update_tick(tick)
            result[interval] = bar
        
        return result

    def get_current_bars(self) -> dict[str, BarData]:
        """获取所有周期的当前 K 线
        
        Returns:
            各周期当前 K 线
        """
        return {
            interval: collector.get_current_bar()
            for interval, collector in self.collectors.items()
        }

    def reset(self) -> None:
        """重置所有合成器"""
        for collector in self.collectors.values():
            collector.reset()
