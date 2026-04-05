"""
TimescaleDB 客户端

提供 TimescaleDB 数据源的连接和操作接口
支持通用查询和 OHLCV/Tick 业务操作
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass

import psycopg2
from psycopg2 import pool
from psycopg2.extras import execute_values

from .config import TimescaleDBConfig, get_config


logger = logging.getLogger(__name__)


@dataclass
class OHLCVData:
    """OHLCV 数据"""
    symbol: str
    exchange: str
    timeframe: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float


class TimescaleDBClient:
    """
    TimescaleDB 客户端
    
    提供时序数据的读写接口
    """
    
    def __init__(self, config: TimescaleDBConfig = None):
        """
        初始化客户端
        
        Args:
            config: TimescaleDB 配置
        """
        self.config = config or get_config()
        self._pool: Optional[pool.ThreadedConnectionPool] = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        连接到 TimescaleDB
        
        Returns:
            是否连接成功
        """
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=self.config.pool.min_connections,
                maxconn=self.config.pool.max_connections,
                host=self.config.host,
                port=self.config.port,
                dbname=self.config.database,
                user=self.config.username,
                password=self.config.password,
                connect_timeout=self.config.pool.timeout
            )
            self._connected = True
            logger.info(f"已连接到 TimescaleDB: {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"连接 TimescaleDB 失败: {e}")
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        if self._pool:
            self._pool.closeall()
            self._pool = None
        self._connected = False
        logger.info("已断开 TimescaleDB 连接")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected and self._pool is not None
    
    def _get_connection(self):
        """获取数据库连接"""
        if not self.is_connected():
            self.connect()
        return self._pool.getconn()
    
    def _return_connection(self, conn):
        """归还连接"""
        if self._pool and conn:
            self._pool.putconn(conn)
    
    @contextmanager
    def get_connection(self):
        """
        获取连接（上下文管理器）
        
        用法:
            with client.get_connection() as conn:
                # 使用 conn
                pass
        """
        if not self.is_connected():
            self.connect()
        
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"执行失败: {e}")
            raise
        finally:
            self._return_connection(conn)
    
    # ==================== 通用查询方法 ====================
    
    def execute(self, query: str, params: Tuple = None) -> bool:
        """
        执行 SQL 语句
        
        Args:
            query: SQL 语句
            params: 参数元组
            
        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return True
    
    def fetch_all(self, query: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """
        查询所有结果（返回字典列表）
        
        Args:
            query: SQL 语句
            params: 参数元组
            
        Returns:
            字典列表
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def fetch_one(self, query: str, params: Tuple = None) -> Optional[Dict[str, Any]]:
        """
        查询单条结果
        
        Args:
            query: SQL 语句
            params: 参数元组
            
        Returns:
            字典或 None
        """
        results = self.fetch_all(query, params)
        return results[0] if results else None
    
    def execute_values(self, query: str, values: List[Tuple]) -> bool:
        """
        批量执行
        
        Args:
            query: SQL 语句（包含 %s 占位符）
            values: 值列表
            
        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, values)
                return True
    
    def execute_script(self, script: str) -> bool:
        """
        执行 SQL 脚本（多条语句）
        
        Args:
            script: SQL 脚本
            
        Returns:
            是否成功
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(script)
                return True
    
    def table_exists(self, table_name: str, schema: str = "public") -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            schema: Schema 名
            
        Returns:
            是否存在
        """
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            )
        """
        result = self.fetch_one(query, (schema, table_name))
        return result['exists'] if result else False
    
    def get_table_columns(self, table_name: str, schema: str = "public") -> List[Dict[str, Any]]:
        """
        获取表结构
        
        Args:
            table_name: 表名
            schema: Schema 名
            
        Returns:
            列信息列表
        """
        query = """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        return self.fetch_all(query, (schema, table_name))
    
    # ==================== 表操作 ====================
    
    def create_tables(self) -> bool:
        """
        创建所需的表结构
        
        Returns:
            是否成功
        """
        if not self.is_connected():
            logger.error("未连接数据库")
            return False
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # 1. 创建 OHLCV 表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ohlcv_data (
                        symbol          TEXT        NOT NULL,
                        exchange        TEXT        NOT NULL,
                        timeframe       TEXT        NOT NULL,
                        time            TIMESTAMPTZ NOT NULL,
                        open            DOUBLE PRECISION,
                        high            DOUBLE PRECISION,
                        low             DOUBLE PRECISION,
                        close           DOUBLE PRECISION,
                        volume          DOUBLE PRECISION,
                        turnover        DOUBLE PRECISION,
                        source          TEXT        DEFAULT 'unknown',
                        created_at      TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (symbol, timeframe, time)
                    );
                """)
                
                # 2. 将 OHLCV 表转换为超表
                cur.execute("""
                    SELECT create_hypertable('ohlcv_data', 'time', 
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    );
                """)
                
                # 3. 创建 Tick 数据表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS tick_data (
                        symbol          TEXT        NOT NULL,
                        exchange        TEXT        NOT NULL,
                        time            TIMESTAMPTZ NOT NULL,
                        last_price      DOUBLE PRECISION,
                        last_volume     DOUBLE PRECISION,
                        bid_price       DOUBLE PRECISION,
                        bid_volume      DOUBLE PRECISION,
                        ask_price       DOUBLE PRECISION,
                        ask_volume      DOUBLE PRECISION,
                        source          TEXT        DEFAULT 'unknown',
                        created_at      TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (symbol, time)
                    );
                """)
                
                # 4. 将 Tick 表转换为超表
                cur.execute("""
                    SELECT create_hypertable('tick_data', 'time',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    );
                """)
                
                # 5. 创建策略信号表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS strategy_signals (
                        strategy_id     TEXT        NOT NULL,
                        symbol          TEXT        NOT NULL,
                        timestamp       TIMESTAMPTZ NOT NULL,
                        signal_type     TEXT        NOT NULL,
                        signal_value    DOUBLE PRECISION,
                        price           DOUBLE PRECISION,
                        metadata        JSONB,
                        created_at      TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (strategy_id, symbol, timestamp)
                    );
                """)
                
                # 6. 将信号表转换为超表
                cur.execute("""
                    SELECT create_hypertable('strategy_signals', 'timestamp',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    );
                """)
                
                # 7. 创建索引
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_tf 
                    ON ohlcv_data (symbol, timeframe);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_tick_symbol 
                    ON tick_data (symbol);
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_signal_strategy_symbol 
                    ON strategy_signals (strategy_id, symbol);
                """)
                
                conn.commit()
                logger.info("表结构创建成功")
                return True
                
        except Exception as e:
            conn.rollback()
            logger.error(f"创建表结构失败: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    # ==================== OHLCV 操作 ====================
    
    def insert_ohlcv(self, data: List[OHLCVData]) -> bool:
        """
        批量插入 OHLCV 数据
        
        Args:
            data: OHLCV 数据列表
            
        Returns:
            是否成功
        """
        if not self.is_connected() or not data:
            return False
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                values = [
                    (
                        d.symbol, d.exchange, d.timeframe, d.time,
                        d.open, d.high, d.low, d.close, d.volume, d.turnover
                    )
                    for d in data
                ]
                
                execute_values(
                    cur,
                    """
                    INSERT INTO ohlcv_data 
                    (symbol, exchange, timeframe, time, open, high, low, close, volume, turnover)
                    VALUES %s
                    ON CONFLICT (symbol, timeframe, time) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        turnover = EXCLUDED.turnover
                    """,
                    values
                )
                
                conn.commit()
                logger.debug(f"插入 {len(data)} 条 OHLCV 数据")
                return True
                
        except Exception as e:
            conn.rollback()
            logger.error(f"插入 OHLCV 数据失败: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    def query_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[OHLCVData]:
        """
        查询 OHLCV 数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            OHLCV 数据列表
        """
        if not self.is_connected():
            return []
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT symbol, exchange, timeframe, time, 
                           open, high, low, close, volume, turnover
                    FROM ohlcv_data
                    WHERE symbol = %s 
                      AND timeframe = %s
                      AND time BETWEEN %s AND %s
                    ORDER BY time ASC
                """, (symbol, timeframe, start_time, end_time))
                
                rows = cur.fetchall()
                return [
                    OHLCVData(
                        symbol=r[0], exchange=r[1], timeframe=r[2], time=r[3],
                        open=r[4], high=r[5], low=r[6], close=r[7], 
                        volume=r[8], turnover=r[9]
                    )
                    for r in rows
                ]
                
        except Exception as e:
            logger.error(f"查询 OHLCV 数据失败: {e}")
            return []
        finally:
            self._return_connection(conn)
    
    # ==================== Tick 操作 ====================
    
    def insert_tick(self, data: List[Dict]) -> bool:
        """
        批量插入 Tick 数据
        
        Args:
            data: Tick 数据列表
            
        Returns:
            是否成功
        """
        if not self.is_connected() or not data:
            return False
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                values = [
                    (
                        d['symbol'], d.get('exchange', 'CFFEX'), d['time'],
                        d.get('last_price'), d.get('last_volume'),
                        d.get('bid_price'), d.get('bid_volume'),
                        d.get('ask_price'), d.get('ask_volume'),
                        d.get('source', 'unknown')
                    )
                    for d in data
                ]
                
                execute_values(
                    cur,
                    """
                    INSERT INTO tick_data 
                    (symbol, exchange, time, last_price, last_volume,
                     bid_price, bid_volume, ask_price, ask_volume, source)
                    VALUES %s
                    """,
                    values
                )
                
                conn.commit()
                return True
                
        except Exception as e:
            conn.rollback()
            logger.error(f"插入 Tick 数据失败: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    # ==================== 信号操作 ====================
    
    def insert_signal(self, data: List[Dict]) -> bool:
        """
        批量插入策略信号
        
        Args:
            data: 信号数据列表
            
        Returns:
            是否成功
        """
        if not self.is_connected() or not data:
            return False
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                values = [
                    (
                        d['strategy_id'], d['symbol'], d['timestamp'],
                        d['signal_type'], d.get('signal_value'),
                        d.get('price'), d.get('metadata')
                    )
                    for d in data
                ]
                
                execute_values(
                    cur,
                    """
                    INSERT INTO strategy_signals 
                    (strategy_id, symbol, timestamp, signal_type, signal_value, price, metadata)
                    VALUES %s
                    """,
                    values
                )
                
                conn.commit()
                return True
                
        except Exception as e:
            conn.rollback()
            logger.error(f"插入信号数据失败: {e}")
            return False
        finally:
            self._return_connection(conn)
    
    # ==================== 统计信息 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        if not self.is_connected():
            return {}
        
        stats = {}
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # OHLCV 数量
                cur.execute("SELECT COUNT(*) FROM ohlcv_data")
                stats['ohlcv_count'] = cur.fetchone()[0]
                
                # Tick 数量
                cur.execute("SELECT COUNT(*) FROM tick_data")
                stats['tick_count'] = cur.fetchone()[0]
                
                # 信号数量
                cur.execute("SELECT COUNT(*) FROM strategy_signals")
                stats['signal_count'] = cur.fetchone()[0]
                
                # 合约列表
                cur.execute("SELECT DISTINCT symbol FROM ohlcv_data")
                stats['symbols'] = [r[0] for r in cur.fetchall()]
                
                # 超表信息
                cur.execute("""
                    SELECT hypertable_name, chunk_count, 
                           range_start, range_end
                    FROM timescaledb_information.hypertables
                """)
                stats['hypertables'] = [
                    {
                        'name': r[0],
                        'chunks': r[1],
                        'range': f"{r[2]} to {r[3]}"
                    }
                    for r in cur.fetchall()
                ]
                
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
        finally:
            self._return_connection(conn)
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态字典
        """
        result = {
            'status': 'healthy',
            'connected': self.is_connected(),
            'checks': {}
        }
        
        if not self.is_connected():
            result['status'] = 'unhealthy'
            result['checks']['connection'] = 'failed'
            return result
        
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result['checks']['connection'] = 'ok'
                
                cur.execute("SELECT COUNT(*) FROM ohlcv_data")
                result['checks']['ohlcv_table'] = 'ok'
                
        except Exception as e:
            result['status'] = 'degraded'
            result['checks']['query'] = str(e)
        finally:
            self._return_connection(conn)
        
        return result


# ==================== 便捷函数 ====================

_client: Optional[TimescaleDBClient] = None


def get_client(config: TimescaleDBConfig = None) -> TimescaleDBClient:
    """获取客户端实例（单例）"""
    global _client
    if _client is None:
        _client = TimescaleDBClient(config)
    return _client


def initialize(config: TimescaleDBConfig = None) -> bool:
    """
    初始化 TimescaleDB 客户端
    
    Args:
        config: 配置
        
    Returns:
        是否成功
    """
    client = get_client(config)
    if client.connect():
        return client.create_tables()
    return False


def close():
    """关闭客户端"""
    global _client
    if _client:
        _client.disconnect()
        _client = None
