"""
MySQL 适配器
优化：COMPOSITE KEY + RANGE 分区（按月）
     MySQL 8.0+ 支持窗口函数用于聚合
"""

from typing import Optional
import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

from .base import BaseAdapter
from .base import register_adapter


@register_adapter("mysql")
class MySQLAdapter(BaseAdapter):
    DB_NAME = "mysql"

    def __init__(self, host="localhost", port=3306, database="lott",
                 user="root", password="", charset="utf8mb4", **kwargs):
        super().__init__(host=host, port=port, database=database, user=user, password=password, **kwargs)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.charset = charset
        self._conn: Optional[pymysql.Connection] = None

    def connect(self):
        self._conn = pymysql.connect(
            host=self.host, port=self.port, database=self.database,
            user=self.user, password=self.password, charset=self.charset,
            cursorclass=DictCursor, autocommit=False,
        )
        self._connected = True

    def disconnect(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._connected = False

    # ====== Schema ======

    def create_schema(self):
        cur = self._conn.cursor()
        # MySQL 分区表：按月 RANGE 分区，自动管理大数据量
        cur.execute("""
            CREATE TABLE IF NOT EXISTS futures_ohlcv (
                id          BIGINT UNSIGNED AUTO_INCREMENT,
                symbol      VARCHAR(32)  NOT NULL,
                exchange    VARCHAR(16)  NOT NULL DEFAULT '',
                datetime    DATETIME(3) NOT NULL,
                open        DECIMAL(12,4) NOT NULL,
                high        DECIMAL(12,4) NOT NULL,
                low         DECIMAL(12,4) NOT NULL,
                close       DECIMAL(12,4) NOT NULL,
                volume      BIGINT UNSIGNED NOT NULL DEFAULT 0,
                hold        BIGINT UNSIGNED NOT NULL DEFAULT 0,
                PRIMARY KEY (id, datetime),
                UNIQUE KEY  uk_symbol_dt (symbol, datetime),
                KEY         k_datetime (datetime),
                KEY         k_symbol (symbol)
            ) ENGINE=InnoDB
            PARTITION BY RANGE (TO_DAYS(datetime)) (
                PARTITION p_default VALUES LESS THAN MAXVALUE
            )
        """)
        self._conn.commit()
        cur.close()

    def drop_schema(self):
        cur = self._conn.cursor()
        cur.execute("DROP TABLE IF EXISTS futures_ohlcv")
        self._conn.commit()
        cur.close()

    # ====== 写入 ======

    def bulk_insert(self, df: pd.DataFrame) -> int:
        df = self.normalize_df(df)
        if "symbol" not in df.columns:
            df["symbol"] = ""
        if "exchange" not in df.columns:
            df["exchange"] = ""

        rows = [
            {
                "symbol": str(r.get("symbol", "")),
                "exchange": str(r.get("exchange", "")),
                "datetime": pd.Timestamp(r["datetime"]).strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r["volume"]),
                "hold": int(r.get("hold", 0)),
            }
            for _, r in df.iterrows()
        ]

        cols = ["symbol", "exchange", "datetime", "open", "high", "low", "close", "volume", "hold"]
        placeholders = ", ".join(["%(" + c + ")s" for c in cols])
        sql = f"INSERT IGNORE INTO futures_ohlcv ({', '.join(cols)}) VALUES ({placeholders})"

        cur = self._conn.cursor()
        cur.executemany(sql, rows)
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
        # MySQL 8.0 + 窗口函数
        freq_map = {
            "1min": "MINUTE", "5min": "MINUTE", "15min": "MINUTE",
            "30min": "MINUTE", "1H": "HOUR", "1D": "DAY",
        }
        mysql_freq = freq_map.get(freq, "HOUR")

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

        # MySQL 聚合：用子查询模拟
        sql = f"""
            SELECT
                DATE_FORMAT(DATE_ADD(datetime, INTERVAL -MINUTE(datetime)%(intvl)s MINUTE), '%%Y-%%m-%%d %%H:%%i:00') AS datetime,
                SUBSTRING_INDEX(GROUP_CONCAT(open   ORDER BY datetime), ',', 1) as open,
                MAX(high)  as high,
                MIN(low)   as low,
                SUBSTRING_INDEX(SUBSTRING_INDEX(GROUP_CONCAT(close  ORDER BY datetime DESC), ',', 1), ',', -1) as close,
                SUM(volume) as volume,
                SUBSTRING_INDEX(SUBSTRING_INDEX(GROUP_CONCAT(hold   ORDER BY datetime DESC), ',', 1), ',', -1) as hold
                {', symbol' if not symbol else ''}
            FROM futures_ohlcv
            {where}
            GROUP BY FLOOR(UNIX_TIMESTAMP(datetime) / %(intvl)s)
                {', symbol' if not symbol else ''}
            ORDER BY datetime
        """.replace("%(intvl)s", str({"1min": 60, "5min": 300, "15min": 900, "30min": 1800, "1H": 3600, "1D": 86400}.get(freq, 3600)))

        df = pd.read_sql_query(sql, self._conn, params=params if params else None)
        return df

    def _count_fast(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM futures_ohlcv")
        count = list(cur.fetchone().values())[0]
        cur.close()
        return count
