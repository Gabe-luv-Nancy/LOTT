# DataFeed 模块需求文档

**更新时间**: 2026-03-18

---

## 一、概述

DataFeed 模块负责从 **SimNow 接收实时 Tick 行情数据**，并将原始 Tick 数据直接写入 **TimescaleDB**。

> ⚠️ **职责边界说明（2026-03-19 澄清）**
> - DataFeed **只管 Tick 高频数据**（毫秒级实时行情）
> - 分钟线及以上的中频数据（1min / 5min / 日线）由 `DataSource` + `DatabaseManage` 模块负责
> - 两者完全独立，数据频率层次不同

**核心定位**：

- **实时性**: 毫秒级 Tick 数据接收与存储
- **原始数据**: 仅存储原始 Tick，不做 K 线合成
- **进程常驻**: 交易时段持续运行，支持断线重连

**职责边界**: DataFeed 只负责原始 Tick 数据接入和存储，K 线合成由 Service 层实现。

---

## 二、技术框架

| 组件     | 说明                                          |
| -------- | --------------------------------------------- |
| 核心框架 | vn.py 2.1.3 + vnpy_ctp                        |
| 数据源   | SimNow CTP (六交所仿真环境)                   |
| 通信协议 | **CTP API 私有协议 (TCP)**，非 WebSocket      |
| 时序数据库 | TimescaleDB                                 |
| 并发模型 | threading + Queue                             |

### SimNow 连接方式说明

SimNow 是六交所提供的 CTP 仿真环境，使用 **CTP API 私有协议** 进行通信：

- **协议类型**: CTP API 私有协议（基于 TCP 的二进制协议）
- **连接方式**: TCP 长连接
- **端口**: 行情服务器 10131，交易服务器 10130
- **官方文档**: [上期技术 CTP API 文档](https://www.sfit.com.cn/)

> 注意：CTP API 不是 WebSocket 协议，而是上期技术开发的私有二进制协议。

---

## 三、目录结构

```
DataFeed/
├── README.MD                   # 本文档
├── Gateway/                    # CTP 行情网关
│   ├── __init__.py
│   └── lott_gateway.py        # vn.py CTP 网关适配
├── Recorder/                   # 数据记录器
│   ├── __init__.py
│   ├── bar_collector.py       # Bar 数据收集
│   └── realtime_recorder.py   # 实时数据记录
└── TimescaleDB/               # TimescaleDB 工具集 ⭐
    ├── __init__.py            # 模块入口
    ├── config.py              # 配置管理（支持 YAML）
    ├── client.py              # 数据库客户端（OHLCV/Tick 操作）
    ├── tables.py              # 表结构管理（长表格式）
    ├── json_import.py         # JSON 数据导入工具
    ├── examples.py            # 使用示例
    ├── timescaledb_config.yaml # YAML 配置文件
    └── README.md              # TimescaleDB 详细文档
```

---

## 四、TimescaleDB 工具集

### 模块职责

| 模块 | 职责 | 说明 |
|------|------|------|
| `config.py` | 配置管理 | 支持 YAML 文件和环境变量 |
| `client.py` | 数据库客户端 | OHLCV/Tick 数据读写 |
| `tables.py` | 表结构管理 | 长表格式存储（symbol, time, value） |
| `json_import.py` | JSON 导入 | 批量导入 JSON 数据，支持去重 |
| `examples.py` | 使用示例 | 演示各种操作 |

### 快速开始

```python
from Data.DataFeed.TimescaleDB import (
    TimescaleDBConfig,
    initialize,
    get_client,
    close,
    TableCreator,
    JSONImport,
    import_json
)

# 1. 初始化连接
config = TimescaleDBConfig(
    host='localhost',
    port=5432,
    database='lott',
    username='postgres',
    password='yourpassword'
)

if initialize(config):
    # 2. 创建表
    creator = TableCreator()
    creator.create_all_tables()
    
    # 3. 导入 JSON 数据
    result = import_json('path/to/data.json')
    print(f"导入: {result.rows_imported} 行")
    
    close()
```

### 一行代码导入 JSON

```python
from Data.DataFeed.TimescaleDB import import_json

result = import_json(
    file_path='X:\\LOTT\\src\\Data\\DataSource\\_json\\data_in_use.json',
    batch_size=1000
)

print(f"导入成功: {result.rows_imported} 行")
```

### DbWrite 工具

`DbWrite` 负责将实时 Tick 数据写入 TimescaleDB：

```python
from Data.DataFeed.TimescaleDB import get_client
from datetime import datetime

client = get_client()

# 写入 Tick 数据
tick_data = [{
    'symbol': 'IF2406',
    'exchange': 'CFFEX',
    'time': datetime.now(),
    'last_price': 3650.0,
    'volume': 1000,
    # ...
}]

client.insert_tick(tick_data)
```

---

## 五、已实现功能

- [x] FeedGateway: CTP 行情接入适配器 (基于 vnpy_ctp)
- [x] TimescaleDB 连接配置
- [x] 基础 Tick 数据写入
- [x] JSON 数据导入工具
- [x] 表结构管理（长表格式）
- [x] 配置管理（支持 YAML）

---

## 六、待实现功能 (PENDING)

- [ ] P0 ConnectionManage: 连接保活机制 (心跳检测)
- [ ] P0 ConnectionManage: 断线重连与数据补齐
- [ ] P0 DbWrite: Tick 数据按合约分表存储
- [ ] P0 DbWrite: 并发写入 TimescaleDB 优化 (连接池)
- [ ] P0 Docker 配置: TimescaleDB 容器端口/密码/数据库名配置
- [ ] P0 数据链路: SimNow → DataFeed → TimescaleDB 完整链路打通
- [ ] P1 TickProcess: 数据解析与标准化
- [ ] P1 多合约并发订阅管理
- [ ] P1 写入失败重试机制
- [ ] P2 内存缓存层 (减少 IO)

---

## 七、核心类定义

| 类名               | 职责                             |
| ------------------ | -------------------------------- |
| FeedGateway        | CTP 连接与订阅管理               |
| TickProcess        | Tick 数据解析（不做 K 线合成）   |
| DbWrite            | 直接写入 TimescaleDB             |
| ConnectionManage   | 连接保活/断线重连                |
| TimescaleDBClient  | TimescaleDB 客户端               |
| TableCreator       | 表结构管理                       |
| JSONImport         | JSON 数据导入                    |

### 模块职责说明

| 模块              | 职责                             |
| ----------------- | -------------------------------- |
| FeedGateway       | CTP 连接与订阅                   |
| TickProcess       | 数据解析（不做合成）             |
| DbWrite           | 直接写入 TimescaleDB             |
| ConnectionManage  | 连接保活/断线重连                |
| TimescaleDB/      | 数据库操作工具集                 |

---

## 八、接口说明

### 供外部调用 (In)

| 接口名        | 输入                 | 输出       | 说明           |
| ------------- | -------------------- | ---------- | -------------- |
| connect       | (setting: Dict)      | bool       | 连接 CTP       |
| subscribe     | (symbol, exchange)   | bool       | 订阅行情       |
| unsubscribe   | (symbol, exchange)   | bool       | 取消订阅       |
| is_connected  | ()                   | bool       | 检查连接状态   |

### 调用外部 (Out)

| 接口名     | 目标        | 输入         | 说明           |
| ---------- | ----------- | ------------ | -------------- |
| write_tick | TimescaleDB | (TickData)   | 写入原始 Tick  |

### 接口详情

```
接口: connect(setting: Dict[str, Any]) -> bool
调用方向: 外部模块 -> DataFeed
说明: 连接 SimNow CTP 服务器

输入:
  - setting: Dict     # 连接配置
    - 用户名: str
    - 密码: str
    - 经纪商代码: str     # 默认 "9999"
    - 行情服务器: str     # 如 "tcp://180.168.146.187:10131"
    - 交易服务器: str     # 如 "tcp://180.168.146.187:10130"
    - 产品名称: str
    - 授权码: str
输出:
  - bool             # 连接成功返回 True
异常:
  - ConnectionError  # 连接失败
```

```
接口: subscribe(symbol: str, exchange: Exchange) -> bool
调用方向: 外部模块 -> DataFeed
说明: 订阅指定合约的实时行情

输入:
  - symbol: str         # 合约代码, 如 "IF2406"
  - exchange: Exchange  # 交易所, 如 Exchange.CFFEX
输出:
  - bool                # 订阅成功返回 True
异常:
  - ConnectionError     # 网关未连接
  - SymbolNotFound      # 合约代码不存在
```

```
接口: write_tick(tick: TickData) -> bool
调用方向: DataFeed -> TimescaleDB
说明: 将原始 Tick 数据写入对应合约的数据表

输入:
  - tick: TickData      # 原始 Tick 数据
输出:
  - bool                # 写入成功返回 True
异常:
  - DatabaseError       # 数据库写入失败
```

---

## 九、用例示例

**用例1: 盘前启动实时抄录**

1. 启动 DataFeed 进程
2. FeedGateway 通过 CTP API 私有协议连接 SimNow 服务器
3. 订阅目标合约列表
4. Tick 到达 → TickProcess 解析 → DbWrite 写入对应合约的 TimescaleDB 分表

**用例2: 策略订阅行情**

1. 策略模块调用 subscribe("AG2506", Exchange.SHFE)
2. FeedGateway 转发订阅请求到 CTP
3. 收到 Tick 后触发 on_tick 回调
4. 原始 Tick 数据写入 TimescaleDB 合约分表

**用例3: 断线重连**

1. ConnectionManage 检测到 CTP 连接断开
2. 记录断点时间戳
3. 自动重连 SimNow
4. 重新订阅合约
5. 从断点继续抄录

**用例4: 批量导入历史数据**

1. 使用 `import_json()` 导入历史 JSON 数据
2. 自动创建元数据记录（去重）
3. 批量写入时序数据表

---

## 附录：Tick 数据表结构

### Tick 数据表 (tick_data)

| 列名 | 类型 | 说明 |
|------|------|------|
| symbol | TEXT | 合约代码 |
| exchange | TEXT | 交易所 |
| time | TIMESTAMPTZ | 时间（毫秒精度） |
| last_price | DOUBLE | 最新价 |
| bid_price/ask_price | DOUBLE | 买卖价 |
| bid_volume/ask_volume | DOUBLE | 买卖量 |
| volume | DOUBLE | 成交量 |

> **注意**：DataFeed 只负责 Tick 数据存储。分钟线及以上的数据由 `DataSource` ETL 流程负责写入 `ohlcv_data` 表，两表独立。

---

*本文档遵循 README_PROTOTYPE.md 规范*
+++++++ REPLACE