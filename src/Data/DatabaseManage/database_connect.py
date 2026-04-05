"""
数据库连接管理模块 - DatabaseConnection + Schema
"""

import threading
import logging
import os
import time
from typing import Dict

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

from .database_tables import Base
from .database_config import DatabaseConfig


# 单例变量
_instance = None
_lock = threading.Lock()


class DatabaseConnection:
    """数据库连接管理器 - 单例模式"""

    def __new__(cls, config: DatabaseConfig = None):
        """单例模式确保只有一个连接实例"""
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = super().__new__(cls)
                    _instance._initialized = False
        return _instance
    
    def __init__(self, config: DatabaseConfig = None):
        """初始化数据库连接管理器"""
        if self._initialized:
            return
        if config is None:
            config = DatabaseConfig()
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._setup_logging()
        self._initialized = True
        self.logger.info("数据库连接管理器初始化完成")
    
    def _setup_logging(self):
        """设置日志系统"""
        logging.basicConfig(
            level=getattr(logging, self.config.log_level, 'INFO'),
            format=getattr(self.config, 'log_format', '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        )
        self.logger = logging.getLogger(__name__)
    
    def create_engine(self):
        """创建数据库引擎 - 支持SQLite和TimescaleDB"""
        if self.engine is not None:
            return self.engine
            
        try:
            if self.config.db_type in ("timescaledb", "postgresql"):
                db_url = self.config.get_postgresql_url()
                self.engine = create_engine(
                    db_url,
                    pool_size=self.config.pg_pool_size,
                    max_overflow=self.config.pg_max_overflow,
                    pool_pre_ping=True
                )
                self.logger.info(f"TimescaleDB引擎创建成功: {self.config.pg_host}:{self.config.pg_port}")
            else:
                self._ensure_sqlite_dir_exists()
                connect_args = self._get_connect_args()
                self.engine = create_engine(
                    self.config.db_url,
                    connect_args=connect_args
                )
                self.logger.info(f"SQLite引擎创建成功: {self.config.db_url}")
            
            self._apply_database_optimizations()
            return self.engine
            
        except Exception as e:
            self.logger.error(f"创建数据库引擎失败: {e}")
            raise

    def _ensure_sqlite_dir_exists(self):
        """确保SQLite数据库文件所在目录存在"""
        if 'sqlite:///' not in self.config.db_url:
            return
        db_path = self.config.db_url.replace('sqlite:///', '', 1)
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            self.logger.info(f"已创建SQLite目录: {db_dir}")
    
    def _get_connect_args(self) -> Dict:
        """获取数据库连接参数"""
        connect_args = getattr(self.config, 'connect_args', {}).copy()
        if 'sqlite' in self.config.db_url:
            connect_args.update({
                'timeout': 30,
                'check_same_thread': False,
            })
        return connect_args
    
    def _apply_database_optimizations(self):
        """应用数据库特定的性能优化"""
        if 'sqlite' in (self.config.db_url or ''):
            self._apply_sqlite_optimizations()
    
    def _apply_sqlite_optimizations(self):
        """应用SQLite性能优化"""
        optimizations = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA cache_size = -10000",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA temp_store = memory",
            "PRAGMA mmap_size = 268435456",
        ]
        try:
            with self.engine.connect() as conn:
                for pragma in optimizations:
                    try:
                        conn.execute(text(pragma))
                    except Exception as e:
                        self.logger.warning(f"SQLite优化设置失败 {pragma}: {e}")
                conn.commit()
        except Exception as e:
            self.logger.warning(f"应用SQLite优化时出错: {e}")
    
    def create_session_factory(self):
        """创建会话工厂"""
        if self.engine is None:
            self.create_engine()
        
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        self.logger.info("会话工厂创建成功")
        return self.SessionLocal
    
    def get_session(self):
        """获取数据库会话"""
        if self.SessionLocal is None:
            self.create_session_factory()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                session = self.SessionLocal()
                session.execute(text('SELECT 1'))
                return session
            except Exception as e:
                self.logger.warning(f"数据库连接测试失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    self._reconnect()
                else:
                    self.logger.error("数据库连接重试次数耗尽")
                    raise
        
        raise Exception("无法建立有效的数据库连接")
    
    def _reconnect(self):
        """重新连接数据库"""
        self.logger.info("尝试重新连接数据库...")
        try:
            if self.engine:
                self.engine.dispose()
            self.engine = None
            self.SessionLocal = None
            time.sleep(1)
            self.create_engine()
            self.create_session_factory()
            self.logger.info("数据库重新连接成功")
        except Exception as e:
            self.logger.error(f"数据库重新连接失败: {e}")
            raise
    
    def get_connection(self):
        """获取原始连接"""
        if self.engine is None:
            self.create_engine()
        return self.engine.connect()
    
    def test_connection(self) -> bool:
        """测试数据库连接是否有效"""
        try:
            with self.get_connection() as conn:
                result = conn.execute(text('SELECT 1'))
                return result.scalar() == 1
        except Exception as e:
            self.logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        global _instance
        try:
            if self.engine:
                self.engine.dispose()
                self.logger.info("数据库连接池已关闭")
            self.engine = None
            self.SessionLocal = None
            _instance = None
            self._initialized = False
        except Exception as e:
            self.logger.error(f"关闭数据库连接时出错: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ==================== 表结构管理器 ====================

class Schema:
    """表结构管理器"""
    
    def __init__(self, connection: DatabaseConnection):
        self.connection = connection
        self.logger = logging.getLogger(__name__)
        self.metadata = Base.metadata
    
    def initialize_tables(self):
        """初始化所有表"""
        try:
            if self.connection.engine is None:
                self.connection.create_engine()
            self.metadata.create_all(self.connection.engine)
            self.logger.info("数据库表结构创建完成")
            return True
        except Exception as e:
            self.logger.error(f"表结构初始化失败: {e}")
            return False
    
    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        inspector = inspect(self.connection.engine)
        return table_name in inspector.get_table_names()
    
    def column_exists(self, table_name: str, colname: str) -> bool:
        """检查列是否存在"""
        inspector = inspect(self.connection.engine)
        columns = inspector.get_columns(table_name)
        return any(col['name'] == colname for col in columns)
    
    def add_dynamic_column(self, table_name: str, colname: str, 
                          column_type: str = "REAL") -> bool:
        """动态添加列到表"""
        if self.column_exists(table_name, colname):
            self.logger.debug(f"列已存在: {table_name}.{colname}")
            return True
        
        try:
            sql_type = column_type.upper()
            alter_sql = text(f'ALTER TABLE {table_name} ADD COLUMN "{colname}" {sql_type}')
            
            session = self.connection.get_session()
            session.execute(alter_sql)
            session.commit()
            session.close()
            
            self.logger.info(f"成功添加动态列: {table_name}.{colname} ({sql_type})")
            return True
        except Exception as e:
            self.logger.error(f"添加列失败 {table_name}.{colname}: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> Dict:
        """获取表信息"""
        inspector = inspect(self.connection.engine)
        return {
            "table_name": table_name,
            "columns": inspector.get_columns(table_name),
            "indexes": inspector.get_indexes(table_name),
            "primary_keys": inspector.get_pk_constraint(table_name),
        }
