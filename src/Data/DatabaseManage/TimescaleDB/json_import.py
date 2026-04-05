"""
JSON 数据导入工具

将 pandas DataFrame 格式的 JSON 数据导入 TimescaleDB
支持多级列名、时间戳转换、去重
"""

import json
import hashlib
import logging
from typing import Dict, Any, List, Tuple, Optional, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

import pandas as pd

from .client import TimescaleDBClient, get_client
from .tables import TableCreator
from .config import TimescaleDBConfig, get_config


logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    metadata_id: Optional[int] = None
    rows_imported: int = 0
    rows_skipped: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class JSONImport:
    """
    JSON 数据导入工具
    
    支持将 pandas DataFrame 格式的 JSON 数据导入 TimescaleDB
    """
    
    def __init__(
        self,
        client: TimescaleDBClient = None,
        config: TimescaleDBConfig = None
    ):
        self.client = client or get_client(config)
        self.config = config or get_config()
        self.table_creator = TableCreator(self.client, self.config)
        self.schema = self.config.chunk.schema_name
    
    # ==================== 哈希计算 ====================
    
    def compute_data_hash(
        self,
        columns: List,
        index: List,
        data: List[List]
    ) -> str:
        """
        计算数据唯一哈希（用于去重判断）
        """
        hash_content = {
            'columns': columns,
            'index': index[:100] if len(index) > 100 else index,
            'data_shape': [len(data), len(data[0]) if data else 0]
        }
        content_str = json.dumps(hash_content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    # ==================== 时间戳转换 ====================
    
    def convert_timestamp(
        self,
        ms_timestamp: int,
        target_timeframe: str = "1min"
    ) -> Tuple[datetime, str]:
        """转换毫秒时间戳"""
        dt = datetime.fromtimestamp(ms_timestamp / 1000, tz=timezone.utc)
        china_tz = timezone(timedelta(hours=8))
        dt = dt.astimezone(china_tz)
        
        if target_timeframe == "1d":
            dt = dt.replace(hour=15, minute=0, second=0, microsecond=0)
        elif target_timeframe == "1h":
            dt = dt.replace(minute=0, second=0, microsecond=0)
        elif target_timeframe == "5min":
            minute = (dt.minute // 5) * 5
            dt = dt.replace(minute=minute, second=0, microsecond=0)
        elif target_timeframe == "1min":
            dt = dt.replace(second=0, microsecond=0)
        
        return dt, target_timeframe
    
    def detect_timeframe(self, index: List[int]) -> str:
        """自动检测时间间隔"""
        if not index or len(index) < 2:
            return "1d"
        
        diffs = [index[i+1] - index[i] for i in range(min(len(index)-1, 100))]
        avg_diff = sum(diffs) / len(diffs)
        seconds = avg_diff / 1000
        
        if seconds >= 86400:
            return "1d"
        elif seconds >= 3600:
            return "1h"
        elif seconds >= 300:
            return "5min"
        elif seconds >= 60:
            return "1min"
        else:
            return "1min"
    
    # ==================== 元数据处理 ====================
    
    def parse_column_level(self, column: List[str], level: int) -> str:
        """解析列名的某一级别"""
        if level <= len(column):
            return column[level - 1]
        return ""
    
    def create_metadata(
        self,
        columns: List[List[str]],
        index: List[int],
        data: List[List],
        source_file: str,
        source_type: str = "json"
    ) -> Optional[int]:
        """创建元数据记录"""
        data_hash = self.compute_data_hash(columns, index, data)
        
        conn = self.client._pool.getconn()
        try:
            with conn.cursor() as cur:
                # 检查是否已存在
                cur.execute(
                    f"SELECT id FROM {self.schema}.data_metadata WHERE data_hash = %s",
                    (data_hash,)
                )
                existing = cur.fetchone()
                
                if existing:
                    logger.info(f"数据已存在，跳过 (hash: {data_hash[:16]}...)")
                    return existing[0]
                
                # 检测时间间隔
                timeframe = self.detect_timeframe(index)
                start_time, _ = self.convert_timestamp(index[0], timeframe)
                end_time, _ = self.convert_timestamp(index[-1], timeframe)
                
                # 计算统计信息
                row_count = len(index)
                all_values = [v for row in data for v in row if v is not None]
                null_count = sum(1 for row in data for v in row if v is None)
                
                first_col = columns[0] if columns else []
                
                sql = f"""
                INSERT INTO {self.schema}.data_metadata (
                    data_hash, source_file, source_type,
                    level1, level2, level3, level4,
                    timeframe, start_time, end_time,
                    row_count, null_count,
                    value_min, value_max,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
                """
                
                cur.execute(sql, (
                    data_hash, source_file, source_type,
                    self.parse_column_level(first_col, 1),
                    self.parse_column_level(first_col, 2),
                    self.parse_column_level(first_col, 3),
                    self.parse_column_level(first_col, 4),
                    timeframe, start_time, end_time,
                    row_count, null_count,
                    min(all_values) if all_values else None,
                    max(all_values) if all_values else None,
                ))
                
                result = cur.fetchone()
                conn.commit()
                logger.info(f"创建元数据记录成功 (id: {result[0]})")
                return result[0]
                
        except Exception as e:
            logger.error(f"创建元数据失败: {e}")
            conn.rollback()
            return None
        finally:
            self.client._pool.putconn(conn)
    
    # ==================== 数据导入 ====================
    
    def import_data(
        self,
        data: Dict[str, Any],
        source_file: str,
        source_type: str = "json",
        batch_size: int = 1000,
        progress_callback: Callable[[int, int], None] = None
    ) -> ImportResult:
        """导入JSON数据"""
        result = ImportResult(success=False)
        
        try:
            columns = data.get('columns', [])
            index = data.get('index', [])
            values = data.get('data', [])
            
            if not columns or not index or not values:
                result.errors.append("数据格式无效")
                return result
            
            # 创建元数据
            metadata_id = self.create_metadata(
                columns, index, values, source_file, source_type
            )
            
            if not metadata_id:
                result.errors.append("创建元数据失败")
                return result
            
            result.metadata_id = metadata_id
            
            # 导入数据
            timeframe = self.detect_timeframe(index)
            total_rows = len(index) * len(columns)
            imported = 0
            skipped = 0
            batch = []
            
            for row_idx, ts_ms in enumerate(index):
                dt, actual_tf = self.convert_timestamp(ts_ms, timeframe)
                
                for col_idx, column in enumerate(columns):
                    if row_idx >= len(values) or col_idx >= len(values[row_idx]):
                        continue
                    
                    value = values[row_idx][col_idx]
                    
                    if value is None:
                        skipped += 1
                        continue
                    
                    batch.append((
                        metadata_id,
                        self.parse_column_level(column, 1),
                        self.parse_column_level(column, 2),
                        self.parse_column_level(column, 3),
                        actual_tf,
                        dt,
                        value
                    ))
                    
                    if len(batch) >= batch_size:
                        self._insert_batch(batch)
                        imported += len(batch)
                        batch = []
                        
                        if progress_callback:
                            progress_callback(imported, total_rows)
            
            if batch:
                self._insert_batch(batch)
                imported += len(batch)
                if progress_callback:
                    progress_callback(imported, total_rows)
            
            result.success = True
            result.rows_imported = imported
            result.rows_skipped = skipped
            
            logger.info(f"导入完成: {imported} 行导入, {skipped} 行跳过")
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"导入失败: {e}")
        
        return result
    
    def _insert_batch(self, batch: List[Tuple]) -> None:
        """批量插入数据"""
        from psycopg2.extras import execute_values
        
        sql = f"""
        INSERT INTO {self.schema}.timeseries_data (
            metadata_id, symbol, symbol_name, data_type,
            timeframe, time, value
        ) VALUES %s
        ON CONFLICT (metadata_id, time) DO NOTHING
        """
        
        conn = self.client._pool.getconn()
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, batch)
            conn.commit()
        finally:
            self.client._pool.putconn(conn)
    
    # ==================== 文件导入 ====================
    
    def import_from_file(
        self,
        file_path: str,
        batch_size: int = 1000,
        progress_callback: Callable[[int, int], None] = None
    ) -> ImportResult:
        """从JSON文件导入"""
        logger.info(f"读取文件: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self.import_data(
            data=data,
            source_file=file_path,
            source_type='json',
            batch_size=batch_size,
            progress_callback=progress_callback
        )
    
    def import_from_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str,
        timeframe: str = "1d",
        batch_size: int = 1000
    ) -> ImportResult:
        """从 pandas DataFrame 导入"""
        data = {
            'columns': [list(col) if isinstance(col, tuple) else [col] 
                       for col in df.columns],
            'index': [int(ts.timestamp() * 1000) if isinstance(ts, datetime) else ts 
                     for ts in df.index],
            'data': df.values.tolist()
        }
        
        return self.import_data(
            data=data,
            source_file=source_name,
            source_type='dataframe',
            batch_size=batch_size
        )


def import_json(
    file_path: str,
    config: TimescaleDBConfig = None,
    batch_size: int = 1000
) -> ImportResult:
    """
    便捷函数：从JSON文件导入
    
    Args:
        file_path: 文件路径
        config: 数据库配置
        batch_size: 批量大小
        
    Returns:
        ImportResult
    """
    from .client import initialize
    
    if not initialize(config):
        return ImportResult(success=False, errors=["连接数据库失败"])
    
    # 确保表存在
    creator = TableCreator()
    creator.create_all_tables()
    
    importer = JSONImport()
    return importer.import_from_file(file_path, batch_size)
