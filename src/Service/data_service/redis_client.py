"""
Redis Client - Redis 消息队列客户端

功能:
- Pub/Sub 发布订阅 (实时数据分发)
- Stream 消息队列 (持久化消息)
- 缓存管理 (热点数据)
"""

import asyncio
import json
import logging
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from .config import RedisConfig


@dataclass
class OHLCVMessage:
    """OHLCV 消息 (回测主要数据)"""
    symbol: str
    exchange: str
    timestamp: datetime
    timeframe: str
    
    # OHLCV 数据
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    turnover: float = 0.0
    
    # 元数据
    source: str = "redis"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "open": self.open_price,
            "high": self.high_price,
            "low": self.low_price,
            "close": self.close_price,
            "volume": self.volume,
            "turnover": self.turnover,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OHLCVMessage":
        """从字典创建"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(
            symbol=data['symbol'],
            exchange=data['exchange'],
            timestamp=data['timestamp'],
            timeframe=data['timeframe'],
            open_price=data['open'],
            high_price=data['high'],
            low_price=data['low'],
            close_price=data['close'],
            volume=data['volume'],
            turnover=data.get('turnover', 0),
            source=data.get('source', 'redis')
        )
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, data: str) -> "OHLCVMessage":
        """从 JSON 创建"""
        return cls.from_dict(json.loads(data))


@dataclass  
class TickMessage:
    """Tick 消息 (实时数据)"""
    symbol: str
    exchange: str
    timestamp: datetime
    last_price: float
    last_volume: float
    bid_price: float
    bid_volume: float
    ask_price: float
    ask_volume: float
    source: str = "ctp"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "timestamp": self.timestamp.isoformat(),
            "last_price": self.last_price,
            "last_volume": self.last_volume,
            "bid_price": self.bid_price,
            "bid_volume": self.bid_volume,
            "ask_price": self.ask_price,
            "ask_volume": self.ask_volume,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TickMessage":
        """从字典创建"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, data: str) -> "TickMessage":
        """从 JSON 创建"""
        return cls.from_dict(json.loads(data))


class RedisClient:
    """
    Redis 客户端
    
    功能:
    - Pub/Sub: 实时数据分发
    - Stream: 消息持久化
    - Cache: 热点数据缓存
    """
    
    def __init__(self, config: RedisConfig = None):
        """
        初始化
        
        Args:
            config: Redis 配置
        """
        self.config = config or RedisConfig()
        self._client: Optional[Redis] = None
        self._pubsub: Optional[PubSub] = None
        self._subscriptions: Dict[str, List[Callable]] = {}
    
    # ==================== 连接管理 ====================
    
    async def connect(self) -> None:
        """建立连接"""
        self._client = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.db,
            password=self.config.password or None,
            decode_responses=True
        )
        print(f"[Redis] 已连接 {self.config.host}:{self.config.port}")
    
    async def close(self) -> None:
        """关闭连接"""
        if self._pubsub:
            await self._pubsub.close()
            self._pubsub = None
        
        if self._client:
            await self._client.close()
            self._client = None
            print("[Redis] 连接已关闭")
    
    @property
    def client(self) -> Redis:
        """获取客户端"""
        if self._client is None:
            raise RuntimeError("Redis 未连接")
        return self._client
    
    # ==================== 键管理 ====================
    
    def _key(self, key: str) -> str:
        """带前缀的键名"""
        return f"{self.config.key_prefix}{key}"
    
    # ==================== 缓存操作 ====================
    
    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl: int = None
    ) -> None:
        """
        设置缓存
        
        Args:
            key: 键名
            value: 值 (会自动 JSON 序列化)
            ttl: 过期时间 (秒)
        """
        full_key = self._key(key)
        serialized = json.dumps(value, default=str)
        
        ttl = ttl or self.config.cache_ttl_seconds
        await self.client.setex(full_key, ttl, serialized)
    
    async def cache_get(self, key: str) -> Any:
        """
        获取缓存
        
        Args:
            key: 键名
            
        Returns:
            值 或 None
        """
        full_key = self._key(key)
        value = await self.client.get(full_key)
        
        if value:
            return json.loads(value)
        return None
    
    async def cache_delete(self, key: str) -> None:
        """删除缓存"""
        full_key = self._key(key)
        await self.client.delete(full_key)
    
    # ==================== OHLCV 缓存 ====================
    
    async def cache_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        data: List[Dict],
        ttl: int = None
    ) -> None:
        """
        缓存 OHLCV 数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            data: OHLCV 数据列表
            ttl: 过期时间
        """
        key = f"ohlcv:{symbol}:{timeframe}"
        await self.cache_set(key, data, ttl)
    
    async def get_cached_ohlcv(
        self,
        symbol: str,
        timeframe: str
    ) -> Optional[List[Dict]]:
        """
        获取缓存的 OHLCV 数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            
        Returns:
            OHLCV 数据 或 None
        """
        key = f"ohlcv:{symbol}:{timeframe}"
        return await self.cache_get(key)
    
    # ==================== Pub/Sub 实时分发 ====================
    
    async def publish_ohlcv(self, msg: OHLCVMessage) -> int:
        """
        发布 OHLCV 消息
        
        Args:
            msg: OHLCVMessage
            
        Returns:
            订阅者数量
        """
        channel = self._key(f"pub:ohlcv:{msg.symbol}:{msg.timeframe}")
        return await self.client.publish(channel, msg.to_json())
    
    async def publish_tick(self, msg: TickMessage) -> int:
        """
        发布 Tick 消息
        
        Args:
            msg: TickMessage
            
        Returns:
            订阅者数量
        """
        channel = self._key(f"pub:tick:{msg.symbol}")
        return await self.client.publish(channel, msg.to_json())
    
    async def subscribe_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        callback: Callable[[OHLCVMessage], None]
    ) -> None:
        """
        订阅 OHLCV 数据
        
        Args:
            symbol: 合约代码
            timeframe: 时间周期
            callback: 回调函数
        """
        channel = self._key(f"pub:ohlcv:{symbol}:{timeframe}")
        await self._subscribe(channel, callback)
    
    async def subscribe_tick(
        self,
        symbol: str,
        callback: Callable[[TickMessage], None]
    ) -> None:
        """
        订阅 Tick 数据
        
        Args:
            symbol: 合约代码
            callback: 回调函数
        """
        channel = self._key(f"pub:tick:{symbol}")
        await self._subscribe(channel, callback)
    
    async def _subscribe(
        self,
        channel: str,
        callback: Callable
    ) -> None:
        """内部订阅方法"""
        if self._pubsub is None:
            self._pubsub = self.client.pubsub()
        
        await self._pubsub.subscribe(channel)
        
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(callback)
        
        print(f"[Redis] 已订阅: {channel}")
    
    async def unsubscribe(self, channel: str) -> None:
        """取消订阅"""
        if self._pubsub and channel in self._subscriptions:
            await self._pubsub.unsubscribe(channel)
            del self._subscriptions[channel]
    
    async def start_listening(self) -> None:
        """开始监听消息"""
        if self._pubsub is None:
            raise RuntimeError("请先订阅至少一个频道")
        
        print("[Redis] 开始监听消息...")
        
        async for message in self._pubsub.listen():
            if message["type"] == "message":
                channel = message["channel"]
                
                try:
                    # 尝试解析为 OHLCV
                    try:
                        msg = OHLCVMessage.from_json(message["data"])
                        msg_type = "ohlcv"
                    except:
                        # 解析为 Tick
                        msg = TickMessage.from_json(message["data"])
                        msg_type = "tick"
                    
                    # 调用回调
                    if channel in self._subscriptions:
                        for callback in self._subscriptions[channel]:
                            await callback(msg)
                            
                except Exception as e:
                    logging.error(f"[Redis] 处理消息失败: {e}")
    
    # ==================== Stream 消息队列 ====================
    
    async def stream_add(
        self,
        stream: str,
        message: Dict[str, Any],
        max_len: int = None
    ) -> str:
        """
        添加消息到 Stream
        
        Args:
            stream: Stream 名称
            message: 消息字典
            max_len: 最大长度
            
        Returns:
            消息 ID
        """
        full_stream = self._key(f"stream:{stream}")
        
        kwargs = {"*": message}
        if max_len:
            kwargs["MAXLEN"] = max_len
        elif self.config.stream_max_len:
            kwargs["MAXLEN"] = self.config.stream_max_len
        
        return await self.client.xadd(full_stream, kwargs)
    
    async def stream_add_ohlcv(
        self,
        symbol: str,
        data: Dict[str, Any]
    ) -> str:
        """
        添加 OHLCV 到 Stream
        
        Args:
            symbol: 合约代码
            data: OHLCV 数据
            
        Returns:
            消息 ID
        """
        return await self.stream_add(
            f"ohlcv:{symbol}",
            data,
            max_len=100000  # OHLCV 数据保留更多
        )
    
    async def stream_read_group(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block: int = None
    ) -> List[Dict[str, Any]]:
        """
        从消费者组读取消息
        
        Args:
            stream: Stream 名称
            group_name: 消费者组名
            consumer_name: 消费者名
            count: 数量
            block: 阻塞时间 (毫秒)
            
        Returns:
            消息列表
        """
        full_stream = self._key(f"stream:{stream}")
        group_key = self._key(f"group:{group_name}")
        
        try:
            if block:
                messages = await self.client.xreadgroup(
                    group_key, consumer_name,
                    {full_stream: ">"},
                    count=count, block=block
                )
            else:
                messages = await self.client.xreadgroup(
                    group_key, consumer_name,
                    {full_stream: ">"},
                    count=count
                )
            
            result = []
            for stream_name, msg_list in messages:
                for msg_id, data in msg_list:
                    result.append({
                        "id": msg_id,
                        "data": data
                    })
            
            return result
            
        except Exception as e:
            if "NOGROUP" in str(e):
                # 创建消费者组
                await self.stream_create_group(stream, group_name)
                return []
            raise
    
    async def stream_create_group(
        self,
        stream: str,
        group_name: str,
        start_id: str = "0"
    ) -> None:
        """创建消费者组"""
        full_stream = self._key(f"stream:{stream}")
        
        try:
            await self.client.xgroup_create(
                full_stream, group_name,
                id=start_id, mkstream=True
            )
            print(f"[Redis] 消费者组 {group_name} 已创建")
        except Exception as e:
            if "BUSYGROUP" not in str(e):
                raise
    
    async def stream_ack(
        self,
        stream: str,
        group_name: str,
        msg_id: str
    ) -> int:
        """确认消息"""
        full_stream = self._key(f"stream:{stream}")
        group_key = self._key(f"group:{group_name}")
        
        return await self.client.xack(full_stream, group_key, msg_id)
    
    # ==================== 心跳与状态 ====================
    
    async def set_heartbeat(
        self,
        service: str,
        status: Dict[str, Any]
    ) -> None:
        """
        设置服务心跳
        
        Args:
            service: 服务名
            status: 状态信息
        """
        status['timestamp'] = datetime.now().isoformat()
        key = f"heartbeat:{service}"
        await self.cache_set(key, status, ttl=60)
    
    async def get_heartbeat(self, service: str) -> Optional[Dict[str, Any]]:
        """获取服务心跳"""
        key = f"heartbeat:{service}"
        return await self.cache_get(key)


# ==================== 工厂函数 ====================

def create_redis_client(
    host: str = "localhost",
    port: int = 6379,
    key_prefix: str = "lott:"
) -> RedisClient:
    """
    创建 Redis 客户端
    
    Returns:
        RedisClient 实例
    """
    config = RedisConfig(
        host=host,
        port=port,
        key_prefix=key_prefix
    )
    return RedisClient(config)
