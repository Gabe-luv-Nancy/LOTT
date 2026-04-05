"""
数据操作主类 - DataOperation

提供 DataFrame 级别的中频数据（1min+ K 线）增删改查接口。
技术选型：TimescaleDB（与 DataFeed 共用实例）。

用法：
    from Data.DataManage import DataOperation
    
    data_op = DataOperation()
    
    # 添加数据（OHLCV 格式 DataFrame）
    data_op.add(df)
    
    # 查询数据
    result = data_op.query(symbol='IF2406', timeframe='1min', start='2024-01-01')
    
    # 获取统计
    stats = data_op.get_table_stats()
"""

import logging
import os
import sys
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import pandas as pd
import numpy as np

# 添加父目录到路径以支持包导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Data.DataManage.timeseries_io import TimescaleIO

logger = logging.getLogger(__name__)


class DataOperation:
    """
    数据操作管理器 - TimescaleDB 版本
    
    提供 OHLCV 格式的数据增删改查接口，
    支持标准 K 线数据的批量导入与查询。
    """
    
    def __init__(self, config=None):
        """
        初始化
        
        Args:
            config: TimescaleDB 配置，默认从 DataFeed 读取
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self._ts_io = None
        
        # 默认尝试连接 TimescaleDB
        try:
            self._ts_io = TimescaleIO(config=config)
            self._ts_io.create_ohlcv_table()
            self.logger.info("DataOperation (TimescaleDB) 初始化完成")
        except Exception as e:
            self.logger.warning(f"TimescaleDB 连接失败（功能受限）: {e}")
    
    @property
    def ts_io(self) -> TimescaleIO:
        """获取 TimescaleIO 实例（懒加载）"""
        if self._ts_io is None:
            self._ts_io = TimescaleIO(config=self.config)
            self._ts_io.create_ohlcv_table()
        return self._ts_io
    
    def add(self, df: pd.DataFrame, overwrite_strategy: str = 'skip') -> bool:
        """
        添加 OHLCV DataFrame 到 TimescaleDB
        
        Args:
            df: OHLCV DataFrame，必须包含列：
                symbol, exchange, timeframe, time, open, high, low, close, volume
            overwrite_strategy: 覆盖策略（仅 'skip' 和 'overwrite' 支持）
                - 'skip': 跳过重复数据（ON CONFLICT DO NOTHING）
                - 'overwrite': 覆盖重复数据（ON CONFLICT DO UPDATE）
        
        Returns:
            bool: 是否成功
        """
        if df is None or df.empty:
            self.logger.warning("DataFrame 为空，跳过导入")
            return False
        
        if overwrite_strategy not in ('skip', 'overwrite'):
            self.logger.warning(f"不支持的策略 '{overwrite_strategy}'，使用 'skip'")
            overwrite_strategy = 'skip'
        
        try:
            result = self.ts_io.insert_ohlcv(df)
            self.logger.info(
                f"导入完成: {result['rows_imported']} 行成功, "
                f"{result['rows_skipped']} 行跳过"
            )
            return True
        except Exception as e:
            self.logger.error(f"数据导入失败: {e}")
            return False
    
    def query(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        timeframe: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 10000,
    ) -> pd.DataFrame:
        """
        查询 OHLCV 数据
        
        Args:
            symbol: 合约代码过滤（如 'IF2406'）
            exchange: 交易所过滤（如 'CFFEX'）
            timeframe: 周期过滤（如 '1min', '5min', '1day'）
            start: 起始时间（ISO 字符串）
            end: 结束时间（ISO 字符串）
            limit: 最大返回行数
        
        Returns:
            pd.DataFrame: OHLCV 数据
        """
        try:
            return self.ts_io.query_ohlcv(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                start=start,
                end=end,
                limit=limit,
            )
        except Exception as e:
            self.logger.error(f"查询失败: {e}")
            return pd.DataFrame()
    
    def get_table_stats(self) -> Dict:
        """
        获取表统计信息
        
        Returns:
            Dict: 包含行数、合约数、周期数、时间范围等
        """
        try:
            return self.ts_io.get_table_stats()
        except Exception as e:
            self.logger.error(f"获取表统计失败: {e}")
            return {}
    
    def get_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """
        获取数据库中的合约列表
        
        Args:
            exchange: 交易所过滤
        
        Returns:
            List[str]: 合约代码列表
        """
        try:
            df = self.query(exchange=exchange, limit=999999)
            if df.empty:
                return []
            return sorted(df['symbol'].unique().tolist())
        except Exception as e:
            self.logger.error(f"获取合约列表失败: {e}")
            return []
    
    def get_timeframes(self, symbol: Optional[str] = None) -> List[str]:
        """
        获取数据库中的周期列表
        
        Args:
            symbol: 合约代码过滤
        
        Returns:
            List[str]: 周期列表
        """
        try:
            df = self.query(symbol=symbol, limit=999999)
            if df.empty:
                return []
            return sorted(df['timeframe'].unique().tolist())
        except Exception as e:
            self.logger.error(f"获取周期列表失败: {e}")
            return []
    
    def close(self):
        """关闭数据库连接"""
        if self._ts_io:
            self._ts_io.close()
            self._ts_io = None
            self.logger.info("DataOperation 连接已关闭")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
