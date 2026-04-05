import logging
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

try:
    from dateutil.parser import parse
except ImportError:
    parse = None

try:
    import pytz
except ImportError:
    pytz = None


class TimestampEngine:
    """
    时间戳解析与标准化引擎。

    支持 7 种时间格式自动识别与统一转换，
    提供去重、时区标准化、重采样等清洗功能。

    用法:
        engine = TimestampEngine()
        df = engine.normalize(df, 'timestamp')
        df = engine.clean(df, 'timestamp', strategy={'duplicates': 'keep_last'})
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def normalize(self, df: pd.DataFrame, time_column: str) -> pd.DataFrame:
        """将时间列标准化为 UTC 时区的 DatetimeIndex"""
        try:
            if time_column not in df.columns:
                raise ValueError(f"时间列 '{time_column}' 不存在")

            df[time_column] = self._convert_to_datetime(df[time_column])
            df = df.set_index(time_column)

            if not isinstance(df.index, pd.DatetimeIndex):
                self.logger.warning("索引不是 DatetimeIndex 类型")
                return df

            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            else:
                df.index = df.index.tz_convert('UTC')

            df.index = df.index.astype('datetime64[ns, UTC]')
            return df
        except Exception as e:
            self.logger.error(f"时间标准化失败: {e}")
            return df

    def clean(
        self,
        df: pd.DataFrame,
        time_column: str,
        strategy: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        清洗时间数据。

        strategy 字典支持:
            duplicates: keep_first | keep_last | average | sum | min | max
            resample.freq: 重采样频率（如 'D', '1h'）
            resample.method: 插值方法（linear, ffill, bfill, nearest, zero, constant）
        """
        if strategy is None:
            strategy = {'duplicates': 'keep_last'}

        try:
            df = self.normalize(df, time_column)
            dup = strategy.get('duplicates', 'keep_last')
            if dup != 'none':
                df = self._handle_duplicates(df, dup)

            if 'resample' in strategy:
                freq    = strategy['resample'].get('freq', 'D')
                method  = strategy['resample'].get('method', 'linear')
                df = self.resample(df, freq=freq, method=method)

            return df
        except Exception as e:
            self.logger.error(f"时间清洗失败: {e}")
            return df

    def resample(
        self,
        df: pd.DataFrame,
        freq: str = 'D',
        method: str = 'linear',
        fill_value: Optional[float] = None,
    ) -> pd.DataFrame:
        """重采样时间序列"""
        try:
            if method == 'linear':
                return df.resample(freq).interpolate(method='linear')
            elif method in ('pad', 'ffill'):
                return df.resample(freq).ffill()
            elif method in ('backfill', 'bfill'):
                return df.resample(freq).bfill()
            elif method == 'nearest':
                return df.resample(freq).nearest()
            elif method == 'zero':
                return df.resample(freq).asfreq().fillna(0)
            elif method == 'constant' and fill_value is not None:
                return df.resample(freq).asfreq().fillna(fill_value)
            else:
                return df.resample(freq).mean()
        except Exception as e:
            self.logger.error(f"重采样失败: {e}")
            return df

    def process_financial(self, df: pd.DataFrame) -> pd.DataFrame:
        """金融数据处理：跳过非交易日（周末）"""
        if not isinstance(df.index, pd.DatetimeIndex):
            self.logger.warning("索引不是 DatetimeIndex，无法过滤非交易日")
            return df
        return df[df.index.dayofweek < 5]

    def process_iot(self, df: pd.DataFrame) -> pd.DataFrame:
        """IoT 数据处理：时钟漂移校正（预留）"""
        self.logger.warning("时钟漂移校正功能暂未实现")
        return df

    def process_scientific(self, df: pd.DataFrame) -> pd.DataFrame:
        """科学数据处理：非标准日历转换（预留）"""
        self.logger.warning("非标准日历转换功能暂未实现")
        return df

    def _convert_to_datetime(self, series: pd.Series) -> pd.Series:
        """将各种格式的时间数据转换为 UTC datetime"""
        parsed = pd.Series(index=series.index, dtype='datetime64[ns, UTC]')

        for idx, value in series.items():
            try:
                # 数值型时间戳（Unix）
                if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
                    ts = float(value)
                    if ts > 1e10:          # 毫秒级
                        parsed[idx] = pd.to_datetime(ts, unit='ms', utc=True)
                    else:                   # 秒级
                        parsed[idx] = pd.to_datetime(ts, unit='s', utc=True)
                    continue

                # dateutil 解析
                if parse is not None:
                    dt = parse(str(value))
                    if dt.tzinfo is None:
                        if pytz is not None:
                            dt = pytz.utc.localize(dt)
                    else:
                        dt = dt.astimezone(pytz.utc)
                    parsed[idx] = dt
                else:
                    parsed[idx] = pd.to_datetime(value, utc=True)

            except Exception:
                try:
                    parsed[idx] = pd.to_datetime(value, utc=True)
                except Exception:
                    self.logger.error(f"无法解析时间格式: {value}")
                    parsed[idx] = pd.NaT

        return parsed

    def _handle_duplicates(self, df: pd.DataFrame, strategy: str) -> pd.DataFrame:
        """处理重复时间戳"""
        if not isinstance(df.index, pd.DatetimeIndex):
            self.logger.warning("无法处理重复时间戳 - 索引不是 DatetimeIndex")
            return df

        strategy_map = {
            'keep_first': lambda d: d[~d.index.duplicated(keep='first')],
            'keep_last':  lambda d: d[~d.index.duplicated(keep='last')],
            'average':    lambda d: d.groupby(d.index).mean(),
            'sum':        lambda d: d.groupby(d.index).sum(),
            'min':        lambda d: d.groupby(d.index).min(),
            'max':        lambda d: d.groupby(d.index).max(),
        }
        func = strategy_map.get(strategy, strategy_map['keep_last'])
        return func(df)
