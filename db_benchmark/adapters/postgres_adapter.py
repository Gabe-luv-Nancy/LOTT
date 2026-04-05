"""
PostgreSQL 适配器
优化：BRIN索引（时间序列专用，省空间速度快）
     + TimescaleDB hypertables（如插件可用）
"""

from typing import Optional
import pandas as pd
from psycopg2 import sql, extras

from .base import BaseAdapter
from .base import register_adapter

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None


@register_adapter("postgresql")
class PostgreSQLAdapter(BaseAdapter):
    DB_NAME = "postgresql"

    def __init__(self, host="localhost", port=5432, database="lott",
                 user="postgres", password="", **kwargs):
        if psycopg2 is None:
            raise ImportError("psycopg2 not installed: pip install psycopg2-binary")
        super().__init__(host=host, port=port, database=database, user=user, password=password, **kwargs)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self._conn = None
        self._has_timescale = False

    def connect(self):
        self._conn = psycopg2.connect(
            host=self.host, port=self.port, database=self.database,
            user=self.user, password=self.password,
        )
        self._conn.autocommit = False
        self._connected = True
        # 检查 TimescaleDB
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT 1 FROM pg_extension WHERE extname='timescaledb'")
            self._has_timescale = cur.fetchone() is not None
            cur.close()
        except Exception:
            self._has_timescale = False

    def disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._connected = False

    # ====== Schema ======

    def create_schema(self):
        cur = self._conn.cursor()
        if self._has_timescale:
            # TimescaleDB 超表：自动按时间分片，BRIN 索引加速时间查询
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
            cur.execute("SELECT create_hypertable('futures_ohlcv', 'datetime', if_not_exists=>TRUE)")
            # TimescaleDB 自动创建时间分区的 BRIN 索引
            cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol ON futures_ohlcv (symbol)")
        else:
            # 纯 PostgreSQL：手动分表 + BRIN 索引
            cur.execute("""
                CREATE TABLE IF NOT EXISTS futures_ohlcv (
                    id          BIGSERIAL PRIMARY KEY,
                    symbol      VARCHAR(32)  NOT NULL,
                    exchange    VARCHAR(16)  NOT NULL DEFAULT '',
                    datetime    TIMESTAMPTZ  NOT NULL,
                    open        NUMERIC(12,4) NOT NULL,
                    high        NUMERIC(12,4) NOT NULL,
                    low         NUMERIC(12,4) NOT NULL,
                    close       NUMERIC(12,4) NOT NULL,
                    volume      BIGINT        NOT NULL DEFAULT 0,
                    hold        BIGINT        NOT NULL DEFAULT 0
                )
            """)
            # BRIN 索引：专为时间序列设计，比 B-tree 小 100 倍，查询快 10 倍
            cur.execute("CREATE INDEX IF NOT EXISTS idx_dt_brin ON futures_ohlcv USING BRIN(datetime)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_symbol_dt ON futures_ohlcv (symbol, datetime)")
        self._conn.commit()
        cur.close()

    def drop_schema(self):
        cur = self._conn.cursor()
        cur.execute("DROP TABLE IF EXISTS futures_ohlcv CASCADE")
        self._conn.commit()
        cur.close()

    # ====== 写入 ======

    def bulk_insert(self, df: pd.DataFrame) -> int:
        df = self.normalize_df(df)
        cols = ["symbol", "exchange", "datetime", "open", "high", "low", "close", "volume", "hold"]
        if "symbol" not in df.columns:
            df["symbol"] = ""
        if "exchange" not in df.columns:
            df["exchange"] = ""

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

        query = sql.SQL("INSERT INTO futures_ohlcv ({}) VALUES %s ON CONFLICT DO NOTHING").format(
            sql.SQL(", ").join(sql.Identifier(c) for c in cols)
        )
        extras.execute_values(cur := self._conn.cursor(), query.as_string(self._conn), rows, page_size=5000)
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

        df = pd.read_sql_query(sql, self._conn, params=params if params else None)
        return df

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
        # PostgreSQL 的 date_trunc 是目前最快的聚合方式
        freq_map = {"1H": "hour", "1D": "day", "1W": "week", "1min": "minute", "5min": "minute"}
        pg_freq = freq_map.get(freq, freq)

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

        sql = f"""
            SELECT {group.replace('%s', '%s')} as datetime,
                   min(open)  as open,
                   max(high)  as high,
                   min(low)   as low,
                   (array_agg(close ORDER BY datetime DESC))[1] as close,
                   sum(volume) as volume,
                   (array_agg(hold ORDER BY datetime DESC))[1] as hold
                   {', symbol' if not symbol else ''}
            FROM futures_ohlcv
            {where}
            GROUP BY {group.replace('%s', '%s')}
            ORDER BY datetime
        """
        df = pd.read_sql_query(sql, self._conn, params=[pg_freq] + (params if params else []) + [pg_freq])
        return df

    def _count_fast(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM futures_ohlcv")
        count = cur.fetchone()[0]
        cur.close()
        return count
