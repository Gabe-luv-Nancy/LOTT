# -*- coding: utf-8 -*-
"""
Data.DatabaseManage.tsdb_config — TimescaleDB 连接配置

所有 TimescaleDB 连接参数统一在这里定义，
其他地方只引用，不写明码。

用法:
    from Data.DatabaseManage.tsdb_config import TSDB, get_tsdb_url

    # 连接字符串
    url = get_tsdb_url()              # postgresql://user:***@host:port/db
    print(TSDB.password)              # 仍然是明码，注意保护

    # psycopg2 直连
    conn = psycopg2.connect(**TSDB.as_dict())

    # SQLAlchemy
    engine = create_engine(get_tsdb_url())
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TSDBConfig:
    """
    TimescaleDB 连接配置。

    所有字段均支持环境变量覆盖：
        TSDB_HOST     → host
        TSDB_PORT     → port
        TSDB_DATABASE → database
        TSDB_USER     → user
        TSDB_PASSWORD → password
    """
    host:     str = "localhost"
    port:     int = 5432
    database: str = "lott"
    user:     str = "postgres"
    password: str = "postgres"

    def as_dict(self) -> dict:
        """转换为 psycopg2.connect() 可用的字典"""
        return {
            "host":     self.host,
            "port":     self.port,
            "database": self.database,
            "user":     self.user,
            "password": self.password,
        }

    def as_url(self) -> str:
        """生成 postgresql:// 连接 URL"""
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )

    def as_url_safe(self) -> str:
        """生成脱敏连接 URL（密码用 *** 代替）"""
        return (
            f"postgresql://{self.user}:****"
            f"@{self.host}:{self.port}/{self.database}"
        )


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default

# 全局配置实例（其他地方只引用这个）


TSDB = TSDBConfig(
    host     = _env("TSDB_HOST",     "localhost"),
    port     = _env_int("TSDB_PORT", 5432),
    database = _env("TSDB_DATABASE", "lott"),
    user     = _env("TSDB_USER",     "postgres"),
    password = _env("TSDB_PASSWORD", "postgres"),
)


def get_tsdb_url() -> str:
    """获取 TSDB 连接 URL"""
    return TSDB.as_url()


def get_tsdb_url_safe() -> str:
    """获取脱敏 TSDB 连接 URL（打印用）"""
    return TSDB.as_url_safe()


def get_tsdb_dict() -> dict:
    """获取 psycopg2 直连参数字典"""
    return TSDB.as_dict()
