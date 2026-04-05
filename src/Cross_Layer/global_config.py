# -*- coding: utf-8 -*-
"""
Cross_Layer.global_config — LOTT 全局配置模块

用法（每个 notebook 第一步）：
    import sys; sys.path.insert(0,"X:/LOTT/src/"); 
    from Cross_Layer.global_config import setup_paths
    setup_paths()

    # 之后随意 import all
    from Cross_Layer import *
    from Data import *

所有大写常量可被任何模块直接引用：
    from Cross_Layer.global_config import ROOT_DIR, TSDB_HOST, JSON_DIR
"""

from __future__ import annotations
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List

# ============================================================================
# 一、项目路径（Path 对象，Windows / Linux 自动兼容）
# ============================================================================

ROOT_DIR      = Path(r"X:\LOTT").resolve()          # 项目根目录
SRC_DIR       = ROOT_DIR / "src"                     # 源码目录

CROSS_LAYER_DIR     = SRC_DIR / "Cross_Layer"
DATA_DIR            = SRC_DIR / "Data"
BACKTEST_DIR        = SRC_DIR / "Backtest"
SERVICE_DIR         = SRC_DIR / "Service"
FRONTEND_DIR        = SRC_DIR / "Frontend"

DATASOURCE_DIR      = DATA_DIR / "DataSource"
DATAMANAGE_DIR      = DATA_DIR / "DataManage"
DATABASEMANAGE_DIR  = DATA_DIR / "DatabaseManage"
DATAFEED_DIR        = DATA_DIR / "DataFeed"
TSDB_DIR            = DATAFEED_DIR / "TimescaleDB"

JSON_DIR            = DATASOURCE_DIR / "_json"
XL_DIR              = DATASOURCE_DIR / "_xl"
RAW_DIR             = DATASOURCE_DIR / "raw"
PROCESSED_DIR       = DATASOURCE_DIR / "processed"
DB_DIR              = DATASOURCE_DIR / "_db"

STRATEGY_DIR        = BACKTEST_DIR / "Strategy"
RESULTS_DIR         = BACKTEST_DIR / "results"

NOTEBOOKS_DIR       = ROOT_DIR / "notebooks"

# ============================================================================
# 二、TimescaleDB 数据库配置（环境变量优先）
# ============================================================================

TSDB_HOST     = os.getenv("TSDB_HOST",     "localhost")
TSDB_PORT     = int(os.getenv("TSDB_PORT",  "5432"))
TSDB_DATABASE = os.getenv("TSDB_DATABASE",  "lott")
TSDB_USER     = os.getenv("TSDB_USER",      "postgres")
TSDB_PASSWORD = os.getenv("TSDB_PASSWORD",  "postgres")

TSDB_URL = (
    f"postgresql://{TSDB_USER}:{TSDB_PASSWORD}"
    f"@{TSDB_HOST}:{TSDB_PORT}/{TSDB_DATABASE}"
)

DOCKER_IMAGE        = "timescale/timescaledb:latest-pg18"
DOCKER_CONTAINER    = "timescaledb"
DOCKER_PORT_MAPPING = "5432:5432"

# ============================================================================
# 三、数据源配置
# ============================================================================

INVALID_VALUES: List[str] = [
    "--", "-", "空", "na", "null",
    "NULL", "NaN", "nan", "None", "none", ""
]

SUPPORTED_TIMEFRAMES: List[str] = [
    "1m", "5m", "15m", "30m",
    "1h", "2h", "4h",
    "1d", "1w"
]

DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE   = "2030-12-31"

# ============================================================================
# 四、日志配置
# ============================================================================

LOG_LEVEL   = logging.INFO
LOG_FORMAT  = "%(asctime)s [%(levelname)8s] %(name)s: %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ============================================================================
# 五、公共函数
# ============================================================================

def setup_paths() -> List[str]:
    """
    将 LOTT 项目路径注册到 sys.path。

    ✅ 可重复调用，不会重复添加。
    ✅ 每次调用都把路径插到最前面，保证 LOTT 模块优先被找到。

    Returns:
        list: 本次新增到 sys.path 的路径（用于打印确认）
    """
    _TARGETS = [
        str(ROOT_DIR),   # X:\LOTT
        str(SRC_DIR),    # X:\LOTT\src
    ]

    loaded = []
    for p in _TARGETS:
        norm = os.path.normpath(p)
        if norm not in sys.path:
            sys.path.insert(0, norm)
            loaded.append(norm)

    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        datefmt=LOG_DATEFMT,
    )
    return loaded


def show_paths() -> None:
    """打印所有 LOTT 路径的加载状态（调试用）。"""
    print("=" * 60)
    print("LOTT 项目路径状态")
    print("=" * 60)
    for p in [str(ROOT_DIR), str(SRC_DIR)]:
        exists = "[OK]" if Path(p).exists() else "[MISS]"
        in_sys = "[in sys.path]" if os.path.normpath(p) in sys.path else "[not in sys.path]"
        print(f"  {exists} {in_sys}  {p}")
    print("=" * 60)


def get_logger(name: str) -> logging.Logger:
    """获取标准化的 Logger。"""
    return logging.getLogger(name)


# ============================================================================
# 六、兼容性别名
# ============================================================================

DIR_LOTT     = str(ROOT_DIR)
DIR_LOTT_SRC = str(SRC_DIR)

# ============================================================================
# 七、版本信息
# ============================================================================

__version__     = "0.2.0"
__project__     = "LOTT"
__description__ = "LOTT 量化分析平台全局配置"


if __name__ == "__main__":
    setup_paths()
    show_paths()
