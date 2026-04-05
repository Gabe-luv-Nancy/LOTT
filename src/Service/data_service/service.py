"""
Data Service Layer - 数据服务层

核心职责:
1. 实时数据分发 (Redis Pub/Sub)
2. 回测 OHLCV 数据准备
3. 数据缓存管理
4. 数据源统一接口

注意:
- 数据库 (TimescaleDB) 由另一团队负责，这里只关注 Service Layer
- 回测时主要使用 OHLCV 数据
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import json

from .config import (
    DataServiceConfig,
    BacktestConfig,
    DataSourceConfig
)
from .redis_client import (
    RedisClient,
    OHLCVMessage,
    TickMessage,
    create_redis_client
)


@dataclass
class OHLCVData:
    """OHLCV 数据结构 (用于回测)"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float = 0.0


@dataclass
class BacktestRequest:
    """回测请求"""
    symbols: List[str]
    timeframes: List[str]
    start_date: str  # "YYYY-MM-DD"
    end_date: str    # "YYYY-MM-DD"
    
    # 可选参数
    preload: bool = True  # 预加载到内存
    as_dataframe: bool = True  # 返回 DataFrame


@dataclass
class BacktestResponse:
    """回测响应"""
    success: bool
    data: Union[Dict[str, Dict[str, pd.DataFrame]], Dict[str, Any]] = None
    error: str = None
    metadata: Dict = None


class DataService:
    """
    Data Service Layer
    
    统一数据访问接口:
    - 实时数据分发 (Pub/Sub)
    - 回测数据准备 (OHLCV)
    - 缓存管理
    """
    
    def __init__(self, config: DataServiceConfig = None):
        """
        初始化
        
        Args:
            config: 服务配置
        """
        self.config = config or DataServiceConfig()
        
        # Redis 客户端
        self._redis: Optional[RedisClient] = None
        
        # 运行时状态
        self._running = False
        self._subscriptions: Dict[str, List[Callable]] = {}
        
        # 统计
        self._tick_count = 0
        self._ohlcv_count = 0
        
        # 回测数据缓存
        self._backtest_cache: Dict[str, pd.DataFrame] = {}
    
    # ==================== 生命周期管理 ====================
    
    async def initialize(self) -> None:
        """初始化"""
        print("[DataService] 初始化中...")
        
        self._redis = create_redis_client(
            host=self.config.redis.host,
            port=self.config.redis.port,
            key_prefix=self.config.redis.key_prefix
        )
        await self._redis.connect()
        
        print("[DataService] 初始化完成")
    
    async def start(self) -> None:
        """启动服务"""
        if self._running:
            return
        
        self._running = True
        print("[DataService] 服务已启动")
    
    async def stop(self) -> None:
        """停止服务"""
        self._running = False
        
        if self._redis:
            await self._redis.close()
        
        print("[DataService] 服务已停止")
    
    # ==================== 实时数据分发 ====================
    
    async def publish_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        data: Dict[str, Any]
    ) -> None:
        """
        发布 OHLCV 数据
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            timeframe: 时间周期
            data: OHLCV 数据字典
        """
        msg = OHLCVMessage(
            symbol=symbol,
            exchange=exchange,
            timestamp=datetime.now(),
            timeframe=timeframe,
            open_price=data['open'],
            high_price=data['high'],
            low_price=data['low'],
            close_price=data['close'],
            volume=data['volume'],
            turnover=data.get('turnover', 0),
            source="dataservice"
        )
        
        await self._redis.publish_ohlcv(msg)
        self._ohlcv_count += 1
    
    async def subscribe_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        callback: Callable[[OHLCVMessage], None]
    ) -> None:
        """
        订阅 OHLCV 实时数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            callback: 回调函数
        """
        await self._redis.subscribe_ohlcv(symbol, timeframe, callback)
    
    async def publish_tick(
        self,
        symbol: str,
        exchange: str,
        data: Dict[str, Any]
    ) -> None:
        """
        发布 Tick 数据
        
        Args:
            symbol: 合约代码
            exchange: 交易所
            data: Tick 数据字典
        """
        msg = TickMessage(
            symbol=symbol,
            exchange=exchange,
            timestamp=datetime.now(),
            last_price=data['last_price'],
            last_volume=data['last_volume'],
            bid_price=data.get('bid_price', 0),
            bid_volume=data.get('bid_volume', 0),
            ask_price=data.get('ask_price', 0),
            ask_volume=data.get('ask_volume', 0),
            source=data.get('source', 'ctp')
        )
        
        await self._redis.publish_tick(msg)
        self._tick_count += 1
    
    async def subscribe_tick(
        self,
        symbol: str,
        callback: Callable[[TickMessage], None]
    ) -> None:
        """
        订阅 Tick 实时数据
        
        Args:
            symbol: 合约代码
            callback: 回调函数
        """
        await self._redis.subscribe_tick(symbol, callback)
    
    # ==================== 回测数据准备 (核心功能) ====================
    
    async def prepare_backtest_data(
        self,
        request: BacktestRequest
    ) -> BacktestResponse:
        """
        准备回测数据 (核心方法)
        
        流程:
        1. 检查本地缓存
        2. 从 Redis 缓存获取
        3. 模拟生成 (如果不存在)
        
        Args:
            request: 回测请求
            
        Returns:
            BacktestResponse: 包含 DataFrame 字典
        """
        try:
            result: Dict[str, Dict[str, pd.DataFrame]] = {}
            metadata: Dict[str, Any] = {}
            
            for symbol in request.symbols:
                symbol_data: Dict[str, pd.DataFrame] = {}
                
                for timeframe in request.timeframes:
                    # 生成缓存键
                    cache_key = f"{symbol}:{timeframe}:{request.start_date}:{request.end_date}"
                    
                    # 检查内存缓存
                    if cache_key in self._backtest_cache:
                        symbol_data[timeframe] = self._backtest_cache[cache_key]
                        continue
                    
                    # 检查 Redis 缓存
                    redis_cache = await self._redis.get_cached_ohlcv(
                        symbol, timeframe
                    )
                    
                    if redis_cache and self.config.backtest.cache_ohlcv:
                        # 转换为 DataFrame
                        df = self._dict_list_to_dataframe(redis_cache)
                        
                        # 过滤日期范围
                        df = self._filter_by_date(df, request.start_date, request.end_date)
                        
                        if request.as_dataframe:
                            symbol_data[timeframe] = df
                        else:
                            symbol_data[timeframe] = df.to_dict('records')
                        
                        # 存入内存缓存
                        self._backtest_cache[cache_key] = df
                    else:
                        # 模拟生成数据 (实际应由数据库层提供)
                        df = await self._generate_ohlcv(
                            symbol, timeframe,
                            request.start_date, request.end_date
                        )
                        
                        if request.as_dataframe:
                            symbol_data[timeframe] = df
                        else:
                            symbol_data[timeframe] = df.to_dict('records')
                        
                        # 缓存到 Redis
                        if self.config.backtest.cache_ohlcv:
                            data_dict = df.to_dict('records')
                            await self._redis.cache_ohlcv(
                                symbol, timeframe, data_dict
                            )
                
                result[symbol] = symbol_data
                metadata[symbol] = {
                    "symbols": request.symbols,
                    "timeframes": request.timeframes,
                    "date_range": f"{request.start_date} to {request.end_date}",
                    "records": len(symbol_data.get(request.timeframes[0], pd.DataFrame()))
                }
            
            return BacktestResponse(
                success=True,
                data=result,
                metadata=metadata
            )
            
        except Exception as e:
            logging.error(f"[DataService] 准备回测数据失败: {e}")
            return BacktestResponse(
                success=False,
                error=str(e)
            )
    
    async def _generate_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        生成 OHLCV 数据 (模拟)
        
        实际实现中，这里应该调用数据库层获取真实数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            DataFrame
        """
        # 时间周期转换为 timedelta
        tf_map = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
            "4h": timedelta(hours=4),
            "1d": timedelta(days=1)
        }
        
        tf_delta = tf_map.get(timeframe, timedelta(minutes=1))
        
        # 生成日期范围
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 生成模拟数据
        import random
        random.seed(f"{symbol}{timeframe}{start_date}")
        
        base_price = {
            "IF2406": 3650.0,
            "IC2406": 5900.0,
            "IH2406": 5500.0,
            "TF2406": 105.0
        }.get(symbol, 100.0)
        
        data = []
        current_time = start.replace(hour=9, minute=30, second=0)
        
        while current_time <= end:
            # 跳过非交易时间
            if current_time.weekday() >= 5:  # 周末
                current_time += timedelta(days=1)
                continue
            
            hour = current_time.hour
            if hour < 9 or (hour >= 15 and hour < 21):  # 非交易时间
                current_time += tf_delta
                continue
            
            # 生成 OHLCV
            change = random.uniform(-0.02, 0.02)
            open_price = base_price * (1 + random.uniform(-0.1, 0.1))
            close_price = open_price * (1 + change)
            high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
            low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
            
            data.append({
                "timestamp": current_time,
                "open": round(open_price, 2),
                "high": round(high_price, 2),
                "low": round(low_price, 2),
                "close": round(close_price, 2),
                "volume": random.uniform(10000, 50000),
                "turnover": random.uniform(1000000, 5000000)
            })
            
            base_price = close_price
            current_time += tf_delta
        
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def _dict_list_to_dataframe(self, data: List[Dict]) -> pd.DataFrame:
        """将字典列表转换为 DataFrame"""
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        return df
    
    def _filter_by_date(
        self,
        df: pd.DataFrame,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """按日期范围过滤 DataFrame"""
        if df.empty:
            return df
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        mask = (df.index >= start) & (df.index <= end)
        return df[mask]
    
    # ==================== 缓存管理 ====================
    
    async def cache_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame
    ) -> None:
        """
        缓存 OHLCV 数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            data: DataFrame
        """
        # 转换为字典列表
        data_dict = data.to_dict('records')
        
        # 存入 Redis
        await self._redis.cache_ohlcv(symbol, timeframe, data_dict)
        
        # 存入内存
        self._backtest_cache[f"{symbol}:{timeframe}"] = data.copy()
    
    async def get_cached_ohlcv(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[pd.DataFrame]:
        """
        获取缓存的 OHLCV 数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            
        Returns:
            DataFrame 或 None
        """
        # 检查内存缓存
        key = f"{symbol}:{timeframe}"
        if key in self._backtest_cache:
            return self._backtest_cache[key]
        
        # 检查 Redis 缓存
        redis_cache = await self._redis.get_cached_ohlcv(symbol, timeframe)
        if redis_cache:
            df = self._dict_list_to_dataframe(redis_cache)
            self._backtest_cache[key] = df
            return df
        
        return None
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self._backtest_cache.clear()
        print("[DataService] 缓存已清空")
    
    # ==================== 统计与监控 ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取服务统计
        
        Returns:
            统计信息
        """
        return {
            "running": self._running,
            "tick_count": self._tick_count,
            "ohlcv_count": self._ohlcv_count,
            "cache_size": len(self._backtest_cache),
            "redis_config": {
                "host": self.config.redis.host,
                "port": self.config.redis.port,
                "key_prefix": self.config.redis.key_prefix
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查
        
        Returns:
            健康状态
        """
        status = {"status": "healthy", "checks": {}}
        
        try:
            await self._redis.client.ping()
            status["checks"]["redis"] = "ok"
        except Exception as e:
            status["checks"]["redis"] = f"error: {e}"
            status["status"] = "unhealthy"
        
        return status


# ==================== 便捷函数 ====================

def create_data_service(
    redis_host: str = "localhost",
    key_prefix: str = "lott:"
) -> DataService:
    """
    创建 Data Service
    
    Returns:
        DataService 实例
    """
    config = DataServiceConfig(
        redis=RedisConfig(
            host=redis_host,
            port=6379,
            key_prefix=key_prefix
        )
    )
    return DataService(config)


def create_backtest_service(
    symbols: List[str] = None,
    timeframes: List[str] = None
) -> DataService:
    """
    创建回测专用服务
    
    Args:
        symbols: 默认合约列表
        timeframes: 默认时间周期列表
        
    Returns:
        DataService 实例
    """
    config = DataServiceConfig(
        backtest=BacktestConfig(
            default_symbols=symbols or ["IF2406", "IC2406"],
            default_timeframes=timeframes or ["1m", "5m", "1h"],
            preload_all=True
        )
    )
    return DataService(config)
