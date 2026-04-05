# TimescaleDB 配置说明文档

## 🏗️ 混合架构设计

TimescaleDB 是实现**混合架构**的核心组件，支持长表存储和物化视图：

```
┌─────────────────────────────────────────────────────────────┐
│                   源数据层（原始数据）                        │
│  • 保留原始行情完整性                                         │
│  • CSV/JSON/Excel 原始文件                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓ ETL 导入
┌─────────────────────────────────────────────────────────────┐
│              主数据层（TimescaleDB 长表）⭐                   │
│  • 长表格式存储（symbol, time, value）                      │
│  • TimescaleDB 超表（按时间自动分区）                        │
│  • 灵活应对品种变化                                           │
└─────────────────────────────────────────────────────────────┘
                              ↓ 连续聚合
┌─────────────────────────────────────────────────────────────┐
│              分析层（物化视图/宽表）                          │
│  • 按需生成分析宽表                                           │
│  • 自动刷新，高性能查询                                       │
│  • 支持回测和分析场景                                         │
└─────────────────────────────────────────────────────────────┘
```

### 架构优势

| 优势 | 说明 |
|------|------|
| **灵活性** | 长表可以灵活应对品种变化，新增品种无需修改表结构 |
| **可追溯** | 源数据保留，方便重新处理和数据校验 |
| **性能** | 分析时用宽表/物化视图，查询速度快 |
| **解耦** | 存储与分析分离，各层独立优化 |

## 目录
1. [配置文件结构](#配置文件结构)
2. [配置项详解](#配置项详解)
3. [YAML 配置示例](#yaml-配置示例)
4. [Python 使用方式](#python-使用方式)
5. [Docker Desktop 配置](#docker-desktop-配置)
6. [表结构说明](#表结构说明)
7. [物化视图（分析宽表）](#物化视图分析宽表)

---

## 配置文件结构

```
LOTT/src/Data/DataFeed/TimescaleDB/
├── config.py                 # Python 配置类（连接参数在此）
├── client.py                 # TimescaleDB 客户端
├── tables.py                 # 表结构定义
├── json_import.py            # JSON 数据导入
├── examples.py               # 使用示例
└── README.md                # 本文档
```

---

## 配置项详解

### 1. 连接配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `host` | string | `localhost` | 数据库地址 |
| `port` | int | `5432` | 数据库端口 |
| `database` | string | `timescaledb` | 数据库名 |
| `username` | string | `admin` | 用户名 |
| `password` | string | `admin123` | 密码 |

### 2. 连接池配置

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `pool.min_connections` | int | `1` | 最小连接数 |
| `pool.max_connections` | int | `10` | 最大连接数 |
| `pool.timeout` | int | `30` | 连接超时(秒) |

### 3. 表结构配置

```yaml
tables:
  ohlcv:
    name: ohlcv_data              # 表名
    primary_key: [symbol, timeframe, time]  # 主键
    time_column: time             # 时间列（用于分区）
    indexes:                     # 索引
      - columns: [symbol, timeframe]
```

### 4. 数据保留策略

```yaml
retention:
  enabled: true                  # 启用压缩
  compression:
    after_days: 30               # 30天后压缩
    chunk_interval: 1 week      # Chunk间隔
  policies:
    ohlcv:
      drop_after: 2 years       # 保留2年
```

### 5. 批量写入配置

```yaml
write:
  batch:
    size: 1000                   # 每批1000条
    max_wait_ms: 1000           # 最多等待1秒
  retry:
    max_attempts: 3             # 最多重试3次
    backoff: 1                  # 重试间隔(秒)
```

---

## YAML 配置示例

### 开发环境配置 (development.yaml)

```yaml
# 开发环境配置
host: localhost
port: 5432
database: timescaledb
username: admin
password: admin123

pool:
  min_connections: 1
  max_connections: 5
  timeout: 30

write:
  batch:
    size: 500
    max_wait_ms: 500

debug: true
```

### 生产环境配置 (production.yaml)

```yaml
# 生产环境配置
host: timescaledb.internal
port: 5432
database: lott_production
username: lott_user
password: <strong-password>

pool:
  min_connections: 5
  max_connections: 20
  timeout: 60

write:
  batch:
    size: 2000
    max_wait_ms: 2000
  retry:
    max_attempts: 5
    backoff: 2

retention:
  enabled: true
  compression:
    after_days: 7
    chunk_interval: 1 day

debug: false
```

---

## Python 使用方式

### 1. 基本使用

```python
from DataFeed.TimescaleDB import client
from DataFeed.TimescaleDB.config import TimescaleDBConfig

# 使用配置（默认：postgres/1211/lott@localhost:5432）
cfg = TimescaleDBConfig()

# 创建客户端
ts_client = client.TimescaleDBClient(cfg)

# 连接
if ts_client.connect():
    # 创建表
    ts_client.create_tables()
    
    # ... 使用客户端 ...
    
    # 断开
    ts_client.disconnect()
```

### 2. 使用便捷函数

```python
from DataSource.TimescaleDB import client

# 初始化（自动加载配置）
if client.initialize():
    print("TimescaleDB 初始化成功")
    
    # 获取统计信息
    stats = client.get_client().get_stats()
    print(f"OHLCV数据: {stats.get('ohlcv_count', 0)} 条")
    
    # 关闭
    client.close()
```

### 3. 插入 OHLCV 数据

```python
from DataSource.TimescaleDB import client
from datetime import datetime
from DataSource.TimescaleDB.client import OHLCVData

# 获取客户端
ts = client.get_client()

# 准备数据
data = [
    OHLCVData(
        symbol="IF2406",
        exchange="CFFEX",
        timeframe="1m",
        time=datetime(2024, 1, 1, 9, 30),
        open=3650.0,
        high=3655.0,
        low=3648.0,
        close=3652.0,
        volume=10000,
        turnover=36520000
    ),
    # ... 更多数据
]

# 批量插入
ts.insert_ohlcv(data)
```

### 4. 查询数据

```python
from DataSource.TimescaleDB import client
from datetime import datetime

ts = client.get_client()

# 查询
data = ts.query_ohlcv(
    symbol="IF2406",
    timeframe="1m",
    start_time=datetime(2024, 1, 1),
    end_time=datetime(2024, 1, 2)
)

for ohlcv in data:
    print(f"{ohlcv.time}: {ohlcv.open} - {ohlcv.close}")
```

---

## Docker Desktop 配置

### 1. Docker Desktop 容器信息

你已经使用 Docker Desktop 安装了 `timescale/timescaledb:latest-pg18` 镜像。

**默认连接参数：**
| 配置项 | 值 |
|--------|-----|
| 主机地址 | `localhost` 或 `127.0.0.1` |
| 端口 | `5432` |
| 数据库名 | `timescaledb` |
| 用户名 | `admin` |
| 密码 | `admin123` |

### 2. 验证连接

```bash
# 使用 Docker Desktop 的 CLI 或 PowerShell
docker ps  # 查看运行中的容器

# 测试连接
docker exec -it <container_name> psql -U admin -d timescaledb
```

### 3. 修改配置

如果需要修改数据库名、用户名或密码，修改 YAML 配置文件的对应字段：

```yaml
host: localhost
port: 5432
database: timescaledb    # 修改数据库名
username: admin          # 修改用户名
password: admin123       # 修改密码
```

---

## 表结构说明

### 1. OHLCV 数据表 (ohlcv_data)

存储 K线数据（分钟/小时/日线）

| 列名 | 类型 | 说明 |
|------|------|------|
| symbol | TEXT | 合约代码 (如 IF2406) |
| exchange | TEXT | 交易所 (如 CFFEX) |
| timeframe | TEXT | 时间周期 (1m, 5m, 1h, 1d) |
| time | TIMESTAMPTZ | K线时间 |
| open | DOUBLE | 开盘价 |
| high | DOUBLE | 最高价 |
| low | DOUBLE | 最低价 |
| close | DOUBLE | 收盘价 |
| volume | DOUBLE | 成交量 |
| turnover | DOUBLE | 成交额 |
| source | TEXT | 数据来源 |

### 2. Tick 数据表 (tick_data)

存储逐笔数据

| 列名 | 类型 | 说明 |
|------|------|------|
| symbol | TEXT | 合约代码 |
| exchange | TEXT | 交易所 |
| time | TIMESTAMPTZ | 时间 |
| last_price | DOUBLE | 最新价 |
| last_volume | DOUBLE | 最新成交量 |
| bid_price | DOUBLE | 买价 |
| bid_volume | DOUBLE | 买量 |
| ask_price | DOUBLE | 卖价 |
| ask_volume | DOUBLE | 卖量 |

### 3. 策略信号表 (strategy_signals)

存储策略交易信号

| 列名 | 类型 | 说明 |
|------|------|------|
| strategy_id | TEXT | 策略ID |
| symbol | TEXT | 合约代码 |
| timestamp | TIMESTAMPTZ | 信号时间 |
| signal_type | TEXT | 信号类型 (buy/sell) |
| signal_value | DOUBLE | 信号值 |
| price | DOUBLE | 价格 |
| metadata | JSONB | 附加信息 |

---

## 故障排查

### 1. 连接失败

```python
# 检查客户端状态
ts = client.get_client()
print(ts.is_connected())

# 查看健康状态
health = ts.health_check()
print(health)
```

### 2. 查看日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
# 重新操作，会输出详细日志
```

### 3. Docker 相关

```bash
# 查看容器日志
docker logs <container_name>

# 重启容器
docker restart <container_name>

# 进入容器
docker exec -it <container_name> bash
```

---

## 物化视图（分析宽表）

### 概念说明

物化视图（Materialized View）是 TimescaleDB 的**连续聚合（Continuous Aggregate）**功能，可以：
- 自动从长表生成分析宽表
- 定时刷新，保持数据同步
- 提供高性能查询，适合分析和回测场景

### 长表 vs 宽表

| 特性 | 长表（主数据层） | 宽表（分析层） |
|------|------------------|----------------|
| **结构** | (symbol, time, open, high, low, close, volume) | (time, cu_close, al_close, au_close, ...) |
| **优点** | 灵活、易扩展、存储高效 | 查询快、易分析、适合回测 |
| **场景** | 数据存储、ETL、实时写入 | 数据分析、回测、报表 |
| **品种变化** | 无需修改表结构 | 需要重建视图 |

### 创建物化视图

#### 1. 每日汇总宽表

```sql
-- 每日宽表（物化视图）
CREATE MATERIALIZED VIEW daily_summary
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS day,
    symbol,
    FIRST(open, time) as open,
    MAX(high) as high,
    MIN(low) as low,
    LAST(close, time) as close,
    SUM(volume) as volume
FROM ohlcv_data
GROUP BY day, symbol
WITH DATA;

-- 创建刷新策略（每小时刷新一次）
SELECT add_continuous_aggregate_policy('daily_summary', 
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

#### 2. 品种横向宽表

```sql
-- 品种收盘价宽表（横向展开）
CREATE MATERIALIZED VIEW daily_close_wide
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS trade_date,
    MAX(CASE WHEN symbol='CU0' THEN close END) as cu_close,
    MAX(CASE WHEN symbol='AL0' THEN close END) as al_close,
    MAX(CASE WHEN symbol='AU0' THEN close END) as au_close,
    MAX(CASE WHEN symbol='AG0' THEN close END) as ag_close,
    MAX(CASE WHEN symbol='ZN0' THEN close END) as zn_close,
    MAX(CASE WHEN symbol='PB0' THEN close END) as pb_close,
    MAX(CASE WHEN symbol='NI0' THEN close END) as ni_close,
    MAX(CASE WHEN symbol='SN0' THEN close END) as sn_close
FROM ohlcv_data
GROUP BY trade_date
WITH DATA;

-- 设置刷新策略
SELECT add_continuous_aggregate_policy('daily_close_wide',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

#### 3. 分钟级聚合宽表

```sql
-- 1分钟 → 5分钟 聚合
CREATE MATERIALIZED VIEW ohlcv_5min
WITH (timescaledb.continuous) AS
SELECT
    symbol,
    time_bucket('5 minutes', time) AS bucket,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM ohlcv_data
WHERE timeframe = '1m'
GROUP BY bucket, symbol
WITH DATA;

SELECT add_continuous_aggregate_policy('ohlcv_5min',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');
```

### 查询物化视图

```python
from Data.DataSource.TimescaleDB import client

ts = client.get_client()

# 查询宽表数据（适合分析）
results = ts.fetch_all("""
    SELECT trade_date, cu_close, al_close, au_close
    FROM daily_close_wide
    WHERE trade_date >= '2024-01-01'
    ORDER BY trade_date
""")

# 转换为 DataFrame 进行分析
import pandas as pd
df = pd.DataFrame(results)
df['cu_al_ratio'] = df['cu_close'] / df['al_close']
print(df.head())
```

### 物化视图管理

```sql
-- 查看所有物化视图
SELECT 
    view_name,
    view_owner,
    materialized_hypertable_name
FROM timescaledb_information.continuous_aggregates;

-- 查看刷新策略
SELECT * FROM timescaledb_information.jobs 
WHERE proc_name = 'policy_refresh_continuous_aggregate';

-- 手动刷新物化视图
CALL refresh_continuous_aggregate('daily_summary', NULL, NULL);

-- 删除刷新策略
SELECT remove_continuous_aggregate_policy('daily_summary');

-- 删除物化视图
DROP MATERIALIZED VIEW daily_summary;
```

### 新增品种后重建视图

当新增交易品种时，需要重建横向宽表物化视图：

```sql
-- 1. 删除旧视图
DROP MATERIALIZED VIEW IF EXISTS daily_close_wide;

-- 2. 重新创建（包含新品种）
CREATE MATERIALIZED VIEW daily_close_wide
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS trade_date,
    MAX(CASE WHEN symbol='CU0' THEN close END) as cu_close,
    MAX(CASE WHEN symbol='AL0' THEN close END) as al_close,
    -- ... 新增品种
    MAX(CASE WHEN symbol='NEW_SYMBOL' THEN close END) as new_close
FROM ohlcv_data
GROUP BY trade_date
WITH DATA;

-- 3. 重新设置刷新策略
SELECT add_continuous_aggregate_policy('daily_close_wide',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');
```

---

## 下一步

1. **验证 TimescaleDB 容器正在运行**（`docker ps` 查看）
2. **配置连接参数**（修改 `config.py` 或实例化 `TimescaleDBConfig()` 时传入）
3. **运行示例代码测试连接**：`python examples.py`
4. **根据实际需求创建物化视图**
5. **根据实际需求调整批量写入和保留策略参数**
