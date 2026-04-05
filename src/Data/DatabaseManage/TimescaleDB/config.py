"""
TimescaleDB 配置模块

提供 TimescaleDB 数据源的配置管理
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class PoolConfig:
    """连接池配置"""
    min_connections: int = 1
    max_connections: int = 10
    timeout: int = 30


@dataclass
class TableConfig:
    """表配置"""
    name: str
    primary_key: List[str]
    time_column: str
    indexes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RetentionPolicy:
    """数据保留策略"""
    drop_after: str = "1 year"


@dataclass
class CompressionConfig:
    """压缩配置"""
    after_days: int = 30
    chunk_interval: str = "1 week"


@dataclass
class RetentionConfig:
    """保留配置"""
    enabled: bool = True
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    policies: Dict[str, RetentionPolicy] = field(default_factory=dict)


@dataclass
class ChunkConfig:
    """超表分区配置"""
    time_interval: str = "1 day"  # chunk 时间间隔
    schema_name: str = "public"   # 数据库 schema


@dataclass
class BatchConfig:
    """批量写入配置"""
    size: int = 1000
    max_wait_ms: int = 1000


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3
    backoff: int = 1


@dataclass
class WriteConfig:
    """写入配置"""
    batch: BatchConfig = field(default_factory=BatchConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)


@dataclass
class QueryConfig:
    """查询配置"""
    timeout: int = 60
    default_range: Dict[str, str] = field(default_factory=lambda: {
        "start": "2024-01-01",
        "end": "2024-12-31"
    })


@dataclass
class DockerConfig:
    """Docker 配置"""
    image: str = "timescale/timescaledb:latest-pg18"
    container_name: str = "timescaledb"
    ports: List[str] = field(default_factory=lambda: ["5432:5432"])
    environment: Dict[str, str] = field(default_factory=lambda: {
        "POSTGRES_USER": "admin",
        "POSTGRES_PASSWORD": "1211",
        "POSTGRES_DB": "timescaledb"
    })
    volumes: Dict[str, str] = field(default_factory=lambda: {
        "timescale_data": "/var/lib/postgresql/data"
    })


@dataclass
class EnvironmentConfig:
    """环境配置"""
    host: str = "localhost"
    pool: PoolConfig = field(default_factory=PoolConfig)
    debug: bool = False


@dataclass
class TimescaleDBConfig:
    """TimescaleDB 主配置"""
    # 连接配置
    host: str = "localhost"
    port: int = 5432
    database: str = "lott"
    username: str = "admin"
    password: str = "1211"
    
    # 连接池
    pool: PoolConfig = field(default_factory=PoolConfig)
    
    # 超表分区配置
    chunk: ChunkConfig = field(default_factory=ChunkConfig)
    
    # 表结构
    tables: Dict[str, TableConfig] = field(default_factory=dict)
    
    # 数据保留
    retention: RetentionConfig = field(default_factory=RetentionConfig)
    
    # 写入配置
    write: WriteConfig = field(default_factory=WriteConfig)
    
    # 查询配置
    query: QueryConfig = field(default_factory=QueryConfig)
    
    # Docker 配置
    docker: DockerConfig = field(default_factory=DockerConfig)
    
    # 环境配置
    environments: Dict[str, EnvironmentConfig] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password': self.password,
            'pool': {
                'min_connections': self.pool.min_connections,
                'max_connections': self.pool.max_connections,
                'timeout': self.pool.timeout,
            },
            'chunk': {
                'time_interval': self.chunk.time_interval,
                'schema_name': self.chunk.schema_name,
            },
            'retention': {
                'enabled': self.retention.enabled,
                'compression': {
                    'after_days': self.retention.compression.after_days,
                    'chunk_interval': self.retention.compression.chunk_interval,
                },
            },
            'write': {
                'batch': {
                    'size': self.write.batch.size,
                    'max_wait_ms': self.write.batch.max_wait_ms,
                },
                'retry': {
                    'max_attempts': self.write.retry.max_attempts,
                    'backoff': self.write.retry.backoff,
                },
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimescaleDBConfig':
        """从字典创建"""
        return cls(
            host=data.get('host', 'localhost'),
            port=data.get('port', 5432),
            database=data.get('database', 'timescaledb'),
            username=data.get('username', 'admin'),
            password=data.get('password', '1211'),
        )


def load_config(config_path: str = None) -> TimescaleDBConfig:
    """
    从 YAML 文件加载配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        TimescaleDBConfig 实例
    """
    if config_path is None:
        # 默认路径
        base_dir = Path(__file__).parent
        config_path = base_dir / "timescaledb_config.yaml"
    
    if not os.path.exists(config_path):
        return TimescaleDBConfig()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    if not data:
        return TimescaleDBConfig()
    
    # 解析配置
    config = TimescaleDBConfig()
    
    # 连接配置
    config.host = data.get('host', 'localhost')
    config.port = data.get('port', 5432)
    config.database = data.get('database', 'timescaledb')
    config.username = data.get('username', 'admin')
    config.password = data.get('password', '1211')
    
    # 连接池
    pool_data = data.get('pool', {})
    config.pool = PoolConfig(
        min_connections=pool_data.get('min_connections', 1),
        max_connections=pool_data.get('max_connections', 10),
        timeout=pool_data.get('timeout', 30)
    )
    
    # 表配置
    tables_data = data.get('tables', {})
    for table_name, table_data in tables_data.items():
        config.tables[table_name] = TableConfig(
            name=table_data.get('name', table_name),
            primary_key=table_data.get('primary_key', []),
            time_column=table_data.get('time_column', 'time'),
            indexes=table_data.get('indexes', [])
        )
    
    # 保留策略
    retention_data = data.get('retention', {})
    config.retention = RetentionConfig(
        enabled=retention_data.get('enabled', True),
        compression=CompressionConfig(
            after_days=retention_data.get('compression', {}).get('after_days', 30),
            chunk_interval=retention_data.get('compression', {}).get('chunk_interval', '1 week')
        ),
        policies={
            k: RetentionPolicy(v.get('drop_after', '1 year'))
            for k, v in retention_data.get('policies', {}).items()
        }
    )
    
    # 写入配置
    write_data = data.get('write', {})
    config.write = WriteConfig(
        batch=BatchConfig(
            size=write_data.get('batch', {}).get('size', 1000),
            max_wait_ms=write_data.get('batch', {}).get('max_wait_ms', 1000)
        ),
        retry=RetryConfig(
            max_attempts=write_data.get('retry', {}).get('max_attempts', 3),
            backoff=write_data.get('retry', {}).get('backoff', 1)
        )
    )
    
    # 查询配置
    query_data = data.get('query', {})
    config.query = QueryConfig(
        timeout=query_data.get('timeout', 60),
        default_range=query_data.get('default_range', {
            "start": "2024-01-01",
            "end": "2024-12-31"
        })
    )
    
    # Docker 配置
    docker_data = data.get('docker', {})
    config.docker = DockerConfig(
        image=docker_data.get('image', 'timescale/timescaledb:latest-pg18'),
        container_name=docker_data.get('container_name', 'timescaledb'),
        ports=docker_data.get('ports', ['5432:5432']),
        environment=docker_data.get('environment', {}),
        volumes=docker_data.get('volumes', {})
    )
    
    # 环境配置
    env_data = data.get('environments', {})
    for env_name, env_data in env_data.items():
        pool_data = env_data.get('pool', {})
        config.environments[env_name] = EnvironmentConfig(
            host=env_data.get('host', 'localhost'),
            pool=PoolConfig(
                min_connections=pool_data.get('min_connections', 1),
                max_connections=pool_data.get('max_connections', 10),
                timeout=pool_data.get('timeout', 30)
            ),
            debug=env_data.get('debug', False)
        )
    
    return config


def get_default_config() -> TimescaleDBConfig:
    """获取默认配置"""
    return TimescaleDBConfig()


# 全局配置实例
_default_config: Optional[TimescaleDBConfig] = None


def get_config() -> TimescaleDBConfig:
    """获取全局配置（单例）"""
    global _default_config
    if _default_config is None:
        _default_config = load_config()
    return _default_config


def reload_config() -> TimescaleDBConfig:
    """重新加载配置"""
    global _default_config
    _default_config = load_config()
    return _default_config
