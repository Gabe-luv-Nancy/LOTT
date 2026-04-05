"""
Redis Configuration - Redis 配置

仅包含 Redis 消息队列相关配置
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RedisConfig:
    """Redis 配置"""
    # 连接配置
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    
    # 键前缀 (命名空间隔离)
    key_prefix: str = "lott:"
    
    # Stream 配置
    stream_max_len: int = 10000  # Stream 最大消息数
    
    # 缓存配置
    cache_ttl_seconds: int = 300  # 缓存 TTL (5分钟)
    
    # Pub/Sub 配置
    heartbeat_interval: int = 30  # 心跳间隔 (秒)


@dataclass
class DataSourceConfig:
    """数据源配置"""
    # 数据源类型
    source_type: str = "simulator"  # simulator, ctp, simnow
    
    # SimNow 配置
    simnow_front: str = "tcp://180.168.146.187:10201"
    
    # CTP 配置
    ctp_front: Optional[str] = None
    ctp_broker: str = "9999"
    
    # 订阅配置
    symbols: List[str] = field(default_factory=lambda: [
        "IF2406", "IC2406", "IH2406", "TF2406"
    ])
    timeframes: List[str] = field(default_factory=lambda: [
        "1m", "5m", "15m", "1h", "1d"
    ])


@dataclass
class BacktestConfig:
    """回测配置"""
    # 数据源
    data_source: str = "redis"  # redis, csv, api
    
    # 缓存配置
    cache_ohlcv: bool = True  # 是否缓存 OHLCV 数据
    cache_dir: str = "~/LOTT/.cache/ohlcv"  # 缓存目录
    
    # 回测数据范围
    default_symbols: List[str] = field(default_factory=lambda: [
        "IF2406", "IC2406", "IH2406"
    ])
    default_timeframes: List[str] = field(default_factory=lambda: [
        "1m", "5m", "1h", "1d"
    ])
    default_start_date: str = "2024-01-01"
    default_end_date: str = "2024-12-31"
    
    # 数据加载优化
    preload_all: bool = False  # 预加载所有数据到内存
    batch_size: int = 10000  # 批量加载大小


@dataclass
class DataServiceConfig:
    """Data Service Layer 统一配置"""
    redis: RedisConfig = field(default_factory=RedisConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    
    # 服务配置
    service_name: str = "lott-dataservice"
    log_level: str = "INFO"


# ==================== 便捷函数 ====================

def get_default_config() -> DataServiceConfig:
    """获取默认配置"""
    return DataServiceConfig()


def get_backtest_config() -> BacktestConfig:
    """获取回测专用配置"""
    return BacktestConfig(
        data_source="redis",
        cache_ohlcv=True,
        default_symbols=["IF2406", "IC2406"],
        default_timeframes=["1m", "5m", "1h"],
        preload_all=True
    )
