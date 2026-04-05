# data_service 子模块文档

## 模块概述

data_service 子模块是 Service 层的核心组件，提供实时数据分发、回测数据准备和缓存管理功能。

## 文件结构

```
data_service/
├── __init__.py           # 模块入口，导出公共接口
├── config.py             # 服务配置类
├── service.py            # 数据服务主类
├── redis_client.py       # Redis 客户端封装
├── datasource.py         # 数据源（CTP/SimNow/Generator）
└── README.md             # 本文档
```

## 核心组件说明

### 1. config.py（服务配置）

**类**: `RedisConfig`

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | str | "localhost" | Redis 主机 |
| `port` | int | 6379 | Redis 端口 |
| `db` | int | 0 | 数据库编号 |
| `password` | Optional[str] | None | 密码 |
| `key_prefix` | str | "lott:" | 键前缀 |
| `stream_max_len` | int | 10000 | Stream 最大消息数 |
| `cache_ttl_seconds` | int | 300 | 缓存 TTL |
| `heartbeat_interval` | int | 30 | 心跳间隔 |

**类**: `DataSourceConfig`

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `source_type` | str | "simulator" | 数据源类型 |
| `simnow_front` | str | "tcp://..." | SimNow 前置地址 |
| `ctp_front` | Optional[str] | None | CTP 前置地址 |
| `ctp_broker` | str | "9999" | Broker ID |
| `symbols` | List[str] | ["IF2406", ...] | 订阅合约 |
| `timeframes` | List[str] | ["1m", "5m", ...] | 时间周期 |

**类**: `BacktestConfig`

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `data_source` | str | "redis" | 数据源 |
| `cache_ohlcv` | bool | True | 是否缓存 OHLCV |
| `cache_dir` | str | "~/LOTT/.cache/ohlcv" | 缓存目录 |
| `default_symbols` | List[str] | [...] | 默认合约 |
| `default_timeframes` | List[str] | [...] | 默认时间周期 |
| `default_start_date` | str | "2024-01-01" | 默认开始日期 |
| `default_end_date` | str | "2024-12-31" | 默认结束日期 |
| `preload_all` | bool | False | 预加载所有数据 |
| `batch_size` | int | 10000 | 批量加载大小 |

**类**: `DataServiceConfig`

```python
@dataclass
class DataServiceConfig:
    redis: RedisConfig = field(default_factory=RedisConfig)
    data_source: DataSourceConfig = field(default_factory=DataSourceConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    service_name: str = "lott-dataservice"
    log_level: str = "INFO"
```

### 2. service.py（数据服务主类）

**类**: `DataService`

**功能**: 统一数据访问接口

**主要方法**:

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `initialize()` | 初始化服务 | None |
| `start()` | 启动服务 | None |
| `stop()` | 停止服务 | None |
| `publish_ohlcv(symbol, exchange, timeframe, data)` | 发布 OHLCV 数据 | None |
| `subscribe_ohlcv(symbol, timeframe, callback)` | 订阅 OHLCV 数据 | None |
| `publish_tick(symbol, exchange, data)` | 发布 Tick 数据 | None |
| `subscribe_tick(symbol, callback)` | 订阅 Tick 数据 | None |
| `prepare_backtest_data(request)` | 准备回测数据 | BacktestResponse |
| `cache_ohlcv(symbol, timeframe, data)` | 缓存 OHLCV 数据 | None |
| `get_cached_ohlcv(symbol, timeframe)` | 获取缓存数据 | pd.DataFrame |
| `clear_cache()` | 清空缓存 | None |
| `get_stats()` | 获取服务统计 | Dict |
| `health_check()` | 健康检查 | Dict |

**数据结构**:

```python
@dataclass
class OHLCVData:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float = 0.0

@dataclass
class BacktestRequest:
    symbols: List[str]
    timeframes: List[str]
    start_date: str
    end_date: str
    preload: bool = True
    as_dataframe: bool = True

@dataclass
class BacktestResponse:
    success: bool
    data: Union[Dict, Any] = None
    error: str = None
    metadata: Dict = None
```

### 3. redis_client.py（Redis 客户端）

**类**: `RedisClient`

**功能**: Redis 连接和操作封装

**主要方法**:

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `connect()` | 建立连接 | None |
| `disconnect()` | 断开连接 | None |
| `publish(channel, message)` | 发布消息 | None |
| `subscribe(channel, callback)` | 订阅频道 | None |
| `set(key, value, ttl)` | 设置键值 | None |
| `get(key)` | 获取值 | Any |
| `delete(key)` | 删除键 | None |
| `xadd(stream, data)` | 添加 Stream 消息 | str |
| `xread(streams, count, block)` | 读取 Stream 消息 | List |

### 4. datasource.py（数据源）

**类**: `CTPDataSource`

**功能**: CTP 实时数据源

**主要方法**:

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `connect()` | 连接数据源 | bool |
| `disconnect()` | 断开连接 | None |
| `subscribe(symbols, timeframes)` | 订阅合约 | None |
| `unsubscribe()` | 取消订阅 | None |

**类**: `SimNowDataSource`

**功能**: SimNow 模拟环境数据源（继承自 CTPDataSource）

**类**: `OHLCVGenerator`

**功能**: OHLCV 数据生成器（用于回测）

**主要方法**:

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `generate(symbol, timeframe, start_date, end_date, base_price)` | 生成数据 | pd.DataFrame |

## 使用示例

### 示例 1: 启动数据服务

```python
from Service.data_service import DataService, DataServiceConfig

# 创建服务
config = DataServiceConfig()
service = DataService(config)

# 初始化并启动
await service.initialize()
await service.start()

# 健康检查
health = await service.health_check()
print(health)

# 停止服务
await service.stop()
```

### 示例 2: 准备回测数据

```python
from Service.data_service import DataService, BacktestRequest

service = DataService()
await service.initialize()

# 准备回测数据
request = BacktestRequest(
    symbols=["IF2406", "IC2406"],
    timeframes=["1m", "5m"],
    start_date="2024-01-01",
    end_date="2024-06-30"
)
response = await service.prepare_backtest_data(request)

if response.success:
    for symbol, data in response.data.items():
        print(f"{symbol}: {len(data['1m'])} records")
```

### 示例 3: 订阅实时数据

```python
async def on_tick(msg):
    print(f"Tick: {msg.symbol} @ {msg.last_price}")

await service.subscribe_tick("IF2406", on_tick)
```

## 技术框架

- **Python 版本**: 3.8+
- **核心依赖**:
  - redis >= 4.0.0
  - asyncio (内置)
  - pandas >= 1.3.0

## 对外接口

```python
from Service.data_service import (
    # 服务类
    DataService,                # 数据服务主类
    DataServiceConfig,          # 服务配置
    
    # 配置类
    RedisConfig,                # Redis 配置
    DataSourceConfig,           # 数据源配置
    BacktestConfig,             # 回测配置
    
    # 数据结构
    BacktestRequest,            # 回测请求
    BacktestResponse,           # 回测响应
    OHLCVData,                  # OHLCV 数据结构
    
    # 数据源
    CTPDataSource,              # CTP 数据源
    SimNowDataSource,           # SimNow 数据源
    OHLCVGenerator,             # OHLCV 生成器
    
    # 工厂函数
    create_data_service,        # 创建数据服务
    create_backtest_service,    # 创建回测服务
)
```

## 服务架构

```
┌─────────────────────────────────────────────────────┐
│                   DataService                        │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  Pub/Sub    │  │   Cache     │  │  Backtest   │  │
│  │  实时分发    │  │   缓存管理   │  │  数据准备   │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
├─────────────────────────────────────────────────────┤
│                    Redis Client                      │
├─────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐                   │
│  │ CTP/SimNow  │  │  Generator  │                   │
│  │  数据源     │  │  数据生成    │                   │
│  └─────────────┘  └─────────────┘                   │
└─────────────────────────────────────────────────────┘
```

## 注意事项

1. **异步操作**: 所有 I/O 操作都是异步的，需要使用 `await`
2. **Redis 依赖**: 确保 Redis 服务已启动
3. **时区处理**: 所有时间默认使用 UTC
4. **资源释放**: 使用完毕后调用 `stop()` 释放资源