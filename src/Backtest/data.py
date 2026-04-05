"""
UniData - 统一数据格式

标准化的OHLCV数据结构
"""

from dataclasses import dataclass
from typing import Optional, ClassVar
import pandas as pd
import numpy as np


@dataclass
class UniData:
    """
    统一数据格式
    
    标准化的OHLCV数据结构，内部兼容多种格式
    
    Attributes:
        df: 标准化后的 DataFrame
        symbol: 交易品种
        timeframe: 时间周期
    """
    
    df: pd.DataFrame
    symbol: str = ""
    timeframe: str = "1d"
    
    # 列名映射
    COLUMNS: ClassVar[dict] = {
        'open': 'Open',
        'high': 'High', 
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        'timestamp': 'Timestamp'
    }
    
    def __post_init__(self):
        """初始化后处理"""
        self._standardize_columns()
    
    def _standardize_columns(self):
        """标准化列名"""
        if self.df is None or self.df.empty:
            return
            
        rename_map = {}
        for standard, preferred in self.COLUMNS.items():
            if standard in self.df.columns and standard != preferred:
                rename_map[standard] = preferred
        
        if rename_map:
            self.df = self.df.rename(columns=rename_map)
    
    # === 属性访问器 ===
    
    @property
    def close(self) -> np.ndarray:
        """收盘价"""
        return self.df['Close'].values if 'Close' in self.df.columns else np.array([])
    
    @property
    def open(self) -> np.ndarray:
        """开盘价"""
        return self.df['Open'].values if 'Open' in self.df.columns else np.array([])
    
    @property
    def high(self) -> np.ndarray:
        """最高价"""
        return self.df['High'].values if 'High' in self.df.columns else np.array([])
    
    @property
    def low(self) -> np.ndarray:
        """最低价"""
        return self.df['Low'].values if 'Low' in self.df.columns else np.array([])
    
    @property
    def volume(self) -> np.ndarray:
        """成交量"""
        return self.df['Volume'].values if 'Volume' in self.df.columns else np.array([])
    
    @property
    def index(self) -> pd.DatetimeIndex:
        """时间索引"""
        if isinstance(self.df.index, pd.DatetimeIndex):
            return self.df.index
        elif 'Timestamp' in self.df.columns:
            return pd.to_datetime(self.df['Timestamp'])
        return pd.DatetimeIndex([])
    
    @property
    def shape(self) -> tuple:
        """数据形状"""
        return self.df.shape
    
    @property
    def empty(self) -> bool:
        """是否为空"""
        return self.df.empty
    
    # === 工厂方法 ===
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, symbol: str = "", timeframe: str = "1d") -> "UniData":
        """
        从 DataFrame 创建
        
        Args:
            df: 包含 OHLCV 列的 DataFrame
            symbol: 交易品种
            timeframe: 时间周期
        """
        return cls(df=df.copy(), symbol=symbol, timeframe=timeframe)
    
    @classmethod
    def from_csv(cls, path: str, symbol: str = "", timeframe: str = "1d", **kwargs) -> "UniData":
        """
        从 CSV 文件创建
        
        Args:
            path: CSV 文件路径
            symbol: 交易品种
            timeframe: 时间周期
            **kwargs: pandas read_csv 参数
        """
        df = pd.read_csv(path, **kwargs)
        return cls(df=df, symbol=symbol, timeframe=timeframe)
    
    # === 数据操作 ===
    
    def head(self, n: int = 5) -> pd.DataFrame:
        """获取前n行"""
        return self.df.head(n)
    
    def tail(self, n: int = 5) -> pd.DataFrame:
        """获取后n行"""
        return self.df.tail(n)
    
    def loc(self, key) -> pd.Series:
        """按标签索引"""
        return self.df.loc[key]
    
    def iloc(self, key) -> pd.Series:
        """按位置索引"""
        return self.df.iloc[key]
    
    def __len__(self) -> int:
        """数据长度"""
        return len(self.df)
    
    @property
    def datetime(self) -> np.ndarray:
        """时间戳序列"""
        return self.index.values
    
    def validate(self) -> bool:
        """
        验证数据有效性
        
        Returns:
            bool: 数据是否有效
            
        Raises:
            ValueError: 数据无效时抛出
        """
        if self.df is None or self.df.empty:
            raise ValueError("数据为空")
        
        required_cols = ['Close']
        for col in required_cols:
            if col not in self.df.columns:
                raise ValueError(f"缺少必需列: {col}")
        
        # 检查数据长度
        if len(self.df) < 2:
            raise ValueError("数据点数不足，至少需要2条记录")
        
        return True
    
    def get_bar(self, idx: int) -> dict:
        """
        获取指定位置的K线数据
        
        Args:
            idx: K线索引
            
        Returns:
            dict: 包含 OHLCV 的字典
        """
        if idx < 0 or idx >= len(self.df):
            raise IndexError(f"索引 {idx} 超出范围 [0, {len(self.df)-1}]")
        
        row = self.df.iloc[idx]
        return {
            'open': row.get('Open', row.get('open', 0)),
            'high': row.get('High', row.get('high', 0)),
            'low': row.get('Low', row.get('low', 0)),
            'close': row.get('Close', row.get('close', 0)),
            'volume': row.get('Volume', row.get('volume', 0)),
            'datetime': self.index[idx] if idx < len(self.index) else None
        }
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        转换为 DataFrame
        
        Returns:
            pd.DataFrame: 数据副本
        """
        return self.df.copy()
    
    def slice(self, start: int, end: int) -> "UniData":
        """
        切片数据
        
        Args:
            start: 起始索引
            end: 结束索引
            
        Returns:
            UniData: 切片后的新数据对象
        """
        return UniData(
            df=self.df.iloc[start:end].copy(),
            symbol=self.symbol,
            timeframe=self.timeframe
        )
    
    def __getitem__(self, key) -> pd.Series:
        """支持 [] 索引"""
        return self.df[key]
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"UniData(symbol='{self.symbol}', timeframe='{self.timeframe}', bars={len(self)})"
