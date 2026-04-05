"""
TimescaleDB 中频数据读写模块

本模块负责 1min 及以上 K 线数据的批量读写操作，
与 DataFeed（Tick 高频）共用同一 TimescaleDB 实例。

用法：
    from Data.DataManage.timeseries_io import TimescaleIO
    
    ts = TimescaleIO()
    ts.insert_ohlcv(df)
    result = ts.query_ohlcv(symbol='IF2406', timeframe='1min', start='2024-01-01')
"""

import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import pandas as pd
import numpy as np
from psycopg2 import pool
from psycopg2.extras import execute_values

# 添加父目录到路径，支持未安装时导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 复用 DataFeed 的 TimescaleDB 配置
try:
    from Data.DatabaseManage.TimescaleDB.config import TimescaleDBConfig, get_config
    from Data.DatabaseManage.TimescaleDB.tables import TableCreator
    _HAS_DATAFEED = True
except ImportError:
    _HAS_DATAFEED = False
    TimescaleDBConfig = None
    get_config = None
    TableCreator = None

logger = logging.getLogger(__name__)


class TimescaleIO:
    """
    TimescaleDB 中频数据读写器
    
    负责 1min 及以上 K 线数据的读写，
    数据格式为标准 OHLCV 长表（symbol + time 唯一键）。
    """
    
    def __init__(self, config: TimescaleDBConfig = None):
        """
        初始化
        
        Args:
            config: TimescaleDB 配置，默认从 DataFeed 读取
        """
        if config is None and _HAS_DATAFEED:
            config = get_config()
        
        self.config = config
        self._pool = None
        self._connect()
    
    def _connect(self):
        """建立连接池"""
        if self.config is None:
            raise RuntimeError(
                "TimescaleDB 配置未找到。"
                "请确保 DataFeed/TimescaleDB 已配置，或传入 config 参数。"
            )
        
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
            )
            logger.info(f"TimescaleDB 连接池已建立: {self.config.host}:{self.config.port}")
        except Exception as e:
            logger.error(f"TimescaleDB 连接失败: {e}")
            raise
    
    def insert_ohlcv(
        self,
        df: pd.DataFrame,
        if_exists: str = 'append',
        batch_size: int = 1000
    ) -> Dict[str, int]:
        """
        批量写入 OHLCV 数据
        
        Args:
            df: DataFrame，必须包含以下列：
                - symbol (str): 合约代码
                - exchange (str): 交易所
                - timeframe (str): 周期（1min/5min/1day）
                - time (datetime): K 线开始时间
                - open, high, low, close (float): OHLC
                - volume (float): 成交量
            if_exists: 'append'（追加）或 'replace'（替换）
            batch_size: 每批写入行数
        
        Returns:
            Dict: {'rows_imported': N, 'rows_skipped': M}
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空，跳过导入")
            return {'rows_imported': 0, 'rows_skipped': 0}
        
        required_cols = ['symbol', 'exchange', 'timeframe', 'time', 'open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"DataFrame 缺少必要列: {missing}")
        
        # 准备数据
        records = []
        for _, row in df.iterrows():
            records.append((
                str(row['symbol']),
                str(row['exchange']),
                str(row['timeframe']),
                row['time'] if isinstance(row['time'], datetime) else pd.to_datetime(row['time']),
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                float(row['volume']),
                float(row.get('turnover', 0.0)),
            ))
        
        sql = """
            INSERT INTO ohlcv_data 
            (symbol, exchange, timeframe, time, open, high, low, close, volume, turnover)
            VALUES %s
            ON CONFLICT (symbol, exchange, timeframe, time) 
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                turnover = EXCLUDED.turnover
        """
        
        conn = self._pool.getconn()
        try:
            cursor = conn.cursor()
            
            total = len(records)
            imported = 0
            for i in range(0, total, batch_size):
                batch = records[i:i + batch_size]
                execute_values(cursor, sql, batch)
                imported += len(batch)
                logger.info(f"写入进度: {imported}/{total}")
            
            conn.commit()
            logger.info(f"✅ OHLCV 导入完成: {imported} 行")
            return {'rows_imported': imported, 'rows_skipped': total - imported}
        
        except Exception as e:
            conn.rollback()
            logger.error(f"OHLCV 导入失败: {e}")
            raise
        finally:
            self._pool.putconn(conn)
    
    def query_ohlcv(
        self,
        symbol: Optional[str] = None,
        exchange: Optional[str] = None,
        timeframe: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        limit: int = 10000
    ) -> pd.DataFrame:
        """
        查询 OHLCV 数据
        
        Args:
            symbol: 合约代码过滤
            exchange: 交易所过滤
            timeframe: 周期过滤
            start: 起始时间（ISO 字符串或 datetime）
            end: 结束时间
            limit: 最大返回行数
        
        Returns:
            pd.DataFrame: OHLCV 数据
        """
        conditions = []
        params = {}
        
        if symbol:
            conditions.append("symbol = %(symbol)s")
            params['symbol'] = symbol
        if exchange:
            conditions.append("exchange = %(exchange)s")
            params['exchange'] = exchange
        if timeframe:
            conditions.append("timeframe = %(timeframe)s")
            params['timeframe'] = timeframe
        if start:
            conditions.append("time >= %(start)s")
            params['start'] = start
        if end:
            conditions.append("time <= %(end)s")
            params['end'] = end
        
        where = " AND ".join(conditions) if conditions else "1=1"
        
        sql = f"""
            SELECT symbol, exchange, timeframe, time, open, high, low, close, volume, turnover
            FROM ohlcv_data
            WHERE {where}
            ORDER BY time DESC
            LIMIT %(limit)s
        """
        params['limit'] = limit
        
        conn = self._pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            if not rows:
                return pd.DataFrame()
            
            df = pd.DataFrame(rows, columns=[
                'symbol', 'exchange', 'timeframe', 'time',
                'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            df['time'] = pd.to_datetime(df['time'])
            return df
        
        finally:
            self._pool.putconn(conn)
    
    def get_table_stats(self) -> Dict:
        """获取表统计信息"""
        sql = """
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT symbol) as symbol_count,
                COUNT(DISTINCT timeframe) as timeframe_count,
                MIN(time) as earliest,
                MAX(time) as latest
            FROM ohlcv_data
        """
        conn = self._pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            row = cursor.fetchone()
            return {
                'total_rows': row[0] or 0,
                'symbol_count': row[1] or 0,
                'timeframe_count': row[2] or 0,
                'earliest': row[3],
                'latest': row[4],
            }
        finally:
            self._pool.putconn(conn)
    
    def create_ohlcv_table(self):
        """创建 OHLCV 表（如不存在）"""
        if _HAS_DATAFEED and TableCreator:
            creator = TableCreator(config=self.config)
            creator.create_ohlcv_table()
            return
        
        conn = self._pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_data (
                    id BIGSERIAL,
                    symbol TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    time TIMESTAMPTZ NOT NULL,
                    open DOUBLE PRECISION NOT NULL,
                    high DOUBLE PRECISION NOT NULL,
                    low DOUBLE PRECISION NOT NULL,
                    close DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION NOT NULL,
                    turnover DOUBLE PRECISION DEFAULT 0,
                    PRIMARY KEY (symbol, exchange, timeframe, time)
                )
            """)
            cursor.execute("""
                SELECT 1 FROM pg_indexes WHERE tablename = 'ohlcv_data' AND indexname = 'ohlcv_data_time_idx'
            """)
            if not cursor.fetchone():
                cursor.execute("""
                    CREATE INDEX idx_ohlcv_time ON ohlcv_data (time DESC)
                """)
            
            # 转换为超表（TimescaleDB）
            cursor.execute("""
                SELECT 1 FROM timescaledb_information.hypertables WHERE hypertable_name = 'ohlcv_data'
            """)
            if not cursor.fetchone():
                cursor.execute("SELECT create_hypertable('ohlcv_data', 'time', if_not_exists:=TRUE)")
            
            conn.commit()
            logger.info("✅ ohlcv_data 表创建完成（已是超表）")
        except Exception as e:
            conn.rollback()
            logger.warning(f"创建表时出现警告（可能已存在）: {e}")
        finally:
            self._pool.putconn(conn)
    
    def close(self):
        """关闭所有连接"""
        if self._pool:
            self._pool.closeall()
            logger.info("TimescaleDB 连接池已关闭")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("TimescaleIO 连接测试...")
    try:
        ts = TimescaleIO()
        stats = ts.get_table_stats()
        print(f"✅ 连接成功！表统计: {stats}")
        ts.close()
    except Exception as e:
        print(f"❌ 连接失败: {e}")
