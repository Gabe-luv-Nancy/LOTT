"""
SQLite 适配器
优化：WAL模式 + 批量插入 + 复合索引
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional
import numpy as np

import pandas as pd

from .base import BaseAdapter
from .base import register_adapter


@register_adapter("sqlite")
class SQLiteAdapter(BaseAdapter):
    DB_NAME = "sqlite"

    def __init__(self, path: str = ":memory:", timeout: int = 30, **kwargs):
        super().__init__(path=path, timeout=timeout, **kwargs)
        self.path = path
        self.timeout = timeout
        self._conn: Optional[sqlite3.Connection] = None

    # ====== 连接管理 ======

    def connect(self):
        if self._conn:
            return
        # 创建目录
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, timeout=self.timeout)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        self._conn.execute("PRAGMA temp_store=MEMORY")
        self._conn.row_factory = sqlite3.Row
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
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol          TEXT    NOT NULL,
                exchange        TEXT    NOT NULL DEFAULT '',
                datetime        TEXT    NOT NULL,
                open            REAL    NOT NULL,
                high            REAL    NOT NULL,
                low             REAL    NOT NULL,
                close           REAL    NOT NULL,
                volume          INTEGER NOT NULL DEFAULT 0,
                hold            INTEGER NOT NULL DEFAULT 0
            )
        """)
        # 复合唯一索引：防止同一时刻同一品种重复
        self._conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_symbol_datetime
            ON futures_ohlcv(symbol, datetime)
        """)
        # 时间范围快速过滤
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_datetime
            ON futures_ohlcv(datetime)
        """)
        # symbol 前缀加速 LIKE 查询
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol
            ON futures_ohlcv(symbol)
        """)
        self._conn.commit()

    def drop_schema(self):
        self._conn.execute("DROP TABLE IF EXISTS futures_ohlcv")
        self._conn.commit()

    # ====== 写入 ======

    def bulk_insert(self, df: pd.DataFrame) -> int:
        df = self.normalize_df(df)
        rows = [
            (
                row.get("symbol", ""),
                row.get("exchange", ""),
                pd.Timestamp(row["datetime"]).strftime("%Y-%m-%d %H:%M:%S"),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                int(row["volume"]),
                int(row.get("hold", 0)),
            )
            for _, row in df.iterrows()
        ]
        self._conn.executemany(
            "INSERT OR IGNORE INTO futures_ohlcv "
            "(symbol, exchange, datetime, open, high, low, close, volume, hold) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self._conn.commit()
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
            cond.append("symbol = ?")
            params.append(symbol)
        if start_dt:
            cond.append("datetime >= ?")
            params.append(start_dt)
        if end_dt:
            cond.append("datetime <= ?")
            params.append(end_dt)

        where = ("WHERE " + " AND ".join(cond)) if cond else ""
        sql = f"SELECT * FROM futures_ohlcv {where} ORDER BY datetime"
        if limit:
            sql += f" LIMIT {limit}"
        if params:
            df = pd.read_sql_query(sql, self._conn, params=params)
        else:
            df = pd.read_sql_query(sql, self._conn)
        return df

    def query_latest(self, symbol: str, n: int = 1) -> pd.DataFrame:
        df = pd.read_sql_query(
            "SELECT * FROM futures_ohlcv WHERE symbol = ? ORDER BY datetime DESC LIMIT ?",
            self._conn,
            params=(symbol, n),
        )
        return df

    def query_aggregate(
        self,
        symbol: Optional[str] = None,
        freq: str = "1H",
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
    ) -> pd.DataFrame:
        # SQLite 不支持复杂窗口函数，用 Python 聚合
        freq_map = {"1H": "h", "1D": "D", "1min": "min", "5min": "5min",
                    "15min": "15min", "30min": "30min"}
        pd_freq = freq_map.get(freq, freq)
        df = self.query_range(symbol=symbol, start_dt=start_dt, end_dt=end_dt)
        if df.empty:
            return df
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime")

        grp = df.groupby(pd.Grouper(freq=pd_freq))
        agg = grp.agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
            hold=("hold", "last"),
        )
        agg = agg.reset_index()
        if symbol:
            agg["symbol"] = symbol
        return agg

    def _count_fast(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM futures_ohlcv")
        return cur.fetchone()[0]
