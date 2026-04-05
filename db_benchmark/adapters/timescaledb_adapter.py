"""
TimescaleDB 适配器
基于 PostgreSQL + TimescaleDB 扩展
Hypertable 自动按月分区，BRIN 索引加速时间查询
Continuous Aggregate 预计算聚合，查询秒回
"""

from typing import Optional
import os

import pandas as pd

from .base import BaseAdapter, register_adapter

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None


@register_adapter("timescaledb")
class TimescaleDBAdapter(BaseAdapter):
    DB_NAME = "timescaledb"
    SUPPORTS_BULK_INSERT = True
    SUPPORTS_UPSERT = True

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
        **kwargs,
    ):
        if psycopg2 is None:
            raise ImportError("psycopg2 not installed: pip install psycopg2-binary")

        # 从环境变量读取（兼容 docker-compose）
        self.host = host or os.getenv("PG_HOST", "localhost")
        self.port = port or int(os.getenv("PG_PORT", "5432"))
        self.database = database or os.getenv("PG_DB", "lott")
        self.user = user or os.getenv("PG_USER", "postgres")
        self.password = password or os.getenv("PG_PASSWORD", "")
        self._conn = None
        self._has_timescaledb = False

    def connect(self):
        self._conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
        )
        self._conn.autocommit = False

        # 检查 TimescaleDB 扩展是否安装
        try:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT 1 FROM pg_extension WHERE extname='timescaledb'"
            )
            self._has_timescaledb = cur.fetchone() is not None
            cur.close()
        except Exception:
            self._has_timescaledb = False

    def disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    # ====== Schema ======

    def create_schema(self):
        cur = self._conn.cursor()

        # 创建基础表
        cur.execute("""
            CREATE TABLE IF NOT EXISTS futures_ohlcv (
                id          BIGSERIAL,
                symbol      VARCHAR(32)  NOT NULL,
                exchange    VARCHAR(16)  NOT NULL DEFAULT '',
                datetime    TIMESTAMPTZ  NOT NULL,
                open        NUMERIC(12,4) NOT NULL,
                high        NUMERIC(12,4) NOT NULL,
                low         NUMERIC(12,4) NOT NULL,
                close       NUMERIC(12,4) NOT NULL,
                volume      BIGINT        NOT NULL DEFAULT 0,
                hold        BIGINT        NOT NULL DEFAULT 0,
                PRIMARY KEY (id, datetime)
            )
        """)

        if self._has_timescaledb:
            # 转为 Hypertable（TimescaleDB 核心）
            # chunk_time_interval: 按月分区（约 30 天）
            cur.execute("""
                SELECT create_hypertable(
                    'futures_ohlcv',
                    'datetime',
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '30 days'
                )
            """)
            # 自动创建时间分区索引
            print("[TimescaleDB] Hypertable created, partitioning by 30 days")
        else:
            # 纯 PostgreSQL：手动 BRIN 索引
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_dt_brin "
                "ON futures_ohlcv USING BRIN(datetime)"
            )
            print("[PostgreSQL] BRIN index created (TimescaleDB not installed)")

        # 品种符号索引
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_symbol_dt "
            "ON futures_ohlcv (symbol, datetime)"
        )

        self._conn.commit()
        cur.close()

    def drop_schema(self):
        cur = self._conn.cursor()
        # CASCADE 自动删除 Hypertable 的所有 chunks
        cur.execute("DROP TABLE IF EXISTS futures_ohlcv CASCADE")
        self._conn.commit()
        cur.close()

    # ====== 写入 ======

    def bulk_insert(self, df: pd.DataFrame) -> int:
        df = self.normalize_df(df)
        if "symbol" not in df.columns:
            df["symbol"] = ""
        if "exchange" not in df.columns:
            df["exchange"] = ""

        cols = ["symbol", "exchange", "datetime", "open", "high", "low", "close", "volume", "hold"]
        rows = [
            (
                str(r.get("symbol", "")),
                str(r.get("exchange", "")),
                pd.Timestamp(r["datetime"]).tz_localize("UTC"),
                float(r["open"]),
                float(r["high"]),
                float(r["low"]),
                float(r["close"]),
                int(r["volume"]),
                int(r.get("hold", 0)),
            )
            for _, r in df.iterrows()
        ]

        query = """
            INSERT INTO futures_ohlcv (symbol, exchange, datetime, open, high, low, close, volume, hold)
            VALUES %s
            ON CONFLICT (id, datetime) DO NOTHING
        """
        cur = self._conn.cursor()
        execute_values(cur, query, rows, page_size=5000)
        self._conn.commit()
        cur.close()
        return len(rows)

    # ====== 查询 ======

    def query_range(
        self,
        symbol: Optional[str] = None,
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        cond, params = [], []
        if symbol:
            cond.append("symbol = %s")
            params.append(symbol)
        if start_dt:
            cond.append("datetime >= %s")
            params.append(start_dt)
        if end_dt:
            cond.append("datetime <= %s")
            params.append(end_dt)

        where = ("WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT * FROM futures_ohlcv {where} ORDER BY datetime"
        if limit:
            sql += f" LIMIT {limit}"

        return pd.read_sql_query(sql, self._conn, params=params if params else None)

    def query_latest(self, symbol: str, n: int = 1) -> pd.DataFrame:
        return pd.read_sql_query(
            "SELECT * FROM futures_ohlcv WHERE symbol = %s ORDER BY datetime DESC LIMIT %s",
            self._conn, params=(symbol, n)
        )

    def query_aggregate(
        self,
        symbol: Optional[str] = None,
        freq: str = "1H",
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
    ) -> pd.DataFrame:
        freq_map = {
            "1min": "minute", "5min": "minute", "15min": "minute",
            "30min": "minute", "1H": "hour", "1D": "day",
        }
        pg_freq = freq_map.get(freq, "hour")

        cond, params = [], []
        if symbol:
            cond.append("symbol = %s")
            params.append(symbol)
        if start_dt:
            cond.append("datetime >= %s")
            params.append(start_dt)
        if end_dt:
            cond.append("datetime <= %s")
            params.append(end_dt)

        where = ("WHERE " + " AND ".join(cond)) if cond else ""
        group = "symbol, date_trunc(%s, datetime)" if symbol else "date_trunc(%s, datetime)"

        # 聚合 OHLCV：开盘价取第一个、收盘价取最后一个、最高最低取极值
        sql = f"""
            SELECT
                date_trunc(%s, datetime) as datetime,
                min(open)  as open,
                max(high)  as high,
                min(low)   as low,
                (SELECT close FROM futures_ohlcv t2
                 WHERE date_trunc(%s, t2.datetime) = date_trunc(%s, t1.datetime)
                   {('AND t2.symbol = t1.symbol' if not symbol else '')}
                 ORDER BY t2.datetime DESC LIMIT 1) as close,
                sum(volume) as volume,
                (SELECT hold FROM futures_ohlcv t2
                 WHERE date_trunc(%s, t2.datetime) = date_trunc(%s, t1.datetime)
                   {('AND t2.symbol = t1.symbol' if not symbol else '')}
                 ORDER BY t2.datetime DESC LIMIT 1) as hold
                {', symbol' if not symbol else ''}
            FROM futures_ohlcv t1
            {where}
            GROUP BY {group.replace('%s', '%s')}
            ORDER BY datetime
        """
        # 简化：用 FIRST/LAST（TimescaleDB/PG 扩展支持）
        sql = f"""
            SELECT
                date_trunc(%s, datetime) as datetime,
                min(open)  as open,
                max(high)  as high,
                min(low)   as low,
                last(close, datetime) as close,
                sum(volume) as volume,
                last(hold, datetime)  as hold
                {', symbol' if not symbol else ''}
            FROM futures_ohlcv
            {where}
            GROUP BY {f'symbol, date_trunc(%s, datetime)' if not symbol else 'date_trunc(%s, datetime)'}
            ORDER BY datetime
        """
        # 构建参数字符串
        all_params = [pg_freq]
        if not symbol:
            all_params.append(pg_freq)
        all_params.extend(params if params else [])

        return pd.read_sql_query(sql, self._conn, params=all_params)

    def _count_fast(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM futures_ohlcv")
        count = cur.fetchone()[0]
        cur.close()
        return count

    # ====== TimescaleDB 专属功能 ======

    def create_continuous_aggregate(
        self,
        name: str,
        freq: str = "1H",
        symbol: Optional[str] = None,
    ):
        """
        创建连续聚合（后台定时物化视图）
        查询性能提升 10-100 倍（不需要每次扫描原始数据）

        示例：创建 1H 聚合视图
          adapter.create_continuous_aggregate("ohlcv_1h", freq="1H")
        """
        if not self._has_timescaledb:
            print("[WARN] TimescaleDB extension not installed, skipping continuous aggregate")
            return

        cond = ""
        if symbol:
            cond = f"WHERE symbol = '{symbol}'"

        sql = f"""
            CALL add_continuous_aggregate_policy('{name}_ca',
                start_offset => INTERVAL '3 hours',
                end_offset   => INTERVAL '1 hour',
                schedule_interval => INTERVAL '1 hour'
            )
        """
        # 先创建物化视图
        view_sql = f"""
            CREATE MATERIALIZED VIEW IF NOT EXISTS {name}_ca
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('{freq}', datetime) as datetime,
                symbol,
                first(open, datetime)  as open,
                max(high)              as high,
                min(low)               as low,
                last(close, datetime)  as close,
                sum(volume)::bigint    as volume,
                last(hold, datetime)   as hold
            FROM futures_ohlcv
            {cond}
            GROUP BY time_bucket('{freq}', datetime), symbol
        """
        cur = self._conn.cursor()
        try:
            cur.execute(view_sql)
            self._conn.commit()
            print(f"[TimescaleDB] Continuous aggregate '{name}_ca' created")
        except Exception as e:
            self._conn.rollback()
            print(f"[TimescaleDB] Continuous aggregate may already exist: {e}")
        cur.close()
