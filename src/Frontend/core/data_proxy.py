"""
数据代理模块

提供数据缓存、转换和预处理功能，优化图表绘制性能。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

from .data_manager import DataManager, BarData


class DataProxy:
    """
    数据代理
    
    职责：
    - 缓存常用数据
    - 数据格式转换
    - 数据预处理（降采样、插值等）
    """
    
    def __init__(self, data_manager: DataManager):
        """
        初始化数据代理
        
        Args:
            data_manager: 数据管理器实例
        """
        self._data_manager = data_manager
        self._cache: Dict[str, Any] = {}
        self._cache_ttl: Dict[str, int] = {}
    
    # ==================== 数据缓存 ====================
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        return self._cache.get(key)
    
    def set_cached_data(self, key: str, data: Any, ttl: int = None):
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 数据
            ttl: 过期时间（秒）
        """
        self._cache[key] = data
        if ttl is not None:
            self._cache_ttl[key] = ttl
    
    def invalidate_cache(self, key: str = None):
        """
        使缓存失效
        
        Args:
            key: 缓存键，为 None 时清除所有缓存
        """
        if key is None:
            self._cache.clear()
            self._cache_ttl.clear()
        else:
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)
    
    # ==================== 数据转换 ====================
    
    def to_pandas_series(self, data: List[BarData], field: str = 'close') -> pd.Series:
        """
        将 BarData 列表转换为 pandas Series
        
        Args:
            data: BarData 列表
            field: 字段名
            
        Returns:
            pandas Series
        """
        if not data:
            return pd.Series()
        
        index = [bar.datetime for bar in data]
        values = [getattr(bar, field, np.nan) for bar in data]
        
        return pd.Series(values, index=index, name=field)
    
    def to_pandas_dataframe(self, data: List[BarData]) -> pd.DataFrame:
        """
        将 BarData 列表转换为 DataFrame
        
        Args:
            data: BarData 列表
            
        Returns:
            DataFrame
        """
        if not data:
            return pd.DataFrame()
        
        records = []
        for bar in data:
            record = {
                'datetime': bar.datetime,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'turnover': bar.turnover,
                'open_interest': bar.open_interest,
            }
            # 添加额外数据
            record.update(bar.extra)
            records.append(record)
        
        df = pd.DataFrame(records)
        df.set_index('datetime', inplace=True)
        return df
    
    def to_numpy_array(self, data: List[BarData], field: str = 'close') -> np.ndarray:
        """
        将数据转换为 numpy 数组
        
        Args:
            data: 数据列表
            field: 字段名
            
        Returns:
            numpy 数组
        """
        if not data:
            return np.array([])
        
        return np.array([getattr(bar, field, np.nan) for bar in data])
    
    # ==================== 数据预处理 ====================
    
    def downsample(
        self,
        data: pd.Series,
        target_freq: str = 'D',
        method: str = 'mean'
    ) -> pd.Series:
        """
        数据降采样
        
        Args:
            data: 原始数据
            target_freq: 目标频率（如 'D', 'W', 'M'）
            method: 聚合方法（'mean', 'sum', 'last'）
            
        Returns:
            降采样后的数据
        """
        if data.empty:
            return data
        
        agg_methods = {
            'mean': 'mean',
            'sum': 'sum',
            'last': 'last',
            'first': 'first',
            'max': 'max',
            'min': 'min',
        }
        
        agg_method = agg_methods.get(method, 'mean')
        return data.resample(target_freq).agg(agg_method)
    
    def interpolate(
        self,
        data: pd.Series,
        method: str = 'linear',
        limit: int = None
    ) -> pd.Series:
        """
        数据插值
        
        Args:
            data: 原始数据
            method: 插值方法（'linear', 'pad', 'nearest'）
            limit: 最大插值数量
            
        Returns:
            插值后的数据
        """
        if data.empty:
            return data
        
        return data.interpolate(method=method, limit=limit)
    
    def normalize(
        self,
        data: pd.Series,
        method: str = 'minmax'
    ) -> pd.Series:
        """
        数据归一化
        
        Args:
            data: 原始数据
            method: 归一化方法（'minmax', 'zscore'）
            
        Returns:
            归一化后的数据
        """
        if data.empty:
            return data
        
        if method == 'minmax':
            min_val = data.min()
            max_val = data.max()
            if max_val == min_val:
                return data - min_val
            return (data - min_val) / (max_val - min_val)
        elif method == 'zscore':
            mean_val = data.mean()
            std_val = data.std()
            if std_val == 0:
                return data - mean_val
            return (data - mean_val) / std_val
        
        return data
    
    def apply_lagging(
        self,
        data: pd.Series,
        lagging: int
    ) -> pd.Series:
        """
        应用滞后阶数
        
        Args:
            data: 原始数据
            lagging: 滞后阶数（正数=滞后，负数=超前）
            
        Returns:
            滞后处理后的数据
        """
        if data.empty or lagging == 0:
            return data
        
        if lagging > 0:
            return data.shift(lagging)
        else:
            return data.shift(lagging)
    
    # ==================== 数据统计 ====================
    
    def get_statistics(self, data: pd.Series) -> Dict[str, float]:
        """
        获取数据统计信息
        
        Args:
            data: 数据序列
            
        Returns:
            统计信息字典
        """
        if data.empty:
            return {}
        
        clean_data = data.dropna()
        
        if clean_data.empty:
            return {}
        
        return {
            'count': len(clean_data),
            'mean': float(clean_data.mean()),
            'std': float(clean_data.std()),
            'min': float(clean_data.min()),
            'max': float(clean_data.max()),
            'median': float(clean_data.median()),
            'q25': float(clean_data.quantile(0.25)),
            'q75': float(clean_data.quantile(0.75)),
        }
    
    def get_y_range(
        self,
        data: pd.Series,
        min_ix: int = None,
        max_ix: int = None,
        padding: float = 0.1
    ) -> Tuple[float, float]:
        """
        获取 Y 轴范围
        
        Args:
            data: 数据序列
            min_ix: 起始索引
            max_ix: 结束索引
            padding: 边距比例
            
        Returns:
            (y_min, y_max)
        """
        if data.empty:
            return (0.0, 1.0)
        
        if min_ix is not None and max_ix is not None:
            data = data.iloc[min_ix:max_ix]
        
        if data.empty:
            return (0.0, 1.0)
        
        y_min = float(data.min())
        y_max = float(data.max())
        
        if y_min == y_max:
            y_min -= 1
            y_max += 1
        
        padding_val = (y_max - y_min) * padding
        return (y_min - padding_val, y_max + padding_val)
    
    # ==================== 置信区间计算 ====================
    
    def calculate_confidence_band(
        self,
        data: pd.Series,
        level: float = 0.95,
        window: int = 20
    ) -> Tuple[pd.Series, pd.Series]:
        """
        计算滚动置信区间
        
        Args:
            data: 数据序列
            level: 置信水平（如0.95）
            window: 滚动窗口大小
            
        Returns:
            (lower_band, upper_band)
        """
        if data.empty or len(data) < window:
            return (pd.Series(), pd.Series())
        
        from scipy import stats
        
        # 滚动统计
        rolling = data.rolling(window=window)
        mean = rolling.mean()
        std = rolling.std()
        
        # 计算置信区间
        alpha = 1 - level
        z_score = stats.norm.ppf(1 - alpha / 2)
        
        margin = std * z_score
        lower = mean - margin
        upper = mean + margin
        
        return (lower, upper)
    
    def calculate_bollinger_bands(
        self,
        data: pd.Series,
        window: int = 20,
        num_std: float = 2.0
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        计算布林带
        
        Args:
            data: 数据序列
            window: 窗口大小
            num_std: 标准差倍数
            
        Returns:
            (middle, lower, upper)
        """
        if data.empty or len(data) < window:
            return (pd.Series(), pd.Series(), pd.Series())
        
        middle = data.rolling(window=window).mean()
        std = data.rolling(window=window).std()
        
        upper = middle + num_std * std
        lower = middle - num_std * std
        
        return (middle, lower, upper)
    
    # ==================== 代理方法 ====================
    
    def get_count(self) -> int:
        """获取数据数量（代理到 DataManager）"""
        return self._data_manager.get_count()
    
    def get_bar(self, ix: int) -> Optional[BarData]:
        """获取指定索引的Bar数据（代理到 DataManager）"""
        return self._data_manager.get_bar(ix)
    
    def get_price_range(self, start_ix: int = None, end_ix: int = None) -> Tuple[float, float]:
        """获取价格范围（代理到 DataManager）"""
        return self._data_manager.get_price_range(start_ix, end_ix)
