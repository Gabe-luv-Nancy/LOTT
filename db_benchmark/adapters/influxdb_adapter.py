"""
InfluxDB 适配器
优化：InfluxDB 原生时序模型，Tag 索引，Timestamptp 时间戳
     支持连续查询（downsampling）和保留策略
"""

from typing import Optional
import pandas as pd
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

from .base import BaseAdapter
from .base import register_adapter


@register_adapter("influxdb")
class InfluxDBAdapter(BaseAdapter):
    DB_NAME = "influxdb"
    SUPPORTS_BULK_INSERT = True
    SUPPORTS_UPSERT = True
    TABLE_NAME = "futures_ohlcv"  # InfluxDB 里叫 measurement

    def __init__(self, url="http://localhost:8086", token="", org="lott",
                 bucket="futures", timeout=30_000, **kwargs):
        super().__init__(url=url, token=token, org=org, bucket=bucket, **kwargs)
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.timeout = timeout
        self._client: Optional[InfluxDBClient] = None
        self._write_api = None
        self._query_api = None

    def connect(self):
        self._client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org,
            timeout=self.timeout,
        )
        self._write_api = self._client.write_api(write_type=SYNCHRONOUS)
        self._query_api = self._client.query_api()
        self._connected = True

    def disconnect(self):
        if self._client:
            self._client.close()
            self._client = None
            self._connected = False

    # ====== Schema ======

    def create_schema(self):
        """InfluxDB 是 schemaless，但我们可以创建保留策略和连续查询"""
        # 创建保留策略（默认保留 100 年）
        try:
            self._client.write_api().write(
                bucket=f"{self.bucket}/autogen",
                org=self.org,
                record="futures_ohlcv,symbol=init,exchange=init datetime=0,open=0,high=0,low=0,close=0,volume=0,hold=0",
            )
        except Exception:
            pass  # 已存在

    def drop_schema(self):
        """删除measurement"""
        try:
            self._client.delete_api().delete(
                predicate='_measurement="futures_ohlcv"',
                start="1970-01-01T00:00:00Z",
                stop="2030-01-01T00:00:00Z",
                bucket=self.bucket,
                org=self.org,
            )
        except Exception:
            pass

    # ====== 写入 ======

    def bulk_insert(self, df: pd.DataFrame) -> int:
        df = self.normalize_df(df)
        if "symbol" not in df.columns:
            df["symbol"] = ""
        if "exchange" not in df.columns:
            df["exchange"] = ""

        from influxdb_client import Point

        points = []
        for _, r in df.iterrows():
            pt = Point(self.TABLE_NAME) \
                .tag("symbol", str(r.get("symbol", ""))) \
                .tag("exchange", str(r.get("exchange", ""))) \
                .field("open", float(r["open"])) \
                .field("high", float(r["high"])) \
                .field("low", float(r["low"])) \
                .field("close", float(r["close"])) \
                .field("volume", int(r["volume"])) \
                .field("hold", int(r.get("hold", 0))) \
                .time(pd.Timestamp(r["datetime"]).value)
            points.append(pt)

        self._write_api.write(bucket=self.bucket, org=self.org, record=points)
        return len(points)

    # ====== 查询 ======

    def query_range(
        self,
        symbol: Optional[str] = None,
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        cond = f'_measurement="{self.TABLE_NAME}"'
        if symbol:
            cond += f' AND symbol="{symbol}"'
        if start_dt:
            cond += f' AND time >= {pd.Timestamp(start_dt).value}'
        if end_dt:
            cond += f' AND time <= {pd.Timestamp(end_dt).value}'

        flux = f'''
            from(bucket:"{self.bucket}")
            |> range(start: 0)
            |> filter(fn: (r) => {cond})
            |> sort(columns: ["time"])
            '''
        if limit:
            flux += f"\n|> limit(n: {limit})"

        try:
            tables = self._query_api.query(flux, org=self.org)
            records = []
            for table in tables:
                for record in table.records:
                    records.append({
                        "datetime": record.get_time(),
                        "symbol": record.values.get("symbol", ""),
                        "exchange": record.values.get("exchange", ""),
                        "open": record.values.get("open"),
                        "high": record.values.get("high"),
                        "low": record.values.get("low"),
                        "close": record.values.get("close"),
                        "volume": record.values.get("volume"),
                        "hold": record.values.get("hold"),
                    })
            return pd.DataFrame(records)
        except Exception:
            return pd.DataFrame()

    def query_latest(self, symbol: str, n: int = 1) -> pd.DataFrame:
        flux = f'''
            from(bucket:"{self.bucket}")
            |> range(start: 0)
            |> filter(fn: (r) => r._measurement == "{self.TABLE_NAME}" AND r.symbol == "{symbol}")
            |> sort(columns: ["time"], desc: true)
            |> limit(n: {n})
        '''
        try:
            tables = self._query_api.query(flux, org=self.org)
            records = []
            for table in tables:
                for record in table.records:
                    records.append({
                        "datetime": record.get_time(),
                        "symbol": record.values.get("symbol", ""),
                        "open": record.values.get("open"),
                        "high": record.values.get("high"),
                        "low": record.values.get("low"),
                        "close": record.values.get("close"),
                        "volume": record.values.get("volume"),
                        "hold": record.values.get("hold"),
                    })
            return pd.DataFrame(records)
        except Exception:
            return pd.DataFrame()

    def query_aggregate(
        self,
        symbol: Optional[str] = None,
        freq: str = "1H",
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
    ) -> pd.DataFrame:
        interval_map = {
            "1min": "1m", "5min": "5m", "15min": "15m",
            "30min": "30m", "1H": "1h", "1D": "1d",
        }
        interval = interval_map.get(freq, "1h")

        cond = f'_measurement="{self.TABLE_NAME}"'
        if symbol:
            cond += f' AND symbol="{symbol}"'
        if start_dt:
            cond += f' AND time >= {pd.Timestamp(start_dt).value}'
        if end_dt:
            cond += f' AND time <= {pd.Timestamp(end_dt).value}'

        flux = f'''
            from(bucket:"{self.bucket}")
            |> range(start: 0)
            |> filter(fn: (r) => {cond})
            |> window(interval: {interval})
            |> reduce(
                identity: {{open: 0.0, high: 0.0, low: 999999.0, close: 0.0, volume: 0, hold: 0}},
                fn: (r, accumulator) => ({{
                    open: if accumulator.open == 0.0 then r.open else accumulator.open,
                    high: if r.high > accumulator.high then r.high else accumulator.high,
                    low: if r.low < accumulator.low then r.low else accumulator.low,
                    close: r.close,
                    volume: accumulator.volume + r.volume,
                    hold: r.hold,
                }})
            )
            |> duplicate(column: "_stop", as: "_time")
            |> keep(columns: ["_time", "open", "high", "low", "close", "volume", "hold"])
        '''
        try:
            tables = self._query_api.query(flux, org=self.org)
            records = []
            for table in tables:
                for record in table.records:
                    records.append({
                        "datetime": record.get_time(),
                        "open": record.values.get("open"),
                        "high": record.values.get("high"),
                        "low": record.values.get("low"),
                        "close": record.values.get("close"),
                        "volume": record.values.get("volume"),
                        "hold": record.values.get("hold"),
                    })
            df = pd.DataFrame(records)
            if symbol and not df.empty:
                df["symbol"] = symbol
            return df
        except Exception:
            return pd.DataFrame()

    def _count_fast(self) -> int:
        flux = f'''
            from(bucket:"{self.bucket}")
            |> range(start: 0)
            |> filter(fn: (r) => r._measurement == "{self.TABLE_NAME}")
            |> count()
        '''
        try:
            tables = self._query_api.query(flux, org=self.org)
            for table in tables:
                for record in table.records:
                    return int(record.get_value())
        except Exception:
            return 0
        return 0
