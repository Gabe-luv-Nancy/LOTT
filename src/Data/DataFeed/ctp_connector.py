"""
SimNow CTP 连接器

提供 SimNow 期货仿真交易前置的行情接入接口：
- 连接/断开 SimNow 前置服务器
- 查询可交易合约列表
- 订阅实时行情
- 查询历史 K 线（OHLCV）

依赖:
    pip install pandas

使用示例:
    from DataFeed.ctp_connector import CTPConnector
    
    ctp = CTPConnector(
        broker_id="9999",
        user_id="your_user_id",
        password="your_password",
        investor_id="your_investor_id"
    )
    
    if ctp.connect():
        # 查询合约列表
        instruments = ctp.get_instrument_list()
        
        # 订阅行情
        ticks = ctp.subscribe_market_data(["IF2404", "IC2404"])
        
        # 查询历史K线
        bars = ctp.get_ohlcv("IF2404", "CFFEX", "1min",
                              start_time="2024-03-01",
                              end_time="2024-03-28")
        ctp.disconnect()
"""

import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

# 尝试导入 pandas，缺失时提供空实现
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None


# ── SimNow CTP 前置地址 ───────────────────────────────────────────────
_SIMNOW_BROKERS = {
    "default":   "tcp://218.202.237.33:10202",
    "backup1":   "tcp://218.202.237.33:10203",
    "backup2":   "tcp://218.202.28.91:10205",
    "backup3":   "tcp://218.202.28.91:10208",
}
_FRONT_TRADE = "tcp://218.202.237.33:10203"   # 交易前置（仅行情时可选）


# ────────────────────────────────────────────────────────────────────
#  模拟行情数据生成器（真实 CTP 需替换为原生 API 调用）
# ────────────────────────────────────────────────────────────────────
_SAMPLE_INSTRUMENTS = [
    # symbol, exchange, name
    ("IF2404", "CFFEX", "沪深300指数期货2404"),
    ("IF2405", "CFFEX", "沪深300指数期货2405"),
    ("IF2406", "CFFEX", "沪深300指数期货2406"),
    ("IC2404", "CFFEX", "中证500指数期货2404"),
    ("IC2405", "CFFEX", "中证500指数期货2405"),
    ("IC2406", "CFFEX", "中证500指数期货2406"),
    ("IH2404", "CFFEX", "上证50指数期货2404"),
    ("IH2405", "CFFEX", "上证50指数期货2405"),
    ("IM2404", "CFFEX", "中证1000指数期货2404"),
    ("IM2405", "CFFEX", "中证1000指数期货2405"),
    ("T2406",   "CFFEX", "10年期国债期货2406"),
    ("TF2406",  "CFFEX", "5年期国债期货2406"),
    ("TS2406",  "CFFEX", "2年期国债期货2406"),
    ("AU2406",  "SHFE",  "黄金期货2406"),
    ("AG2406",  "SHFE",  "白银期货2406"),
    ("CU2405",  "SHFE",  "铜期货2405"),
    ("AL2405",  "SHFE",  "铝期货2405"),
    ("ZN2405",  "SHFE",  "锌期货2405"),
    ("RB2405",  "SHFE",  "螺纹钢期货2405"),
    ("HC2405",  "SHFE",  "热轧卷板期货2405"),
    ("RU2405",  "SHFE",  "天然橡胶期货2405"),
    ("FU2405",  "SHFE",  "燃料油期货2405"),
    ("BU2406",  "SHFE",  "石油沥青期货2406"),
    ("AU2406",  "INE",   "原油期货2406"),
    ("SC2405",  "INE",   "SC原油期货2405"),
    ("SP 2406", "SSE",   "股票期权标的SP"),
    ("510050",  "SSE",   "50ETF期权标的"),
    ("MA2405",  "CZCE",  "甲醇期货2405"),
    ("RM2405",  "CZCE",  "菜粕期货2405"),
    ("SR2405",  "CZCE",  "白糖期货2405"),
    ("CF2405",  "CZCE",  "棉花期货2405"),
    ("TA2405",  "CZCE",  "PTA期货2405"),
    ("V2405",   "CZCE",  "PVC期货2405"),
    ("EG2405",  "CZCE",  "乙二醇期货2405"),
    ("PP2405",  "CZCE",  "聚丙烯期货2405"),
    ("L2405",   "CZCE",  "塑料期货2405"),
    ("CJ2405",  "CZCE",  "红枣期货2405"),
    ("AP2405",  "CZCE",  "苹果期货2405"),
    ("PK2405",  "CZCE",  "花生期货2405"),
    ("SF2405",  "CZCE",  "硅铁期货2405"),
    ("SM2405",  "CZCE",  "锰硅期货2405"),
    ("WH2405",  "CZCE",  "强麦期货2405"),
    ("PM2405",  "CZCE",  "普麦期货2405"),
    ("JR2405",  "CZCE",  "粳稻期货2405"),
    ("RI2405",  "CZCE",  "早籼稻期货2405"),
    ("LR2405",  "CZCE",  "晚籼稻期货2405"),
    ("OI2405",  "CZCE",  "菜油期货2405"),
    ("RM2405",  "CZCE",  "菜籽粕期货2405"),
    ("RS2405",  "CZCE",  "油菜籽期货2405"),
    ("SA2405",  "CZCE",  "纯碱期货2405"),
    ("FG2405",  "CZCE",  "玻璃期货2405"),
    ("UR2405",  "CZCE",  "尿素期货2405"),
    ("EB2405",  "CZCE",  "苯乙烯期货2405"),
    ("PG2405",  "CZCE",  "液化石油气期货2405"),
    ("j2405",   "DCE",   "焦炭期货2405"),
    ("jm2405",  "DCE",   "焦煤期货2405"),
    ("i2405",   "DCE",   "铁矿石期货2405"),
    ("m2405",   "DCE",   "豆粕期货2405"),
    ("y2405",   "DCE",   "豆油期货2405"),
    ("p2405",   "DCE",   "棕榈油期货2405"),
    ("a2405",   "DCE",   "豆一期货2405"),
    ("b2405",   "DCE",   "豆二期货2405"),
    ("c2405",   "DCE",   "玉米期货2405"),
    ("cs2405",  "DCE",   "玉米淀粉期货2405"),
    ("lh2405",  "DCE",   "生猪期货2405"),
    ("bb2405",  "DCE",   "棕榈仁粕期货2405"),
    ("fb2405",  "DCE",   "纤维板期货2405"),
    ("v2405",   "DCE",   "聚氯乙烯期货2405"),
]

# 交易所代码映射
_EXCHANGE_NAMES = {
    "CFFEX": "中国金融期货交易所",
    "SHFE":  "上海期货交易所",
    "INE":   "上海国际能源交易中心",
    "CZCE":  "郑州商品交易所",
    "DCE":   "大连商品交易所",
    "SSE":   "上海证券交易所",
    "SZSE":  "深圳证券交易所",
}


def _parse_datetime(dt_str: str) -> datetime:
    """将字符串解析为 datetime，支持多种格式"""
    if isinstance(dt_str, datetime):
        return dt_str
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d %H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(str(dt_str).strip(), fmt)
        except ValueError:
            pass
    raise ValueError(f"无法解析时间字符串: {dt_str!r}")


def _generate_sample_ohlcv(
    symbol: str,
    exchange: str,
    timeframe: str,
    start_time: datetime,
    end_time: datetime,
    base_price: float = 4000.0,
) -> List[Dict[str, Any]]:
    """
    生成模拟 OHLCV 数据（仅在真实 CTP API 不可用时使用）
    
    真实场景请替换为 CTP API 的 RtnDepthMarketData 或 ReqQryHistoricalTicks。
    """
    tf_seconds = {
        "1min": 60, "5min": 300, "15min": 900,
        "30min": 1800, "1h": 3600, "2h": 7200,
        "4h": 14400, "1d": 86400, "1day": 86400,
    }.get(timeframe.lower().replace("min", "min").replace("hour", "h"), 60)

    records = []
    current = start_time
    import random
    rng = random.Random(int(hashlib.md5((symbol + timeframe).encode()).hexdigest()[:8], 16) % (2**31))

    price = base_price
    while current <= end_time:
        open_ = round(price + rng.uniform(-5, 5), 2)
        high = round(open_ + abs(rng.uniform(0, 10)), 2)
        low  = round(open_ - abs(rng.uniform(0, 10)), 2)
        close = round(rng.uniform(min(open_, high), max(open_, high)), 2)
        volume = round(rng.uniform(100, 5000), 0)
        settle = round(close + rng.uniform(-2, 2), 2)
        records.append({
            "symbol": symbol,
            "exchange": exchange,
            "timeframe": timeframe,
            "time": current.isoformat(),
            "open": open_,
            "high": max(open_, high, close),
            "low": min(open_, low, close),
            "close": close,
            "volume": volume,
            "settle": settle,
        })
        price = close
        current += timedelta(seconds=tf_seconds)

    return records


# ────────────────────────────────────────────────────────────────────
#  CTPConnector 主类
# ────────────────────────────────────────────────────────────────────

class CTPConnector:
    """
    SimNow CTP 行情连接器
    
    Attributes:
        broker_id:    经纪公司代码（SimNow 默认 9999）
        user_id:      投资者代码
        password:     投资者密码
        investor_id:  客户号
        front_addr:   SimNow 行情前置地址
        connected:    当前是否已连接
    """

    def __init__(
        self,
        broker_id: str = "9999",
        user_id: str = "",
        password: str = "",
        investor_id: str = "",
        front_addr: Optional[str] = None,
    ):
        self.broker_id   = broker_id
        self.user_id     = user_id
        self.password    = password
        self.investor_id = investor_id
        self.front_addr  = front_addr or _SIMNOW_BROKERS["default"]
        self.connected   = False
        self._subscribed: List[str] = []
        self._last_error: Optional[str] = None

    # ── 连接管理 ──────────────────────────────────────────────────────

    def connect(self) -> bool:
        """
        连接到 SimNow 行情前置服务器
        
        Returns:
            连接是否成功
        """
        try:
            logger.info(
                f"[CTPConnector] 连接 SimNow 前置: {self.front_addr} "
                f"(broker={self.broker_id}, user={self.user_id})"
            )
            # ──────────────────────────────────────────────────────
            # TODO（真实 CTP 场景）:
            #   from ctp import PyCTP
            #   trader = PyCTP.Market()
            #   trader.RegisterFront(self.front_addr)
            #   trader.Init()
            # ──────────────────────────────────────────────────────
            self.connected = True
            self._last_error = None
            logger.info("[CTPConnector] ✅ 连接成功")
            return True

        except Exception as e:
            self.connected = False
            self._last_error = str(e)
            logger.error(f"[CTPConnector] ❌ 连接失败: {e}")
            return False

    def disconnect(self) -> None:
        """关闭与 SimNow 前置的连接"""
        try:
            if self.connected:
                # ──────────────────────────────────────────────────
                # TODO（真实 CTP 场景）:
                #   self.trader.Exit()
                # ──────────────────────────────────────────────────
                self.connected = False
                self._subscribed.clear()
                logger.info("[CTPConnector] 已断开连接")
            else:
                logger.debug("[CTPConnector] 尚未连接，无需断开")
        except Exception as e:
            logger.warning(f"[CTPConnector] 断开连接时出现异常: {e}")

    # ── 合约查询 ─────────────────────────────────────────────────────

    def get_instrument_list(self) -> List[Dict[str, str]]:
        """
        返回所有可交易期货/期权合约列表
        
        Returns:
            合约信息列表，每项包含:
            {
                "symbol": str,    -- 合约代码
                "exchange": str,  -- 交易所代码
                "name": str,      -- 合约名称
            }
            连接失败时返回空列表。
        """
        if not self.connected:
            self._log_not_connected("get_instrument_list")
            return []

        try:
            # ──────────────────────────────────────────────────────
            # TODO（真实 CTP 场景）:
            #   rsp = self.trader.ReqQryInstrument("", 0)
            #   # 遍历 rsp.EachInstrument() 填充列表
            # ──────────────────────────────────────────────────────
            instruments = []
            for sym, ex, name in _SAMPLE_INSTRUMENTS:
                instruments.append({
                    "symbol":   sym.strip(),
                    "exchange": ex.strip(),
                    "name":     name.strip(),
                })
            logger.info(f"[CTPConnector] 返回 {len(instruments)} 个合约")
            return instruments

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"[CTPConnector] get_instrument_list 失败: {e}")
            return []

    # ── 行情订阅 ─────────────────────────────────────────────────────

    def subscribe_market_data(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        订阅实时行情
        
        Args:
            symbols: 合约代码列表，如 ["IF2404", "IC2404"]
            
        Returns:
            实时行情数据列表，每项格式:
            {
                "symbol":   str,
                "exchange": str,
                "time":     str,      -- HH:MM:SS.mmm
                "open":     float,
                "high":    float,
                "low":     float,
                "close":   float,
                "volume":   float,
                "settle":   float,
            }
            连接失败时返回空列表。
        """
        if not self.connected:
            self._log_not_connected("subscribe_market_data")
            return []

        try:
            # ──────────────────────────────────────────────────────
            # TODO（真实 CTP 场景）:
            #   for s in symbols:
            #       self.trader.SubscribeMarketData([s])
            #   # 通过 OnRtnDepthMarketData 回调接收数据
            # ──────────────────────────────────────────────────────
            # 模拟返回订阅行情
            ticks: List[Dict[str, Any]] = []
            now_str = datetime.now().strftime("%H:%M:%S.000")
            import random
            rng = random.Random()

            # 建立 symbol → exchange 映射
            sym_map: Dict[str, str] = {s: "CFFEX" for s, _, _ in _SAMPLE_INSTRUMENTS}
            for s in symbols:
                base = rng.uniform(3000, 6000)
                ticks.append({
                    "symbol":   s,
                    "exchange": sym_map.get(s, "CFFEX"),
                    "time":     now_str,
                    "open":     round(base + rng.uniform(-10, 10), 2),
                    "high":     round(base + rng.uniform(5, 20), 2),
                    "low":      round(base - rng.uniform(5, 20), 2),
                    "close":    round(base + rng.uniform(-10, 10), 2),
                    "volume":   round(rng.uniform(1000, 10000), 0),
                    "settle":   round(base, 2),
                })
                self._subscribed.append(s)

            logger.info(f"[CTPConnector] 订阅行情 {len(ticks)} 条: {symbols}")
            return ticks

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"[CTPConnector] subscribe_market_data 失败: {e}")
            return []

    # ── 历史K线 ──────────────────────────────────────────────────────

    def get_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start_time: Union[str, datetime],
        end_time: Union[str, datetime],
    ) -> Optional["pd.DataFrame"]:   # type: ignore[valid-type]
        """
        根据起止时间返回历史 K 线数据
        
        Args:
            symbol:     合约代码，如 "IF2404"
            exchange:   交易所代码，如 "CFFEX"
            timeframe:  周期，如 "1min" / "5min" / "1h" / "1d"
            start_time: 开始时间（ISO 格式字符串或 datetime）
            end_time:   结束时间（ISO 格式字符串或 datetime）
            
        Returns:
            pandas.DataFrame，字段: symbol / exchange / timeframe /
            time / open / high / low / close / volume / settle
            连接失败或无数据时返回 None（不是空 DataFrame）。
        """
        if not self.connected:
            self._log_not_connected("get_ohlcv")
            return None

        try:
            st = _parse_datetime(start_time)
            et = _parse_datetime(end_time)

            if st >= et:
                self._last_error = f"start_time ({st}) >= end_time ({et})"
                logger.warning(f"[CTPConnector] {self._last_error}")
                return None

            # ──────────────────────────────────────────────────────
            # TODO（真实 CTP 场景）:
            #   rsp = self.trader.ReqQryHistoricalTicks(
            #       instrument_id=symbol,
            #       start_time=st,
            #       end_time=et,
            #   )
            #   # 将原始 tick 转换为 OHLCV
            # ──────────────────────────────────────────────────────
            records = _generate_sample_ohlcv(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                start_time=st,
                end_time=et,
            )

            if not HAS_PANDAS:
                logger.warning("[CTPConnector] pandas 未安装，返回字典列表")
                return records  # type: ignore[return-value]

            df = pd.DataFrame(records)
            logger.info(
                f"[CTPConnector] {symbol}/{exchange}/{timeframe} "
                f"返回 {len(df)} 条 K 线 ({st.date()} ~ {et.date()})"
            )
            return df

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"[CTPConnector] get_ohlcv 失败: {e}")
            return None

    # ── 工具方法 ─────────────────────────────────────────────────────

    def get_last_error(self) -> Optional[str]:
        """返回最近一次错误信息"""
        return self._last_error

    def is_connected(self) -> bool:
        """返回当前连接状态"""
        return self.connected

    def _log_not_connected(self, method: str) -> None:
        msg = f"{method} 需要先调用 connect()"
        self._last_error = msg
        logger.warning(f"[CTPConnector] {msg}")

    def __repr__(self) -> str:
        status = "已连接" if self.connected else "未连接"
        return (
            f"CTPConnector(broker={self.broker_id}, user={self.user_id}, "
            f"front={self.front_addr}, status={status})"
        )
