"""
DuckDB 适配器 (Bonus - 分析型数据库，比 SQLite 快 10-100 倍)
优势：列式存储、向量执行、超快分析查询
"""

import duckdb
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from .base import BaseAdapter
from .base import register_adapter


@register_adapter("duckdb")
class DuckDBAdapter(BaseAdapter):
    DB_NAME = "duckdb"

    def __init__(self, path: str = ":memory:", **kwargs):
        super().__init__(path=path, **kwargs)
        self.path = path
        self._conn: Optional[duckdb.DuckDBPyConnection] = None

    def connect(self):
        if self._conn:
            return
        self._conn = duckdb.connect(self.path, read_only=False)
        self._conn.execute("PRAGMA threads=8")
        self._conn.execute("PRAGMA memory_limit='8GB'")
        self._connected = True

    def disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._connected = False

    # ====== Schema ======

    def create_schema(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS futures_ohlcv (
                symbol      VARCHAR NOT NULL,
                exchange    VARCHAR NOT NULL DEFAULT '',
                datetime    TIMESTAMP NOT NULL,
                open        DOUBLE NOT NULL,
                high        DOUBLE NOT NULL,
                low         DOUBLE NOT NULL,
                close       DOUBLE NOT NULL,
                volume      BIGINT NOT NULL DEFAULT 0,
                hold        BIGINT NOT NULL DEFAULT 0
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_dt
            ON futures_ohlcv(datetime)
        """)

    def drop_schema(self):
        self._conn.execute("DROP TABLE IF EXISTS futures_ohlcv")
        self._conn.execute("DROP SEQUENCE IF EXISTS futures_ohlcv_id_seq")

    # ====== 写入 ======

    def bulk_insert(self, df: pd.DataFrame) -> int:
        df = self.normalize_df(df.copy())
        df["datetime"] = pd.to_datetime(df["datetime"])
        # 填充默认列
        for col, val in [("symbol", ""), ("exchange", ""), ("hold", 0)]:
            if col not in df.columns:
                df[col] = val
        # 按表结构顺序排列
        cols = ["symbol", "exchange", "datetime", "open", "high", "low", "close", "volume", "hold"]
        df = df[cols]
        self._conn.execute("DELETE FROM futures_ohlcv WHERE 1=0")  # 确保连接正常
        self._conn.append("futures_ohlcv", df)
        self._conn.commit()
        return len(df)

    # ====== 查询 ======

    def query_range(
        self,
        symbol: Optional[str] = None,
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        cond = []
        if symbol:
            cond.append(f"symbol = '{symbol}'")
        if start_dt:
            cond.append(f"datetime >= '{start_dt}'")
        if end_dt:
            cond.append(f"datetime <= '{end_dt}'")

        where = ("WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT * FROM futures_ohlcv {where} ORDER BY datetime"
        if limit:
            sql += f" LIMIT {limit}"

        df = self._conn.sql(sql).df()
        return df

    def query_latest(self, symbol: str, n: int = 1) -> pd.DataFrame:
        df = self._conn.sql(
            f"SELECT * FROM futures_ohlcv WHERE symbol = '{symbol}' ORDER BY datetime DESC LIMIT {n}"
        ).df()
        return df

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
        duck_freq = freq_map.get(freq, freq)

        cond = []
        if symbol:
            cond.append(f"symbol = '{symbol}'")
        if start_dt:
            cond.append(f"datetime >= '{start_dt}'")
        if end_dt:
            cond.append(f"datetime <= '{end_dt}'")

        where = ("WHERE " + " AND ".join(cond)) if cond else ""

        # 使用窗口函数获取每组的最后一条记录
        sql = f"""
            WITH grouped AS (
                SELECT *,
                    date_trunc('{duck_freq}', datetime) as grp_time,
                    ROW_NUMBER() OVER (
                        PARTITION BY date_trunc('{duck_freq}', datetime)
                        {', symbol' if not symbol else ''}
                        ORDER BY datetime DESC
                    ) as rn
                FROM futures_ohlcv
                {where}
            )
            SELECT
                grp_time as datetime,
                min(open)  as open,
                max(high)  as high,
                min(low)   as low,
                (SELECT close FROM grouped g2
                 WHERE g2.grp_time = g.grp_time
                   {('AND g2.symbol = g.symbol' if not symbol else '')}
                 ORDER BY g2.datetime DESC LIMIT 1) as close,
                sum(volume) as volume,
                (SELECT hold FROM grouped g2
                 WHERE g2.grp_time = g.grp_time
                   {('AND g2.symbol = g.symbol' if not symbol else '')}
                 ORDER BY g2.datetime DESC LIMIT 1) as hold
                {', symbol' if not symbol else ''}
            FROM grouped g
            WHERE rn = 1
            GROUP BY grp_time
                {', symbol' if not symbol else ''}
            ORDER BY grp_time
        """
        df = self._conn.sql(sql).df()
        return df

    def _count_fast(self) -> int:
        return self._conn.sql("SELECT COUNT(*) FROM futures_ohlcv").fetchone()[0]
