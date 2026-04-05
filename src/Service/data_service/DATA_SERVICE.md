# Data Service Layer 设计方案

**创建时间:** 2026-02-18
**职责:** 实时数据分发 + 回测数据准备
**依赖:** Redis (由专业团队提供)

---

## 📐 架构定位

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOTT 整体架构                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐    ┌─────────────────────┐          │
│  │   Data Service     │    │    Data Layer      │          │
│  │   Layer           │    │    (数据库层)       │          │
│  │                   │    │                    │          │
│  │ • 实时数据分发     │    │ • TimescaleDB      │          │
│  │ • 回测数据准备     │    │ • PostgreSQL       │          │
│  │ • 缓存管理         │    │ (由另一团队负责)    │          │
│  └─────────────────────┘    └─────────────────────┘          │
│           │                          │                        │
│           └──────────┬───────────────┘                        │
│                      ▼                                        │
│              ┌─────────────────────┐                          │
│              │      Redis          │                          │
│              │  (消息队列 + 缓存)   │                          │
│              └─────────────────────┘                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 目录结构

```
~/LOTT/data_service/
├── __init__.py              # 模块入口
├── config.py               # 配置 (Redis/DataSource/Backtest)
├── redis_client.py         # Redis 客户端 (Pub/Sub + Stream + Cache)
├── service.py              # DataService 核心服务
├── datasource.py           # 数据源模拟
├── examples/
│   └── usage.py           # 使用示例
└── DATA_SERVICE.md         # 本文档
```

---

## 🎯 核心职责

### 1. 实时数据分发 (Pub/Sub)

```
# 频道设计
lott:pub:ohlcv:{symbol}:{timeframe}   # OHLCV 实时推送
lott:pub:tick:{symbol}                # Tick 实时推送

# 使用方式
await service.subscribe_ohlcv("IF2406", "1m", callback)
await service.publish_ohlcv(symbol, exchange, timeframe, data)
```

### 2. 回测数据准备 (核心功能)

```python
# 请求格式
request = BacktestRequest(
    symbols=["IF2406", "IC2406"],
    timeframes=["1m", "5m", "1h"],
    start_date="2024-01-01",
    end_date="2024-01-31",
    preload=True  # 预加载到内存
)

# 返回格式
response = await service.prepare_backtest_data(request)
# response.data = {
#     "IF2406": {
#         "1m": DataFrame,
#         "5m": DataFrame,
#         "1h": DataFrame
#     },
#     "IC2406": {...}
# }
```

### 3. 数据缓存

```
# 缓存键设计
lott:ohlcv:{symbol}:{timeframe}       # OHLCV 数据缓存
lott:market:{symbol}                   # 最新价格缓存
lott:heartbeat:{service}               # 心跳缓存

# 缓存策略
- OHLCV: 24 小时 TTL
- 市场数据: 5 分钟 TTL
- 心跳: 60 秒 TTL
```

---

## 🔄 与 UniBacktest 集成

```
┌─────────────────────────────────────────────────────────────────┐
│                    UniBacktest 回测流程                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 创建回测请求                                                 │
│     request = BacktestRequest(...)                              │
│                                                                 │
│  2. 调用 DataService 准备数据                                    │
│     response = await data_service.prepare_backtest_data(request) │
│                                                                 │
│  3. 获取 OHLCV DataFrame                                        │
│     df = response.data["IF2406"]["1m"]                          │
│                                                                 │
│  4. 传递给回测引擎                                              │
│     engine.set_data(df)                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**示例:**

```python
from data_service import create_backtest_service, BacktestRequest
from backtest import BacktestLayer

# 1. 获取回测数据
data_service = create_backtest_service()
await data_service.initialize()

request = BacktestRequest(
    symbols=["IF2406"],
    timeframes=["1m"],
    start_date="2024-01-01",
    end_date="2024-06-30"
)
response = await data_service.prepare_backtest_data(request)

# 2. 创建回测
backtest = BacktestLayer()
backtest.set_data(response.data["IF2406"]["1m"])

# 3. 运行回测
result = backtest.run()
```

---

## 📊 Redis Stream (可选)

用于需要持久化的场景:

```
# Stream 设计
lott:stream:ohlcv:{symbol}      # OHLCV 消息流
lott:stream:tick:{symbol}       # Tick 消息流

# 消费者组
lott:group:strategies           # 策略消费组
lott:group:backtest             # 回测消费组
```

---

## 🔧 配置

### Redis 配置

```python
RedisConfig(
    host="localhost",
    port=6379,
    key_prefix="lott:",        # 键前缀
    stream_max_len=10000,       # Stream 最大长度
    cache_ttl_seconds=300,      # 缓存 TTL
    heartbeat_interval=30       # 心跳间隔
)
```

### 回测配置

```python
BacktestConfig(
    data_source="redis",        # 数据源
    cache_ohlcv=True,          # 是否缓存
    cache_dir="~/.cache/ohlcv", # 缓存目录
    preload_all=True,          # 预加载
    batch_size=10000           # 批量大小
)
```

---

## ⚡ 性能

| 操作 | 预期性能 | 说明 |
|-----|---------|------|
| DataFrame 获取 | < 100ms | Redis 缓存命中 |
| 首次数据生成 | 1-5s | 根据数据量 |
| 缓存查询 | < 10ms | 内存缓存 |
| Pub/Sub 延迟 | < 50ms | 实时分发 |

---

## 📝 使用示例

### 1. 初始化服务

```python
from data_service import create_data_service

service = create_data_service(
    redis_host="localhost",
    key_prefix="lott:"
)

await service.initialize()
await service.start()
```

### 2. 准备回测数据

```python
from data_service import BacktestRequest

request = BacktestRequest(
    symbols=["IF2406", "IC2406"],
    timeframes=["1m", "5m", "1h"],
    start_date="2024-01-01",
    end_date="2024-12-31",
    preload=True
)

response = await service.prepare_backtest_data(request)
```

### 3. 实时数据订阅

```python
async def on_tick(tick):
    print(f"{tick.symbol}: {tick.last_price}")

async def on_ohlcv(ohlcv):
    print(f"{ohlcv.symbol} {ohlcv.timeframe}: {ohlcv.close_price}")

await service.subscribe_tick("IF2406", on_tick)
await service.subscribe_ohlcv("IF2406", "1m", on_ohlcv)
```

### 4. 获取统计

```python
stats = service.get_stats()
# {
#     "running": True,
#     "tick_count": 1000,
#     "ohlcv_count": 500,
#     "cache_size": 10
# }

health = await service.health_check()
# {"status": "healthy", "checks": {"redis": "ok"}}
```

---

## 🚀 下一步

1. **安装依赖**: `pip install redis pandas`
2. **启动 Redis**: 确保 Redis 服务运行
3. **运行示例**: `python examples/usage.py`
4. **集成回测**: 与 UniBacktest 集成
