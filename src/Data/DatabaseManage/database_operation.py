"""
数据库操作模块 - DatabaseOperations + TimescaleDBOperations
"""

import logging
import threading
from typing import Any, Dict, List, Optional
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy import text, inspect

from .database_tables import Base, MetaColData, TimeSeriesData
from .database_config import DatabaseConfig
from .utils import _now, hashit, INVALID_VALUES, IF_INVALID


class DatabaseOperations:
    """数据库操作接口 - 封装所有数据库操作"""
    
    def __init__(self, connection):
        self.connection = connection
        self.logger = logging.getLogger(__name__)
    
    def execute_sql(self, sql: str, params=None) -> Any:
        """执行SQL语句"""
        session = self.connection.get_session()
        try:
            if isinstance(params, (list, tuple)):
                # 转换位置参数为字典参数
                result = session.execute(text(sql), params)
            else:
                result = session.execute(text(sql), params or {})
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            self.logger.error(f"SQL执行失败: {sql}, 错误: {e}")
            raise
        finally:
            session.close()
    
    def fetch_all(self, sql: str, params=None) -> List[Any]:
        """查询所有结果"""
        session = self.connection.get_session()
        try:
            if isinstance(params, (list, tuple)):
                result = session.execute(text(sql), params)
            else:
                result = session.execute(text(sql), params or {})
            return result.fetchall()
        except Exception as e:
            self.logger.error(f"查询失败: {sql}, 错误: {e}")
            raise
        finally:
            session.close()
    
    def fetch_one(self, sql: str, params=None) -> Any:
        """查询单个结果"""
        session = self.connection.get_session()
        try:
            if isinstance(params, (list, tuple)):
                result = session.execute(text(sql), params)
            else:
                result = session.execute(text(sql), params or {})
            return result.fetchone()
        except Exception as e:
            self.logger.error(f"查询失败: {sql}, 错误: {e}")
            raise
        finally:
            session.close()
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        inspector = inspect(self.connection.engine)
        return table_name in inspector.get_table_names()
    
    def col_exists(self, table_name: str, colname: str) -> bool:
        """检查列是否存在"""
        inspector = inspect(self.connection.engine)
        columns = inspector.get_columns(table_name)
        return any(col['name'] == colname for col in columns)
    
    def table_add_col(self, table_name: str, colname: str, column_type: str = "REAL") -> bool:
        """表添加列"""
        if self.col_exists(table_name, colname):
            self.logger.debug(f"列已存在: {table_name}.{colname}")
            return True
        
        try:
            sql_type = column_type.upper()
            sql = f'ALTER TABLE {table_name} ADD COLUMN "{colname}" {sql_type}'
            self.execute_sql(sql)
            self.logger.info(f"成功添加动态列: {table_name}.{colname} ({sql_type})")
            return True
        except Exception as e:
            self.logger.error(f"添加列失败 {table_name}.{colname}: {e}")
            return False
    
    def ensure_date_records(self, date_index: pd.DatetimeIndex) -> bool:
        """确保日期记录存在"""
        try:
            date_str_list = [date.strftime('%Y-%m-%d %H:%M:%S') for date in date_index]
            placeholders = ",".join([f"'{date}'" for date in date_str_list])
            
            existing_dates = self.fetch_all(f'''
                SELECT date_index FROM time_series_data 
                WHERE date_index IN ({placeholders})
            ''')
            existing_dates_set = {str(date[0]) for date in existing_dates}
            
            new_dates = [date for date in date_index 
                        if date.strftime('%Y-%m-%d %H:%M:%S') not in existing_dates_set 
                        and str(date) not in existing_dates_set]
            if new_dates:
                values = ",".join([f"('{date.strftime('%Y-%m-%d %H:%M:%S')}')" for date in new_dates])
                self.execute_sql(f'INSERT INTO time_series_data (date_index) VALUES {values}')
                self.logger.info(f"新增{len(new_dates)}个日期记录")
            
            return True
        except Exception as e:
            self.logger.error(f"日期记录处理失败: {e}")
            return False
    
    def check_existing_data(self, colname_hash: str, dates: List[datetime]) -> Dict[str, Any]:
        """检查是否存在数据冲突"""
        try:
            metadata = self.fetch_one(
                "SELECT * FROM _metacoldata WHERE colname_hash = :hash",
                {"hash": colname_hash}
            )
            
            if not metadata:
                return {'exists': False, 'conflicting_dates': []}
            
            # 检查列是否存在
            if not self.col_exists('time_series_data', colname_hash):
                return {'exists': True, 'metadata': metadata, 'conflicting_dates': [], 'conflict_count': 0}
            
            date_str_list = [date.strftime('%Y-%m-%d %H:%M:%S') for date in dates]
            placeholders = ",".join([f"'{d}'" for d in date_str_list])
            
            query = f'''
                SELECT date_index FROM time_series_data 
                WHERE date_index IN ({placeholders}) 
                AND "{colname_hash}" IS NOT NULL
            '''
            
            existing_dates = self.fetch_all(query)
            
            return {
                'exists': True,
                'metadata': metadata,
                'conflicting_dates': [row[0] for row in existing_dates],
                'conflict_count': len(existing_dates)
            }
        except Exception as e:
            if "no such column" in str(e):
                return {'exists': False, 'conflicting_dates': []}
            self.logger.warning(f"检查现有数据时出错: {e}")
            return {'exists': False, 'conflicting_dates': []}
    
    def update_metadata(self, col_info: Dict, hashed_name: str, stats: Dict, existing_info: Dict):
        """更新元数据记录"""
        if existing_info.get('exists', False):
            # 更新现有元数据
            update_parts = []
            params = {}
            stat_fields = ['invalid_count', 'total_count', 'mean', 'std', 'variance', 
                          'skewness', 'kurtosis', 'min', 'max', 'unique_count', 'unique_ratio']
            for key in stat_fields:
                if key in stats:
                    update_parts.append(f"{key} = :{key}")
                    params[key] = stats[key]
            
            update_parts.append("updated_at = :updated_at")
            params['updated_at'] = _now()
            params['colname_hash'] = hashed_name
            
            update_sql = f'''
                UPDATE _metacoldata SET {', '.join(update_parts)} 
                WHERE colname_hash = :colname_hash
            '''
            self.execute_sql(update_sql, params)
        else:
            # 插入新元数据
            params = {
                'original_colname': col_info.get('original_name', ''),
                'colname_hash': hashed_name,
                'level_0': col_info.get('level_0', ''),
                'level_1': col_info.get('level_1', ''),
                'level_2': col_info.get('level_2', ''),
                'created_at': _now(),
                'updated_at': _now(),
                'update_count': 0
            }
            
            stat_fields = ['invalid_count', 'total_count', 'mean', 'std', 'variance', 
                          'skewness', 'kurtosis', 'min', 'max', 'unique_count', 'unique_ratio',
                          'first_valid_date', 'last_valid_date', 'data_type']
            for key in stat_fields:
                if key in stats:
                    params[key] = stats[key]
            
            columns = ', '.join(params.keys())
            placeholders = ', '.join([f':{k}' for k in params.keys()])
            
            insert_sql = f'''
                INSERT INTO _metacoldata ({columns}) 
                VALUES ({placeholders})
            '''
            self.execute_sql(insert_sql, params)
    
    def insert_column_data(self, hashed_name: str, update_data: List[Dict]):
        """插入列数据"""
        if not update_data:
            return
        
        try:
            for data in update_data:
                update_sql = f'''
                    UPDATE time_series_data 
                    SET "{hashed_name}" = :value 
                    WHERE date_index = :date
                '''
                self.execute_sql(update_sql, {'value': data['value'], 'date': data['date']})
            
            self.logger.info(f"更新{len(update_data)}行数据到列{hashed_name}")
        except Exception as e:
            self.logger.error(f"插入列数据失败: {e}")
            raise


# ==================== TimescaleDB 特有操作 ====================

class TimescaleDBOperations(DatabaseOperations):
    """TimescaleDB数据库操作类"""
    
    def __init__(self, connection):
        super().__init__(connection)
    
    def create_hypertable(self, table_name: str, time_column: str = "time") -> bool:
        """创建超表"""
        try:
            sql = f"SELECT create_hypertable('{table_name}', '{time_column}', if_not_exists => TRUE);"
            self.execute_sql(sql)
            self.logger.info(f"超表创建成功: {table_name}")
            return True
        except Exception as e:
            self.logger.error(f"创建超表失败: {e}")
            return False
    
    def insert_time_series(self, table: str, data_list: List[Dict]) -> int:
        """批量插入时序数据"""
        if not data_list:
            return 0
        
        columns = list(data_list[0].keys())
        placeholders = ", ".join([f":{col}" for col in columns])
        columns_str = ", ".join(columns)
        
        sql = f"""
        INSERT INTO {table} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
        """
        
        count = 0
        for data in data_list:
            try:
                self.execute_sql(sql, data)
                count += 1
            except Exception as e:
                self.logger.warning(f"插入失败: {e}")
        
        return count
    
    def query_range(self, table: str, start_time: datetime, 
                   end_time: datetime, time_column: str = "time",
                   limit: int = 1000) -> List[Any]:
        """按时间范围查询"""
        sql = f"""
        SELECT * FROM {table}
        WHERE {time_column} BETWEEN :start_time AND :end_time
        ORDER BY {time_column} DESC
        LIMIT :limit
        """
        return self.fetch_all(sql, {
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit
        })
    
    def get_latest_records(self, table: str, time_column: str = "time",
                          limit: int = 10) -> List[Any]:
        """获取最新记录"""
        sql = f"SELECT * FROM {table} ORDER BY {time_column} DESC LIMIT :limit"
        return self.fetch_all(sql, {"limit": limit})
    
    def downsample(self, source_table: str, dest_table: str,
                   bucket: str, aggregations: Dict[str, str],
                   time_column: str = "time") -> bool:
        """数据降采样"""
        try:
            agg_parts = [f"time_bucket('{bucket}', {time_column}) as {time_column}"]
            for col, func_name in aggregations.items():
                agg_parts.append(f"{func_name}({col}) as {col}")
            
            create_sql = f"CREATE TABLE IF NOT EXISTS {dest_table} (LIKE {source_table} INCLUDING ALL);"
            self.execute_sql(create_sql)
            
            insert_sql = f"""
            INSERT INTO {dest_table} ({time_column}, {', '.join(aggregations.keys())})
            SELECT {', '.join(agg_parts)}
            FROM {source_table}
            GROUP BY time_bucket('{bucket}', {time_column})
            ON CONFLICT DO NOTHING
            """
            self.execute_sql(insert_sql)
            
            self.logger.info(f"降采样完成: {source_table} -> {dest_table}")
            return True
        except Exception as e:
            self.logger.error(f"降采样失败: {e}")
            return False
    
    def create_compression_policy(self, table_name: str, 
                                 compress_after: str = '7 days') -> bool:
        """创建压缩策略"""
        try:
            sql = f"""
            ALTER TABLE {table_name} SET (timescaledb.compress, timescaledb.compress_segmentby = 'id');
            SELECT add_compression_policy('{table_name}', INTERVAL '{compress_after}');
            """
            self.execute_sql(sql)
            return True
        except Exception as e:
            self.logger.error(f"创建压缩策略失败: {e}")
            return False
    
    def create_retention_policy(self, table_name: str, 
                                drop_after: str = '30 days') -> bool:
        """创建数据保留策略"""
        try:
            sql = f"SELECT add_retention_policy('{table_name}', INTERVAL '{drop_after}');"
            self.execute_sql(sql)
            return True
        except Exception as e:
            self.logger.error(f"创建保留策略失败: {e}")
            return False
    
    def get_chunk_stats(self, table_name: str) -> List[Any]:
        """获取分块统计"""
        sql = f"""
        SELECT chunk_name, range_start, range_end, pg_size_pretty(table_size) as size
        FROM timescaledb_information.chunks
        WHERE hypertable_name = '{table_name}'
        ORDER BY range_start DESC
        """
        return self.fetch_all(sql)
    
    def get_table_stats(self, table: str) -> Dict[str, Any]:
        """获取表统计信息"""
        try:
            sql = f"""
            SELECT 
                pg_size_pretty(pg_relation_size('{table}')) as size,
                pg_total_relation_size('{table}') as total_size,
                (SELECT COUNT(*) FROM {table}) as row_count
            """
            result = self.fetch_one(sql)
            if result:
                return {
                    "size": result[0],
                    "total_size": result[1],
                    "row_count": result[2]
                }
            return {}
        except Exception as e:
            self.logger.error(f"获取表统计失败: {e}")
            return {}
