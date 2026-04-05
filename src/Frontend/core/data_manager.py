"""
数据管理器模块

负责数据管理、缓存和查询接口。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from PyQt5.QtCore import QObject, pyqtSignal


@dataclass
class BarData:
    """K线/数据点结构"""
    datetime: datetime           # 时间戳
    open: float = 0.0           # 开盘价
    high: float = 0.0           # 最高价
    low: float = 0.0            # 最低价
    close: float = 0.0          # 收盘价
    volume: float = 0.0         # 成交量
    turnover: float = 0.0       # 成交额
    open_interest: float = 0.0  # 持仓量（期货）
    
    # 额外数据字典
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.datetime, str):
            self.datetime = pd.to_datetime(self.datetime)


class DataManager(QObject):
    """
    数据管理器
    
    职责：
    - 封装数据操作
    - 管理数据缓存
    - 提供数据变更通知
    """
    
    # ==================== 信号定义 ====================
    sigDataUpdated = pyqtSignal(str, object)  # (source, data)
    sigDataLoaded = pyqtSignal(str, object)   # (source, data)
    
    def __init__(self):
        """初始化数据管理器"""
        super().__init__()
        
        # 数据存储
        self._bars: List[BarData] = []
        self._datetime_index: Dict[datetime, int] = {}  # 时间到索引的映射
        
        # 列数据缓存
        self._column_cache: Dict[str, pd.Series] = {}
        
        # 元数据
        self._metadata: Dict[str, Any] = {}
    
    # ==================== 数据查询接口 ====================
    
    def get_bar(self, ix: int) -> Optional[BarData]:
        """
        获取指定索引的 Bar 数据
        
        Args:
            ix: 数据索引
            
        Returns:
            BarData 对象，不存在返回 None
        """
        if 0 <= ix < len(self._bars):
            return self._bars[ix]
        return None
    
    def get_bars(self, start_ix: int, end_ix: int) -> List[BarData]:
        """
        获取指定范围的 Bar 数据列表
        
        Args:
            start_ix: 起始索引
            end_ix: 结束索引
            
        Returns:
            BarData 列表
        """
        start_ix = max(0, start_ix)
        end_ix = min(len(self._bars), end_ix)
        return self._bars[start_ix:end_ix]
    
    def get_count(self) -> int:
        """
        获取数据总数
        
        Returns:
            数据点总数
        """
        return len(self._bars)
    
    def get_index(self, dt: datetime) -> Optional[int]:
        """
        根据时间获取索引
        
        Args:
            dt: 时间点
            
        Returns:
            索引值，不存在返回 None
        """
        return self._datetime_index.get(dt)
    
    def get_datetime(self, ix: int) -> Optional[datetime]:
        """
        根据索引获取时间
        
        Args:
            ix: 索引值
            
        Returns:
            时间对象，不存在返回 None
        """
        if 0 <= ix < len(self._bars):
            return self._bars[ix].datetime
        return None
    
    # ==================== 列数据查询 ====================
    
    def get_column_data(
        self,
        col_hash: str,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.Series:
        """
        获取指定列的数据
        
        Args:
            col_hash: 列哈希值
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            数据序列
        """
        if col_hash not in self._column_cache:
            return pd.Series()
        
        data = self._column_cache[col_hash]
        
        if start_date is not None and end_date is not None:
            data = data.loc[start_date:end_date]
        elif start_date is not None:
            data = data.loc[start_date:]
        elif end_date is not None:
            data = data.loc[:end_date]
        
        return data
    
    def get_columns_data(
        self,
        col_hashes: List[str],
        start_date: datetime = None,
        end_date: datetime = None
    ) -> pd.DataFrame:
        """
        获取多列数据
        
        Args:
            col_hashes: 列哈希列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame
        """
        data_dict = {}
        for col_hash in col_hashes:
            data = self.get_column_data(col_hash, start_date, end_date)
            if not data.empty:
                data_dict[col_hash] = data
        
        return pd.DataFrame(data_dict)
    
    def set_column_data(self, col_hash: str, data: pd.Series):
        """
        设置列数据
        
        Args:
            col_hash: 列哈希值
            data: 数据序列
        """
        self._column_cache[col_hash] = data
    
    # ==================== 元数据查询 ====================
    
    def get_column_info(
        self,
        level_0: str = None,
        level_1: str = None,
        level_2: str = None
    ) -> pd.DataFrame:
        """
        获取列元数据信息
        
        Args:
            level_0: 第一级筛选（代码）
            level_1: 第二级筛选（名称）
            level_2: 第三级筛选（指标）
            
        Returns:
            元数据 DataFrame
        """
        # 如果有元数据，返回筛选后的结果
        if 'column_info' in self._metadata:
            df = self._metadata['column_info']
            
            if level_0 is not None:
                df = df[df.get('level_0', '') == level_0]
            if level_1 is not None:
                df = df[df.get('level_1', '') == level_1]
            if level_2 is not None:
                df = df[df.get('level_2', '') == level_2]
            
            return df
        
        return pd.DataFrame()
    
    def set_metadata(self, key: str, value: Any):
        """
        设置元数据
        
        Args:
            key: 键
            value: 值
        """
        self._metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            元数据值
        """
        return self._metadata.get(key, default)
    
    # ==================== 数据更新接口 ====================
    
    def update_history(self, history: List[BarData]):
        """
        更新历史数据
        
        Args:
            history: 历史数据列表
        """
        self._bars = list(history)
        self._datetime_index = {}
        
        for i, bar in enumerate(self._bars):
            self._datetime_index[bar.datetime] = i
        
        self.sigDataLoaded.emit('history', self._bars)
    
    def update_bar(self, bar_data: BarData):
        """
        更新单个数据点
        
        Args:
            bar_data: 单个数据点
        """
        ix = self.get_index(bar_data.datetime)
        
        if ix is not None:
            self._bars[ix] = bar_data
        else:
            # 添加新数据
            self._bars.append(bar_data)
            self._datetime_index[bar_data.datetime] = len(self._bars) - 1
        
        self.sigDataUpdated.emit('bar', bar_data)
    
    def clear_all(self):
        """清除所有缓存数据"""
        self._bars.clear()
        self._datetime_index.clear()
        self._column_cache.clear()
        self._metadata.clear()
    
    # ==================== 工具方法 ====================
    
    def get_price_range(self, start_ix: int = None, end_ix: int = None) -> Tuple[float, float]:
        """
        获取价格范围
        
        Args:
            start_ix: 起始索引
            end_ix: 结束索引
            
        Returns:
            (min_price, max_price)
        """
        if not self._bars:
            return (0.0, 1.0)
        
        bars = self._bars[start_ix:end_ix] if start_ix is not None else self._bars
        
        high_prices = [bar.high for bar in bars]
        low_prices = [bar.low for bar in bars]
        
        return (min(low_prices), max(high_prices))
    
    def get_last_bar(self) -> Optional[BarData]:
        """获取最后一个 Bar"""
        return self._bars[-1] if self._bars else None
    
    def get_first_bar(self) -> Optional[BarData]:
        """获取第一个 Bar"""
        return self._bars[0] if self._bars else None
    
    # ==================== 兼容性别名方法 ====================
    
    def add_bar(self, bar: BarData):
        """
        添加单个 Bar 数据（兼容性别名）
        
        Args:
            bar: BarData 对象
        """
        self.update_bar(bar)
    
    def clear(self):
        """清除所有数据（兼容性别名）"""
        self.clear_all()
