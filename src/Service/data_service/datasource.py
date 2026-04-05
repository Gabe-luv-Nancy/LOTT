"""
Data Source - 数据源

模拟 CTP/SimNow 实时数据源

实际使用时，替换为真实的 python-ctp 库
"""

import asyncio
import logging
from typing import Optional, Callable, List, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass

from .redis_client import OHLCVMessage, TickMessage
from .config import DataSourceConfig


@dataclass
class QuoteData:
    """报价数据"""
    symbol: str
    exchange: str
    timestamp: datetime
    last_price: float
    last_volume: float
    bid_price: float
    bid_volume: float
    ask_price: float
    ask_volume: float


class CTPDataSource:
    """
    CTP 实时数据源
    
    Attributes:
        on_tick: Tick 数据回调
        on_ohlcv: OHLCV 数据回调
    """
    
    def __init__(self, config: DataSourceConfig = None):
        """
        初始化
        
        Args:
            config: 数据源配置
        """
        self.config = config or DataSourceConfig()
        
        # 回调
        self.on_tick: Optional[Callable[[TickMessage], None]] = None
        self.on_ohlcv: Optional[Callable[[OHLCVMessage], None]] = None
        
        # 状态
        self._connected = False
        self._subscribed: List[str] = []
        self._task: Optional[asyncio.Task] = None
        
        # 价格追踪 (用于生成 OHLCV)
        self._price_map: Dict[str, float] = {}
    
    async def connect(self) -> bool:
        """
        连接数据源
        
        Returns:
            是否连接成功
        """
        print(f"[CTP] 连接到 {self.config.ctp_front or 'simulator'}")
        
        # 模拟连接
        await asyncio.sleep(0.1)
        self._connected = True
        
        print("[CTP] 连接成功")
        return True
    
    async def disconnect(self) -> None:
        """断开连接"""
        self._connected = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        print("[CTP] 已断开连接")
    
    async def subscribe(
        self,
        symbols: List[str],
        timeframes: List[str] = None
    ) -> None:
        """
        订阅合约
        
        Args:
            symbols: 合约列表
            timeframes: 时间周期列表
        """
        self._subscribed = symbols
        self.config.symbols = symbols
        
        if timeframes:
            self.config.timeframes = timeframes
        
        print(f"[CTP] 已订阅 {len(symbols)} 个合约")
        
        # 开始模拟数据
        self._task = asyncio.create_task(self._simulate_data())
    
    async def unsubscribe(self) -> None:
        """取消订阅"""
        self._subscribed = []
        print("[CTP] 已取消订阅")
    
    async def _simulate_data(self) -> None:
        """模拟实时数据 (实际使用时替换为 CTP 回调)"""
        import random
        
        base_prices = {
            "IF2406": 3650.0,
            "IC2406": 5900.0,
            "IH2406": 5500.0,
            "TF2406": 105.0
        }
        
        while self._connected and self._subscribed:
            for symbol in self._subscribed:
                base = base_prices.get(symbol, 100.0)
                current = self._price_map.get(symbol, base)
                
                # 价格波动
                change = random.uniform(-5, 5)
                price = current + change
                self._price_map[symbol] = price
                
                # 创建 Tick
                quote = QuoteData(
                    symbol=symbol,
                    exchange="CFFEX",
                    timestamp=datetime.now(),
                    last_price=price,
                    last_volume=random.uniform(1000, 10000),
                    bid_price=price - 0.2,
                    bid_volume=random.uniform(100, 500),
                    ask_price=price + 0.2,
                    ask_volume=random.uniform(100, 500)
                )
                
                # 触发 Tick 回调
                if self.on_tick:
                    try:
                        msg = TickMessage(
                            symbol=quote.symbol,
                            exchange=quote.exchange,
                            timestamp=quote.timestamp,
                            last_price=quote.last_price,
                            last_volume=quote.last_volume,
                            bid_price=quote.bid_price,
                            bid_volume=quote.bid_volume,
                            ask_price=quote.ask_price,
                            ask_volume=quote.ask_volume,
                            source="ctp"
                        )
                        await self.on_tick(msg)
                    except Exception as e:
                        logging.error(f"[CTP] Tick回调失败: {e}")
            
            await asyncio.sleep(1)


class SimNowDataSource(CTPDataSource):
    """SimNow 模拟环境数据源"""
    
    def __init__(self):
        config = DataSourceConfig(
            source_type="simnow",
            simnow_front="tcp://180.168.146.187:10201"
        )
        super().__init__(config)


class OHLCVGenerator:
    """
    OHLCV 数据生成器
    
    用于生成回测用的 K 线数据
    """
    
    def __init__(self, config: DataSourceConfig = None):
        self.config = config or DataSourceConfig()
    
    def generate(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str,
        base_price: float = 3650.0
    ) -> List[Dict]:
        """
        生成 OHLCV 数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            base_price: 基准价格
            
        Returns:
            OHLCV 数据列表
        """
        import random
        random.seed(f"{symbol}{timeframe}{start_date}")
        
        # 时间周期
        tf_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1)
        }
        
        tf_delta = tf_map.get(timeframe, timedelta(minutes=1))
        
        # 日期范围
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        data = []
        current = start.replace(hour=9, minute=30, second=0)
        
        while current <= end:
            # 跳过周末
            if current.weekday() >= 5:
                current += tf_delta
                continue
            
            # 跳过非交易时间
            hour = current.hour
            if hour < 9 or (hour >= 15 and hour < 21):
                current += tf_delta
                continue
            
            # OHLCV
            change = random.uniform(-0.02, 0.02)
            open_price = base_price * (1 + random.uniform(-0.01, 0.01))
            close_price = open_price * (1 + change)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.005))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.005))
            
            data.append({
                "symbol": symbol,
                "exchange": "CFFEX",
                "timestamp": current.isoformat(),
                "timeframe": timeframe,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": round(random.uniform(10000, 50000), 0),
                "turnover": round(random.uniform(1000000, 5000000), 2),
                "source": "generator"
            })
            
            base_price = close_price
            current += tf_delta
        
        return data


# ==================== 使用示例 ====================

async def example_realtime():
    """实时数据示例"""
    from .service import create_data_service
    
    # 创建数据服务
    service = create_data_service()
    await service.initialize()
    await service.start()
    
    # 设置数据源回调
    ctp = CTPDataSource()
    ctp.on_tick = service.publish_tick
    await ctp.connect()
    await ctp.subscribe(["IF2406", "IC2406"])
    
    # 订阅实时数据
    async def on_realtime(msg):
        print(f"[Realtime] {msg.symbol}: {msg.last_price:.2f}")
    
    await service.subscribe_tick("IF2406", on_realtime)
    
    # 等待
    await asyncio.sleep(10)
    
    # 停止
    await ctp.disconnect()
    await service.stop()


if __name__ == "__main__":
    asyncio.run(example_realtime())
