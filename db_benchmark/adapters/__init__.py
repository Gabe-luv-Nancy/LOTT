from .base import BaseAdapter, register_adapter, ADAPTERS, BenchmarkResult, BenchmarkReport


def get_adapter(name: str, **kwargs) -> BaseAdapter:
    """获取数据库适配器实例（ADAPTERS 在适配器模块导入后会被填充）"""
    if name not in ADAPTERS:
        raise ValueError(f"Unknown adapter: {name}. Available: {list(ADAPTERS.keys())}")
    return ADAPTERS[name](**kwargs)


from .timescaledb_adapter import TimescaleDBAdapter
from .sqlite_adapter import SQLiteAdapter
from .duckdb_adapter import DuckDBAdapter
from .postgres_adapter import PostgreSQLAdapter
from .mysql_adapter import MySQLAdapter
from .influxdb_adapter import InfluxDBAdapter

__all__ = [
    "BaseAdapter", "register_adapter", "ADAPTERS", "get_adapter",
    "BenchmarkResult", "BenchmarkReport",
    "SQLiteAdapter", "DuckDBAdapter", "PostgreSQLAdapter",
    "MySQLAdapter", "InfluxDBAdapter", "TimescaleDBAdapter",
]
