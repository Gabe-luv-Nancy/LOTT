"""
LOTT 数据库基准测试框架
对比 SQLite / PostgreSQL / MySQL / InfluxDB + DuckDB(bonus)
"""

from .config import *  # noqa
from .adapters.base import BaseAdapter, register_adapter, ADAPTERS

__all__ = ["BaseAdapter", "register_adapter", "ADAPTERS"]
