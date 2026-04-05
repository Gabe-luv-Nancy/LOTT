# -*- coding: utf-8 -*-
"""
TimescaleDB 建表操作模块

提供两套表创建函数：

1. 旧接口（向后兼容）：
   create_all_tables() / drop_all_tables() / get_table_list()
   → 创建 ohlcv_data / data_metadata / timeseries_data（旧版三表）

2. 新接口（LOTTHOW 规范）：
   create_all_lotthow_tables() / drop_all_lotthow_tables() / get_table_list()
   → 创建 df_1min/df_5min/df_1day/ef_*/intl_*/external_data（LOTTHOW 全套表）

使用示例（新版）：
    from Data.DatabaseManage.timescale_setup import (
        create_all_lotthow_tables,
        drop_all_lotthow_tables,
        get_table_list,
    )
    result = create_all_lotthow_tables()
    tables = get_table_list()
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

try:
    import psycopg2
except ImportError:
    psycopg2 = None

from .tsdb_config import TSDB, TSDBConfig, get_tsdb_dict

logger = logging.getLogger(__name__)

# ============================================================================
# 连接工具
# ============================================================================

def _get_conn(config: Optional[Dict[str, Any]] = None) -> Optional[Any]:
    """
    获取数据库连接（内部函数）。

    优先级：传入的 config > 全局 TSDB 配置。
    """
    if psycopg2 is None:
        logger.error("psycopg2 未安装，请运行: pip install psycopg2-binary")
        return None

    params = {**get_tsdb_dict(), **(config or {})}

    try:
        conn = psycopg2.connect(
            host=params["host"],
            port=params["port"],
            database=params["database"],
            user=params["user"],
            password=params["password"],
        )
        logger.info(
            f"已连接到 TimescaleDB: "
            f"{params['host']}:{params['port']}/{params['database']}"
        )
        return conn
    except Exception as e:
        logger.error(f"连接 TimescaleDB 失败: {e}")
        return None


# ============================================================================
# 辅助函数
# ============================================================================

def _create_hypertable(
    cur: Any, table: str, time_column: str = "time",
    chunk_interval: str = "1 day"
) -> None:
    """将普通表转为 TimescaleDB 超表（幂等）"""
    cur.execute(
        f"SELECT create_hypertable('{table}', '{time_column}',"
        f"  if_not_exists => TRUE, migrate_data => TRUE,"
        f"  chunk_time_interval => INTERVAL '{chunk_interval}');"
    )


def _add_compression(cur: Any, table: str, segmentby: str = "symbol") -> None:
    """为超表添加压缩策略（30 天后自动压缩）"""
    cur.execute(
        f"ALTER TABLE {table} SET ("
        f"  timescaledb.compress,"
        f"  timescaledb.compress_segmentby = '{segmentby}');"
    )
    cur.execute(
        f"SELECT add_compression_policy("
        f"  '{table}', INTERVAL '30 days', if_not_exists => TRUE);"
    )


# ============================================================================
# 新接口：LOTTHOW 规范全套表
# ============================================================================

# ---- LOTTHOW 表清单 ----
LOTTHOW_TABLES: List[Dict[str, Any]] = [

    # ── 国内期货 df_* ──────────────────────────────────────
    {
        "name": "df_1min",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.df_1min (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                open_interest   DOUBLE PRECISION,
                settle          DOUBLE PRECISION,
                pre_close       DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                category        TEXT,
                underlying      TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 day",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_df_1min_symbol ON public.df_1min (symbol, exchange, time DESC);",
        ],
    },
    {
        "name": "df_5min",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.df_5min (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                open_interest   DOUBLE PRECISION,
                settle          DOUBLE PRECISION,
                pre_close       DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                category        TEXT,
                underlying      TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 day",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_df_5min_symbol ON public.df_5min (symbol, exchange, time DESC);",
        ],
    },
    {
        "name": "df_1day",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.df_1day (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                open_interest   DOUBLE PRECISION,
                settle          DOUBLE PRECISION,
                pre_close       DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                category        TEXT,
                underlying      TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 month",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_df_1day_symbol ON public.df_1day (symbol, exchange, time DESC);",
        ],
    },

    # ── 国内 ETF ef_* ──────────────────────────────────────
    {
        "name": "ef_1min",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.ef_1min (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                net_nav         DOUBLE PRECISION,
                discount_rate   DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                category        TEXT,
                跟踪指数         TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 day",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ef_1min_symbol ON public.ef_1min (symbol, exchange, time DESC);",
        ],
    },
    {
        "name": "ef_5min",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.ef_5min (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                net_nav         DOUBLE PRECISION,
                discount_rate   DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                category        TEXT,
                跟踪指数         TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 day",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ef_5min_symbol ON public.ef_5min (symbol, exchange, time DESC);",
        ],
    },
    {
        "name": "ef_1day",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.ef_1day (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                net_nav         DOUBLE PRECISION,
                discount_rate   DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                category        TEXT,
                跟踪指数         TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 month",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ef_1day_symbol ON public.ef_1day (symbol, exchange, time DESC);",
        ],
    },

    # ── 国际期货 intl_futures_* ──────────────────────────────
    {
        "name": "intl_futures_1min",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.intl_futures_1min (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                open_interest   DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                currency        TEXT,
                unit            TEXT,
                category        TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 day",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_if_1min ON public.intl_futures_1min (symbol, exchange, time DESC);",
        ],
    },
    {
        "name": "intl_futures_5min",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.intl_futures_5min (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                open_interest   DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                currency        TEXT,
                unit            TEXT,
                category        TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 day",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_if_5min ON public.intl_futures_5min (symbol, exchange, time DESC);",
        ],
    },
    {
        "name": "intl_futures_1day",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.intl_futures_1day (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                open_interest   DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                currency        TEXT,
                unit            TEXT,
                category        TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 month",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_if_1day ON public.intl_futures_1day (symbol, exchange, time DESC);",
        ],
    },

    # ── 国际 ETF intl_etf_* ─────────────────────────────────
    {
        "name": "intl_etf_1min",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.intl_etf_1min (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                currency        TEXT,
                category        TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 day",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ie_1min ON public.intl_etf_1min (symbol, exchange, time DESC);",
        ],
    },
    {
        "name": "intl_etf_1day",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.intl_etf_1day (
                time            TIMESTAMPTZ NOT NULL,
                symbol          TEXT        NOT NULL,
                exchange        TEXT        NOT NULL,
                open_           DOUBLE PRECISION,
                high            DOUBLE PRECISION,
                low             DOUBLE PRECISION,
                close_          DOUBLE PRECISION,
                volume          DOUBLE PRECISION,
                turnover        DOUBLE PRECISION,
                is_main         BOOLEAN     NOT NULL DEFAULT FALSE,
                currency        TEXT,
                category        TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 month",
        "segmentby":  "symbol",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ie_1day ON public.intl_etf_1day (symbol, exchange, time DESC);",
        ],
    },

    # ── 外部数据 external_data（宽表，indicator_name 区分指标）────
    {
        "name": "external_data",
        "sql": """
            CREATE TABLE IF NOT EXISTS public.external_data (
                time            TIMESTAMPTZ NOT NULL,
                source          TEXT        NOT NULL,
                indicator_name  TEXT        NOT NULL,
                indicator_value DOUBLE PRECISION,
                freq            TEXT        NOT NULL,
                region          TEXT,
                unit            TEXT,
                symbol          TEXT,
                category        TEXT,
                remark          TEXT,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (source, indicator_name, freq, time)
            );
        """,
        "time_col":   "time",
        "chunk":      "1 month",
        "segmentby":  "indicator_name",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_ed_source ON public.external_data (source, time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ed_freq ON public.external_data (freq, time DESC);",
            "CREATE INDEX IF NOT EXISTS idx_ed_region ON public.external_data (region, time DESC);",
        ],
    },
]


# ---- LOTTHOW 表名列表（用于批量删除） ----
LOTTHOW_TABLE_NAMES = [t["name"] for t in LOTTHOW_TABLES]


# ============================================================================
# 新接口实现
# ============================================================================

def create_all_lotthow_tables(
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    按 LOTTHOW 规范创建全套 TimescaleDB 超表。

    包含：df_1min / df_5min / df_1day（国内期货）、
          ef_1min / ef_5min / ef_1day（国内 ETF）、
          intl_futures_* / intl_etf_*（国际市场）、
          external_data（外部数据）

    Args:
        config: 可选的连接配置字典

    Returns:
        {
            "success": bool,
            "created": [表名, ...],
            "failed":  [(表名, 错误), ...],
            "message": str
        }
    """
    conn = _get_conn(config)
    if conn is None:
        return {"success": False, "message": "数据库连接失败",
                "created": [], "failed": []}

    results: Dict[str, Any] = {
        "success": True,
        "created": [],
        "failed": [],
        "message": "",
    }

    try:
        with conn.cursor() as cur:
            for tbl_def in LOTTHOW_TABLES:
                tbl_name = tbl_def["name"]
                try:
                    # 建表
                    cur.execute(tbl_def["sql"])
                    # 转为超表
                    _create_hypertable(
                        cur, tbl_def["name"],
                        tbl_def["time_col"], tbl_def["chunk"]
                    )
                    # 建索引
                    for idx_sql in tbl_def["indexes"]:
                        cur.execute(idx_sql)
                    # 添加压缩策略
                    _add_compression(cur, tbl_def["name"], tbl_def["segmentby"])

                    conn.commit()
                    results["created"].append(tbl_name)
                    logger.info(f"✓ {tbl_name} 超表创建完成")

                except Exception as e:
                    conn.rollback()
                    results["failed"].append((tbl_name, str(e)))
                    logger.error(f"✗ {tbl_name} 创建失败: {e}")

        results["success"] = len(results["failed"]) == 0
        results["message"] = (
            f"创建完成: 成功={len(results['created'])}, "
            f"失败={len(results['failed'])}"
        )
        logger.info(results["message"])

    except Exception as e:
        results["success"] = False
        results["message"] = str(e)
        logger.error(f"create_all_lotthow_tables 整体异常: {e}")
    finally:
        conn.close()

    return results


def drop_all_lotthow_tables(
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    删除 LOTTHOW 全套表（⚠️ 不可逆）。

    Args:
        config: 可选的连接配置

    Returns:
        {"success": bool, "dropped": [...], "failed": [...], "message": str}
    """
    conn = _get_conn(config)
    if conn is None:
        return {"success": False, "message": "数据库连接失败",
                "dropped": [], "failed": []}

    results: Dict[str, Any] = {
        "success": False,
        "dropped": [],
        "failed": [],
        "message": "",
    }

    try:
        with conn.cursor() as cur:
            # 终止活跃连接
            cur.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state = 'active'
                  AND pid <> pg_backend_pid();
            """)
            # 删除表
            for tbl in LOTTHOW_TABLE_NAMES:
                try:
                    cur.execute(f"DROP TABLE IF EXISTS public.{tbl} CASCADE;")
                    results["dropped"].append(tbl)
                    logger.info(f"✓ 已删除: public.{tbl}")
                except Exception as e:
                    results["failed"].append((tbl, str(e)))
                    logger.warning(f"✗ 删除 {tbl} 失败: {e}")

        conn.commit()
        results["success"] = len(results["failed"]) == 0
        results["message"] = (
            f"删除完成: dropped={results['dropped']}, failed={results['failed']}"
        )

    except Exception as e:
        conn.rollback()
        results["message"] = str(e)
        logger.error(f"drop_all_lotthow_tables 异常: {e}")
    finally:
        conn.close()

    return results


# ============================================================================
# 旧接口（向后兼容）
# ============================================================================

def create_all_tables(
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    创建旧版三表（ohlcv_data / data_metadata / timeseries_data）。
    新项目请使用 create_all_lotthow_tables()。
    """
    conn = _get_conn(config)
    if conn is None:
        return {"success": False, "message": "数据库连接失败"}

    results: Dict[str, Any] = {
        "success": False,
        "ohlcv_data": False,
        "data_metadata": False,
        "timeseries_data": False,
        "message": "",
    }

    try:
        with conn.cursor() as cur:
            # ohlcv_data
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.ohlcv_data (
                    id          BIGSERIAL,
                    symbol      TEXT        NOT NULL,
                    exchange    TEXT        NOT NULL,
                    timeframe   TEXT        NOT NULL,
                    time        TIMESTAMPTZ NOT NULL,
                    open_       DOUBLE PRECISION NOT NULL,
                    high        DOUBLE PRECISION NOT NULL,
                    low         DOUBLE PRECISION NOT NULL,
                    close_      DOUBLE PRECISION NOT NULL,
                    volume      DOUBLE PRECISION NOT NULL,
                    settle      DOUBLE PRECISION,
                    turnover    DOUBLE PRECISION DEFAULT 0,
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (symbol, exchange, timeframe, time)
                );
            """)
            _create_hypertable(cur, "public.ohlcv_data", "time", "1 day")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_tf "
                "ON public.ohlcv_data (symbol, timeframe, time DESC);"
            )
            results["ohlcv_data"] = True

            # data_metadata
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.data_metadata (
                    id          SERIAL PRIMARY KEY,
                    data_hash   TEXT NOT NULL UNIQUE,
                    source_file TEXT,
                    source_type TEXT DEFAULT 'json',
                    level1 TEXT, level2 TEXT, level3 TEXT, level4 TEXT,
                    timeframe   TEXT NOT NULL,
                    start_time  TIMESTAMPTZ,
                    end_time    TIMESTAMPTZ,
                    row_count   BIGINT DEFAULT 0,
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    updated_at  TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            _create_hypertable(
                cur, "public.data_metadata", "created_at", "30 days"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_metadata_hash "
                "ON public.data_metadata (data_hash);"
            )
            results["data_metadata"] = True

            # timeseries_data
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.timeseries_data (
                    id          BIGSERIAL,
                    metadata_id INTEGER
                        REFERENCES public.data_metadata(id) ON DELETE CASCADE,
                    symbol      TEXT NOT NULL,
                    exchange    TEXT,
                    timeframe   TEXT NOT NULL,
                    time        TIMESTAMPTZ NOT NULL,
                    value       DOUBLE PRECISION,
                    value_type  TEXT,
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    PRIMARY KEY (symbol, exchange, timeframe, time)
                );
            """)
            _create_hypertable(cur, "public.timeseries_data", "time", "1 day")
            results["timeseries_data"] = True

        conn.commit()
        results["success"] = True
        results["message"] = (
            f"旧版三表创建成功: "
            f"ohlcv_data={results['ohlcv_data']}, "
            f"data_metadata={results['data_metadata']}, "
            f"timeseries_data={results['timeseries_data']}"
        )
        logger.info(results["message"])

    except Exception as e:
        conn.rollback()
        results["message"] = f"创建超表时出错: {e}"
        logger.error(results["message"])
    finally:
        conn.close()

    return results


def drop_all_tables(
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    删除旧版三表（ohlcv_data / data_metadata / timeseries_data）。
    """
    conn = _get_conn(config)
    if conn is None:
        return {"success": False, "message": "数据库连接失败"}

    tables = ["ohlcv_data", "data_metadata", "timeseries_data"]
    results: Dict[str, Any] = {
        "success": False, "dropped": [], "failed": [], "message": ""
    }

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND state = 'active'
                  AND pid <> pg_backend_pid();
            """)
            for tbl in tables:
                try:
                    cur.execute(f"DROP TABLE IF EXISTS public.{tbl} CASCADE;")
                    results["dropped"].append(tbl)
                except Exception as e:
                    results["failed"].append((tbl, str(e)))
        conn.commit()
        results["success"] = len(results["failed"]) == 0
        results["message"] = (
            f"删除完成: dropped={results['dropped']}, failed={results['failed']}"
        )
    except Exception as e:
        conn.rollback()
        results["message"] = str(e)
    finally:
        conn.close()

    return results


# ============================================================================
# 表列表查询（兼容新旧两套表）
# ============================================================================

def get_table_list(
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    返回当前数据库中所有表的信息。

    Returns:
        [{
            "schema": str,
            "name": str,
            "type": str,
            "row_count": int,
            "is_hypertable": bool,
            "is_continuous_aggregate": bool,
        }, ...]
    """
    conn = _get_conn(config)
    if conn is None:
        return []

    tables: List[Dict[str, Any]] = []

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    t.table_schema  AS schema,
                    t.table_name    AS name,
                    t.table_type    AS type,
                    COALESCE(c.reltuples, 0)::bigint AS row_count
                FROM information_schema.tables t
                LEFT JOIN pg_class c
                    ON c.relname = t.table_name
                    AND c.relnamespace = (
                        SELECT oid FROM pg_namespace
                        WHERE nspname = t.table_schema
                    )
                WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
                  AND t.table_type IN ('BASE TABLE', 'VIEW')
                ORDER BY t.table_schema, t.table_name;
            """)
            rows = cur.fetchall()

            # 超表检测
            cur.execute(
                "SELECT hypertable_name FROM timescaledb_information.hypertables;"
            )
            hypertable_names = {r[0] for r in cur.fetchall()}

            # 连续聚合检测
            cur.execute(
                "SELECT view_name FROM timescaledb_information.continuous_aggregates;"
            )
            caggs_names = {r[0] for r in cur.fetchall()}

            for (schema, name, type_, row_count) in rows:
                tables.append({
                    "schema": schema,
                    "name": name,
                    "type": type_,
                    "row_count": row_count,
                    "is_hypertable": name in hypertable_names,
                    "is_continuous_aggregate": name in caggs_names,
                })

    except Exception as e:
        logger.error(f"获取表列表失败: {e}")
    finally:
        conn.close()

    return tables


# ============================================================================
# TSDBConfig 便捷入口（从 tsdb_config 导入，字段名自动对齐）
# ============================================================================

def create_all_lotthow_tables_from_config(
    ts_config: TSDBConfig
) -> Dict[str, Any]:
    """使用 TSDBConfig 创建 LOTTHOW 全套表"""
    return create_all_lotthow_tables({
        "host":     ts_config.host,
        "port":     ts_config.port,
        "database": ts_config.database,
        "user":     ts_config.user,
        "password": ts_config.password,
    })


def drop_all_lotthow_tables_from_config(
    ts_config: TSDBConfig
) -> Dict[str, Any]:
    """使用 TSDBConfig 删除 LOTTHOW 全套表"""
    return drop_all_lotthow_tables({
        "host":     ts_config.host,
        "port":     ts_config.port,
        "database": ts_config.database,
        "user":     ts_config.user,
        "password": ts_config.password,
    })


def create_all_tables_from_config(
    ts_config: TSDBConfig
) -> Dict[str, Any]:
    """使用 TSDBConfig 创建旧版三表（向后兼容）"""
    return create_all_tables({
        "host":     ts_config.host,
        "port":     ts_config.port,
        "database": ts_config.database,
        "user":     ts_config.user,
        "password": ts_config.password,
    })


def drop_all_tables_from_config(
    ts_config: TSDBConfig
) -> Dict[str, Any]:
    """使用 TSDBConfig 删除旧版三表"""
    return drop_all_tables({
        "host":     ts_config.host,
        "port":     ts_config.port,
        "database": ts_config.database,
        "user":     ts_config.user,
        "password": ts_config.password,
    })


def get_table_list_from_config(
    ts_config: TSDBConfig
) -> List[Dict[str, Any]]:
    """使用 TSDBConfig 获取表列表"""
    return get_table_list({
        "host":     ts_config.host,
        "port":     ts_config.port,
        "database": ts_config.database,
        "user":     ts_config.user,
        "password": ts_config.password,
    })
