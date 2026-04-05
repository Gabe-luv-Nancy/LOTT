"""
TimescaleDB 表结构管理

提供元数据表和主数据表的创建、管理功能
支持长表格式存储（symbol, time, value）
"""

import logging
from typing import Dict, Any, List, Optional

from .client import TimescaleDBClient, get_client
from .config import TimescaleDBConfig, get_config


logger = logging.getLogger(__name__)


class TableCreator:
    """
    TimescaleDB 表创建器
    
    负责创建和管理 TimescaleDB 超表
    """
    
    def __init__(self, client: TimescaleDBClient = None, config: TimescaleDBConfig = None):
        self.client = client or get_client(config)
        self.config = config or get_config()
        self.schema = self.config.chunk.schema_name
    
    def create_metadata_table(self) -> bool:
        """
        创建元数据表 (data_metadata)
        
        元数据表存储数据源信息，用于去重和追溯
        """
        sql = f"""
        -- 元数据表：存储数据源信息
        CREATE TABLE IF NOT EXISTS {self.schema}.data_metadata (
            id SERIAL PRIMARY KEY,
            
            -- 数据唯一标识（去重依据）
            data_hash TEXT NOT NULL UNIQUE,
            
            -- 来源信息
            source_file TEXT,
            source_type TEXT DEFAULT 'json',  -- json/csv/api
            
            -- 多级列名（支持4级）
            level1 TEXT,  -- 证券代码
            level2 TEXT,  -- 证券名称
            level3 TEXT,  -- 数据类型（开盘价/收盘价等）
            level4 TEXT,  -- 备用
            
            -- 时间信息
            timeframe TEXT NOT NULL,  -- 1min/5min/15min/1h/1d等
            start_time TIMESTAMPTZ,
            end_time TIMESTAMPTZ,
            
            -- 统计信息
            row_count BIGINT DEFAULT 0,
            null_count BIGINT DEFAULT 0,
            value_min DOUBLE PRECISION,
            value_max DOUBLE PRECISION,
            
            -- 元信息
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- 索引
            UNIQUE(source_file, data_hash)
        );
        
        -- 元数据索引
        CREATE INDEX IF NOT EXISTS idx_metadata_hash ON {self.schema}.data_metadata(data_hash);
        CREATE INDEX IF NOT EXISTS idx_metadata_source ON {self.schema}.data_metadata(source_file);
        CREATE INDEX IF NOT EXISTS idx_metadata_levels ON {self.schema}.data_metadata(level1, level2, level3);
        CREATE INDEX IF NOT EXISTS idx_metadata_timeframe ON {self.schema}.data_metadata(timeframe);
        """
        
        try:
            self.client._get_connection()
            # 使用底层连接执行
            conn = self.client._pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
                logger.info(f"元数据表 {self.schema}.data_metadata 创建成功")
                return True
            finally:
                self.client._pool.putconn(conn)
        except Exception as e:
            logger.error(f"创建元数据表失败: {e}")
            return False
    
    def create_timeseries_table(self) -> bool:
        """
        创建主数据表 (timeseries_data)
        
        主数据表存储实际的时序数据，采用长表格式
        """
        chunk_interval = self.config.chunk.time_interval
        compression_days = self.config.retention.compression.after_days
        
        sql = f"""
        -- 主数据表：存储时序数据（长表格式）
        CREATE TABLE IF NOT EXISTS {self.schema}.timeseries_data (
            id SERIAL,
            
            -- 外键关联元数据
            metadata_id INTEGER REFERENCES {self.schema}.data_metadata(id) ON DELETE CASCADE,
            
            -- 数据标识
            symbol TEXT NOT NULL,         -- 证券代码
            symbol_name TEXT,             -- 证券名称
            data_type TEXT NOT NULL,     -- 数据类型（收盘价/成交量等）
            
            -- 时间信息
            timeframe TEXT NOT NULL,     -- 时间间隔
            time TIMESTAMPTZ NOT NULL,  -- 时间点
            
            -- 数据值
            value DOUBLE PRECISION,
            
            -- 元信息
            created_at TIMESTAMPTZ DEFAULT NOW(),
            
            -- 主键（复合主键）
            PRIMARY KEY (metadata_id, time)
        );
        
        -- 转换为超表（TimescaleDB核心）
        SELECT create_hypertable(
            '{self.schema}.timeseries_data', 
            'time',
            if_not_exists => TRUE,
            migrate_data => TRUE,
            chunk_time_interval => INTERVAL '{chunk_interval}'
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_data_symbol_timeframe ON {self.schema}.timeseries_data(symbol, timeframe, time);
        CREATE INDEX IF NOT EXISTS idx_data_metadata_time ON {self.schema}.timeseries_data(metadata_id, time);
        CREATE INDEX IF NOT EXISTS idx_data_type ON {self.schema}.timeseries_data(data_type);
        
        -- 列压缩（如启用）
        ALTER TABLE {self.schema}.timeseries_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'metadata_id, symbol, data_type'
        );
        
        -- 添加压缩策略（{compression_days}天后压缩）
        SELECT add_compression_policy(
            '{self.schema}.timeseries_data', 
            INTERVAL '{compression_days} days',
            if_not_exists => TRUE
        );
        """
        
        try:
            conn = self.client._pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
                logger.info(f"主数据表 {self.schema}.timeseries_data 创建成功")
                return True
            finally:
                self.client._pool.putconn(conn)
        except Exception as e:
            logger.error(f"创建主数据表失败: {e}")
            return False
    
    def create_ohlcv_table(self) -> bool:
        """
        创建 OHLCV 数据表 (ohlcv_data)
        
        用于存储中频 K 线数据（1min 及以上），
        由 DataManage 模块写入，DataFeed 模块也可使用。
        
        表结构：
        - symbol: 合约代码
        - exchange: 交易所
        - timeframe: 周期（1min/5min/1day）
        - time: K 线开始时间
        - open/high/low/close: OHLC 价格
        - volume: 成交量
        - turnover: 成交额
        """
        chunk_interval = self.config.chunk.time_interval
        
        sql = f"""
        CREATE TABLE IF NOT EXISTS {self.schema}.ohlcv_data (
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
        );
        
        -- 转换为超表
        SELECT create_hypertable(
            '{self.schema}.ohlcv_data',
            'time',
            if_not_exists => TRUE,
            migrate_data => TRUE,
            chunk_time_interval => INTERVAL '{chunk_interval}'
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time
            ON {self.schema}.ohlcv_data (symbol, timeframe, time DESC);
        CREATE INDEX IF NOT EXISTS idx_ohlcv_time
            ON {self.schema}.ohlcv_data (time DESC);
        
        -- 压缩配置
        ALTER TABLE {self.schema}.ohlcv_data SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'symbol, exchange, timeframe'
        );
        """
        
        try:
            conn = self.client._pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                conn.commit()
                logger.info(f"OHLCV 表 {self.schema}.ohlcv_data 创建成功")
                return True
            finally:
                self.client._pool.putconn(conn)
        except Exception as e:
            logger.error(f"创建 OHLCV 表失败: {e}")
            return False

    def create_all_tables(self) -> bool:
        """创建所有表"""
        return (self.create_metadata_table() 
                and self.create_timeseries_table() 
                and self.create_ohlcv_table())
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = %s
            )
        """
        conn = self.client._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (self.schema, table_name))
                return cur.fetchone()[0]
        except Exception as e:
            logger.error(f"检查表存在失败: {e}")
            return False
        finally:
            self.client._pool.putconn(conn)
    
    def drop_table(self, table_name: str) -> bool:
        """删除表"""
        try:
            conn = self.client._pool.getconn()
            try:
                with conn.cursor() as cur:
                    cur.execute(f"DROP TABLE IF EXISTS {self.schema}.{table_name} CASCADE")
                conn.commit()
                logger.info(f"表 {self.schema}.{table_name} 已删除")
                return True
            finally:
                self.client._pool.putconn(conn)
        except Exception as e:
            logger.error(f"删除表失败: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """获取表信息"""
        info = {'table_name': table_name}
        
        conn = self.client._pool.getconn()
        try:
            with conn.cursor() as cur:
                # 行数
                cur.execute(f"SELECT COUNT(*) FROM {self.schema}.{table_name}")
                info['row_count'] = cur.fetchone()[0]
                
                # 列信息
                cur.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (self.schema, table_name))
                info['columns'] = [
                    {'name': r[0], 'type': r[1], 'nullable': r[2] == 'YES'}
                    for r in cur.fetchall()
                ]
        except Exception as e:
            logger.error(f"获取表信息失败: {e}")
        finally:
            self.client._pool.putconn(conn)
        
        return info
    
    def list_tables(self) -> List[str]:
        """列出所有表"""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        conn = self.client._pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(query, (self.schema,))
                return [r[0] for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"列出表失败: {e}")
            return []
        finally:
            self.client._pool.putconn(conn)


def create_tables(config: TimescaleDBConfig = None) -> bool:
    """
    创建所有表（便捷函数）
    
    Args:
        config: 数据库配置
        
    Returns:
        是否成功
    """
    from .client import initialize
    
    if not initialize(config):
        return False
    
    creator = TableCreator()
    return creator.create_all_tables()
