# LOTT 本地核心功能

**项目名称:** LOTT (LOTTery Project)
**创建时间:** 2026-02-16
**最后更新:** 2026年3月7日23:30:52

---

## 🔐 核心安全原则

1. **开源且内化** - 开源免费，AI执行编程，最终内化成人能全面认知系统（因此需要系统性的README md文档、用例和日志）
2. **自定义数据** - 使用自己组织的数据库Database和数据源Datafeed
3. **本地运行** - 数据本地存储
4. **高度自定义的可视化** - 折线重叠拉伸滞后，且能看到自定义的系列标记
5. **完全隔离** - 在 `~/Projects/LOTT/` 中运行

---

## 🏗️ 系统架构

### 模块依赖关系

```
                    ┌─────────────┐
                    │  Frontend   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────┴────┐       ┌────┴────┐       ┌────┴────┐
    │ Backtest│       │ Service │       │ Strategy│
    └────┬────┘       └────┬────┘       └────┬────┘
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                    ┌──────┴──────┐
                    │    Data     │
                    └──────┬──────┘
                           │
                    ┌──────┴──────┐
                    │ Cross_Layer │
                    └─────────────┘
```

### 总体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOTT 量化交易系统架构                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    数据层 (Data Layer)                   │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ DataSource │→│ DataService │→│  Cache &   │  │  │
│  │  │ (CTP/SimNow)│ │ (Raw Data) │  │  Message   │  │  │
│  │  └─────────────┘  └─────────────┘  │  Queue     │  │  │
│  │                                         │(Redis)    │  │  │
│  │  ┌─────────────────────────────────┐  └─────────────┘  │  │
│  │  │      TimescaleDB Hypertable   │                  │  │
│  │  │      (历史数据持久化)          │                  │  │
│  │  └─────────────────────────────────┘                  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          ↑                                  │
│                    数据版本控制                             │
│                    (Data Versioning)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐           │
│  │ Redis    │←───│ Message  │←───│ Data     │           │
│  │ Cache    │    │ Queue    │    │ Version  │           │
│  │ (热数据) │    │ (Stream) │    │ Control  │           │
│  └──────────┘    └──────────┘    └──────────┘           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   策略容器 (Container)                   │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│  │
│  │  │策略容器A │  │策略容器B │  │策略容器C │  │策略容器D ││  │
│  │  │CTA策略   │  │套利策略  │  │ 日内策略 │  │ 机器学习 ││  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘│  │
│  │       │Subscribe│     │Subscribe│     │Subscribe│     │  │
│  │       └─────────┴─────────┴─────────┴─────────┘   │  │
│  │                    消息队列订阅                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                          ↑                                  │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   容器编排管理                           │  │
│  │  ├── 策略生命周期管理                                    │  │
│  │  ├── 资源配置 (CPU/内存)                               │  │
│  │  ├── 熔断保护 (Circuit Breaker)                        │  │
│  │  └── 异常恢复                                           │  │
│  └─────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    回测与优化模块                        │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐               │  │
│  │  │Backtesting│→│ Reports │→│Optimizer│               │  │
│  │  │  Engine  │  │  (JSON) │  │ 参数调优 │               │  │
│  │  └─────────┘  └─────────┘  └─────────┘               │  │
│  └─────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   监控与告警系统                          │  │
│  │  ├── 数据延迟监控                                        │  │
│  │  ├── 策略健康检查                                        │  │
│  │  ├── 异常行为检测                                        │  │
│  │  └── 告警推送 (飞书/微信)                              │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 技术栈选型

### 核心技术

| 类别   | 技术                                   |
| ---- | ------------------------------------ |
| 编程语言 | Python 3.8+                          |
| 数据处理 | pandas, numpy                        |
| 数据库  | SQLite, TimescaleDB, Redis           |
| 回测框架 | VectorBT, Backtrader, Backtesting.py |
| 可视化  | PyQtGraph, Matplotlib, Seaborn       |
| 统计分析 | scipy, statsmodels                   |
| 机器学习 | scikit-learn                         |

### 技术选型理由

| 组件        | 技术选型                 | 理由                     |
| --------- | -------------------- | ---------------------- |
| **编程语言**  | Python 3.11+         | 科学计算生态完善               |
| **数据库**   | TimescaleDB          | 时序数据优化，Hypertable 自动分区 |
| **缓存/消息** | Redis + Redis Stream | 高性能缓存 + 可靠消息队列         |
| **回测框架**  | Backtrader           | 开源                     |
| **交易API** | CTP (SimNow/实盘)      | 期货官方API                |

### 数据存储架构

```
┌─────────────────────────────────────────────┐
│              TimescaleDB                      │
│  ┌─────────────────────────────────────┐   │
│  │          Hypertable                  │   │
│  │  (自动分区的时序数据表)              │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  数据生命周期策略:                           │
│  ├── Tick 数据: 保留 7 天                  │
│  ├── 分钟K: 保留 90 天                     │
│  ├── 日K: 长期保留                          │
│  └── 自动压缩策略启用                        │
└─────────────────────────────────────────────┘
```

---

## 🔄 Redis 消息队列机制详解

### 什么是 Redis 消息队列？

**简单类比:**

```
传统方式（同步）:
策略 ←→ Redis: 策略必须等 Redis 回复才能继续

消息队列（异步）:
Redis ←[消息队列]← 策略
        ↓
     存入数据
        ↓
   策略需要时提取
```

**实际工作流程:**

```python
# 1. 数据源发布数据到 Redis
redis.publish("lott-market-data", '{"symbol": "IF2406", "price": 3650.2, "volume": 1250}')

# 2. Redis 存储这个消息（消息队列）
# 3. 多个策略容器订阅这个通道
redis.subscribe("lott-market-data", callback=策略A逻辑)
redis.subscribe("lott-market-data", callback=策略B逻辑)

# 4. 每个策略容器同时收到同样的数据，各自处理
```

### 消息队列 vs 容器化策略的关系

```
┌─────────────────────────────────────────────────────┐
│              Redis 消息队列 (数据分发中心)        │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    │
│  │策略容器1 │    │策略容器2 │    │策略容器3 │    │
│  │ CTA策略  │    │ 套利策略 │    │ 日内策略 │    │
│  └────┬────┘    └────┬────┘    └────┬────┘    │
│       │ Subscribe │ Subscribe │ Subscribe │         │
│       └──────────┴──────────┴──────────┘         │
│                    ↑                              │
│         发布数据到这个通道                         │
│         (一个数据源 → 多个消费者)                 │
└─────────────────────────────────────────────────────┘
```

**为什么用消息队列?**

| 问题          | 解决方案        |
| ----------- | ----------- |
| 策略A处理慢，阻塞数据 | 异步发送，策略各自取用 |
| 多个策略都需要数据   | 一份数据，多个消费者  |
| 数据源要等策略处理完  | 解耦，各干各的     |

### Redis 在 LOTT 中的应用场景

```
场景 1: 实时行情分发
┌──────────┐    Redis Stream     ┌──────────┐
│ CTP 接口 │ ──publish───────→ │ 策略容器A│
│ (1秒/次)│                   └──────────┘
└──────────┘                       ↑
                                     │ 订阅同一通道
                              ┌─────┴─────┐
                              │ 策略容器B │
                              │ 策略容器C │
                              └───────────┘

场景 2: 策略间通信
┌──────────┐    Redis Pub/Sub    ┌──────────┐
│ 策略容器A │ ──publish───────→ │ 策略容器B │
│ (发现机会)│                   │ (执行交易)│
└──────────┘                   └──────────┘

场景 3: 任务队列
┌──────────┐    Redis List      ┌──────────┐
│ 主程序   │ ──lpush────────→ │ 工作进程 │
│ (提交任务)│                   └──────────┘
└──────────┘                        ↑
                              ┌─────┴─────┐
                              │ 完成回调  │
                              └───────────┘
```

---

## 💾 数据分发策略（创新设计）

### 设计理念

```
┌─────────────────────────────────────────┐
│           原始数据 (中央仓库)              │
│   TimescaleDB (历史) + Redis (实时)    │
└──────────────────┬────────────────────┘
                   │
        ┌─────────┴─────────┐
        ↓                   ↓
   ┌─────────┐         ┌─────────┐
   │ 客户端A │         │ 客户端B │
   │ (CTA策略)│         │ (套利策略)│
   └────┬────┘         └────┬────┘
        ↓                   ↓
   定制化提取           定制化提取
   - IF2406 tick        - 所有合约日K
   - 技术指标           - 价差数据
   - 1个月              - 1年
```

### 优势对比

| 传统方式      | LOTT 数据分发方式  |
| --------- | ------------ |
| 每个策略读原始大表 | 每个客户端只存自己需要的 |
| 跨客户端数据冗余  | 数据按策略需求分发    |
| 查询慢       | 提取后的数据轻量     |
| 存储成本高     | 客户端分担存储      |

### 具体实现方式

**步骤 1: 策略定义数据需求**

```json
// 策略A的 config.json
{
  "data_requirements": {
    "assets": ["IF", "IC", "IH"],
    "timeframe": "1min",
    "fields": ["close", "volume", "atr"],
    "range": "2024-01-01 to 2024-12-31"
  }
}
```

**步骤 2: 数据分发服务提取**

```python
# 数据服务伪代码
class DataDistributionService:
    def extract_for_strategy(self, strategy_id, requirements):
        # 1. 读取原始 TimescaleDB
        raw_data = self.timescaledb.query(
            assets=requirements.assets,
            timeframe=requirements.timeframe,
            fields=requirements.fields,
            range=requirements.range
        )

        # 2. 按策略需求过滤
        filtered_data = self.filter_data(raw_data, requirements)

        # 3. 转换格式 (Parquet/Feather)
        formatted_data = self.format_data(filtered_data)

        # 4. 发送到对应客户端
        self.send_to_client(strategy_id, formatted_data)

        return formatted_data
```

**步骤 3: 客户端本地存储**

```
~/LOTT-clients/client-A/
├── data/
│   ├── IF_1min.parquet
│   ├── IC_1min.parquet
│   └── IH_1min.parquet
├── config.json              ← 策略需求定义
└── cache/
    └── computed_indicators/  ← 本地计算的因子
```

### 数据同步机制

```
中央数据源                    客户端A                    客户端B
    │                           │                        │
    │  [增量同步]              │                        │
    │ ──────────────────────→ │ 只同步变更部分          │
    │                         │                        │
    │                         │ [客户端自主处理]         │
    │                         │ - 计算技术指标          │
    │                         │ - 生成特征工程          │
    │                         │                        │
    │  [全量同步(可选)]       │                        │
    │ ─────────────────────────────────────────→        │
    │                         │                        │
```

**优势:**

- 中央数据源负责权威数据
- 客户端各自扩展（计算因子、生成特征）
- 只传增量，带宽友好

---

## 📄 回测报告 JSON 格式设计

### 设计目标

- 机器可读：方便程序筛选排序
- 人类可读：方便人工审查
- 可追溯：每个策略有唯一ID
- 可对比：标准化字段，便于横向比较

### JSON 报告完整结构

```json
{
  "$schema": "https://lott.project/schemas/backtest-report-v1.json",

  "strategy_info": {
    "strategy_id": "CTA-MA-Cross-001",
    "strategy_name": "双均线交叉策略",
    "parent_strategy": "CTA-MA-Cross-Base",
    "version": "1.0.0",
    "description": "基于5日和20日均线的趋势跟踪策略"
  },

  "parameters": {
    "fast_ma_period": 5,
    "slow_ma_period": 20,
    "atr_period": 14,
    "stop_loss_pct": 2.0,
    "position_size": 0.1,
    "trade_direction": "long_only"
  },

  "backtest_config": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000.00,
    "commission_rate": 0.0003,
    "slippage": 0.0001,
    "data_version": "v2024-Q4",
    "benchmark": "IF2401"
  },

  "results": {
    "performance": {
      "total_return": 0.1582,
      "annual_return": 0.1645,
      "sharpe_ratio": 1.85,
      "sortino_ratio": 2.34,
      "calmar_ratio": 1.52,
      "max_drawdown": 0.0823,
      "max_drawdown_duration_days": 45,
      "avg_drawdown": 0.0321
    },

    "trading_stats": {
      "total_trades": 234,
      "win_rate": 0.5234,
      "profit_factor": 1.72,
      "avg_trade_pnl": 293.50,
      "avg_trade_return": 0.00068,
      "avg_holding_period_days": 4.2,
      "best_trade": 0.0456,
      "worst_trade": -0.0234,
      "consecutive_wins": 5,
      "consecutive_losses": 3,
      "avg_time_in_market": 0.65
    },

    "monthly_returns": {
      "2024-01": 0.0123,
      "2024-02": -0.0056,
      "2024-03": 0.0234,
      "2024-04": 0.0189,
      "2024-05": -0.0123,
      "2024-06": 0.0256,
      "2024-07": 0.0156,
      "2024-08": -0.0089,
      "2024-09": 0.0321,
      "2024-10": 0.0198,
      "2024-11": 0.0289,
      "2024-12": 0.0212
    }
  },

  "equity_curve": {
    "granularity": "daily",
    "data": [
      {"date": "2024-01-02", "equity": 100500.00, "drawdown": -0.0000},
      {"date": "2024-01-03", "equity": 101200.00, "drawdown": -0.0000},
      {"date": "2024-01-04", "equity": 100850.00, "drawdown": -0.0035},
      {"date": "2024-01-05", "equity": 102100.00, "drawdown": -0.0000},
      ...
    ],
    "total_days": 248,
    "total_records": 248
  },

  "trade_log": {
    "total_trades": 234,
    "trades": [
      {
        "trade_id": "T001",
        "symbol": "IF2406",
        "side": "long",
        "entry_date": "2024-01-15 09:35:00",
        "entry_price": 3620.5,
        "exit_date": "2024-01-18 15:00:00",
        "exit_price": 3650.2,
        "quantity": 1,
        "pnl": 2970.00,
        "pnl_pct": 0.0082,
        "holding_period": 3,
        "exit_reason": "signal_reverse",
        "commission": 108.62,
        "slippage": 36.21
      },
      ...
    ]
  },

  "metadata": {
    "created_at": "2026-02-16T13:30:00Z",
    "data_version": "v2024-Q4",
    "optimization_id": "opt-20260216-001",
    "duration_ms": 12500,
    "software_version": "LOTT-v0.1.0"
  }
}
```

### 策略筛选器伪代码

```python
# 机器筛选示例
def filter_strategies(reports, criteria):
    candidates = []

    for report in reports:
        score = 0
        reasons = []

        # 基础筛选
        if report.results.sharpe_ratio >= criteria.min_sharpe:
            score += 10
        else:
            continue

        if report.results.max_drawdown <= criteria.max_drawdown:
            score += 10
        else:
            continue

        # 盈利筛选
        if report.results.total_return > criteria.min_return:
            score += 10

        if report.results.profit_factor > criteria.min_profit_factor:
            score += 5

        # 交易频率筛选
        if report.trading_stats.avg_holding_period >= criteria.min_holding_days:
            score += 3

        report.final_score = score
        candidates.append((report, score, reasons))

    # 排序输出
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates
```

### 报告存储结构

```
~/LOTT/backtests/
├── 2024/
│   ├── Q1/
│   │   ├── CTA-MA-Cross-001.json
│   │   ├── CTA-MA-Cross-002.json
│   │   ├── ...
│   │   └── index.json  ← 索引文件
│   │
│   ├── Q2/
│   └── ...
│
├── 2025/
│   └── ...
│
└── reports/
    ├── top-strategies-2024-Q1.json
    └── candidate-pool.json
```

---

## 📈 功能模块

### 模块开发状态总览

| 模块          | 完成度 | 说明                     |
| ----------- | --- | ---------------------- |
| Cross_Layer | 95% | 核心功能完成                 |
| Data        | 90% | 核心功能完成，TimescaleDB 待测试 |
| Frontend    | 80% | 核心框架完成，测试与优化待开发        |
| Strategy    | 85% | 策略库丰富，部分策略需完善          |
| Backtest    | 80% | 核心框架完成，适配器待优化          |
| Service     | 70% | 核心服务完成，Returns 类待完善    |
| Report      | 60% | 基本功能完成，更多报告类型待开发       |

### 1. 数据模块 (Data) - 90%

- [x] 数据库配置和连接管理
- [x] SQLite 本地数据库支持
- [x] 元数据自动计算
- [x] 本地文件访问（JSON、Excel）
- [x] 数据导入流程
- [ ] TimescaleDB 完整测试
- [ ] 实时行情接入 (CTP/SimNow)
- [ ] 数据版本控制
- [ ] 断点续传机制

### 2. 回测模块 (Backtest) - 80%

- [x] 多框架回测支持（VectorBT、Backtrader、Backtesting.py）
- [x] 统一的回测接口和配置
- [x] 策略基类和信号格式
- [x] 参数优化功能
- [x] 回测结果分析
- [ ] 适配器优化
- [ ] JSON 报告生成器
- [ ] 报告分析工具

### 3. 策略模块 (Strategy) - 85%

- [x] 趋势跟踪策略（MACD、SAR）
- [x] 均值回归策略（配对交易、布林带、RSI）
- [x] 突破策略（Dual Thrust、London Breakout）
- [x] 时间序列模型（MA、ARIMA）
- [x] 算子工具函数
- [ ] 部分策略完善

### 4. 服务模块 (Service) - 70%

- [x] 交易日过滤
- [x] 回测数据准备
- [x] CTP/SimNow 数据源基础支持
- [x] Redis 实时数据分发基础
- [ ] 收益率计算服务（Returns 类待完善）
- [ ] 模拟交易完整实现
- [ ] 实盘交易接口

### 5. 跨层工具模块 (Cross_Layer) - 95%

- [x] 统一导入管理
- [x] TimestampEngine 时间处理引擎
- [x] 日志系统
- [x] JSON 存储
- [x] 数据详情分析 (detail)

> **注意**: 以下功能已迁移或废弃：
> - `EnhancedDataFrame` → `Data/DatabaseManager/column_selector.py`（函数式API）
> - `InvaPlotWidget` → **已废弃** - 使用 `ChartWidget` + Marker
> - 无效值检测工具 → `Frontend/utils/data_utils.py`

### 6. 前端模块 (Frontend) - 80%

- [x] 核心模块（数据管理、信号总线、配置）
- [x] 图表组件（ChartWidget、元素、标记、光标）
- [x] 数据库面板（元数据查看、列树形导航）
- [x] 变量面板（多层折线图、lagging控制）
- [x] 回测面板（价格图、仓位、收益曲线、交易列表）
- [x] 主窗口和Dock管理器
- [x] 样式系统（主题管理）
- [ ] 单元测试
- [ ] 性能优化
- [ ] 文档完善

### 7. 报告模块 (Report) - 60%

- [x] DataFrame 列信息报告
- [x] MultiIndex 结构分析
- [x] Excel 格式化输出
- [x] 数据摘要统计
- [ ] 更多报告类型开发

### 8. 监控模块 - 待开发

- [ ] 策略运行监控
- [ ] 熔断保护
- [ ] 风险预警
- [ ] 告警推送 (飞书/微信)

### 9. 容器编排 - 待开发

- [ ] 策略隔离运行
- [ ] 资源限制 (CPU/内存)
- [ ] 自动重启
- [ ] 弹性扩缩容

---

## ⚠️ 风险提示

1. **回测≠实盘** - 历史表现不代表未来收益
2. **杠杆风险** - 期货自带杠杆，谨慎使用
3. **合规风险** - 仅供学习和研究用途
4. **数据延迟** - 实时性需验证
5. **技术风险** - 系统稳定性需持续测试

---

## 🚀 快速开始

```python
# 1. 设置路径
import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *

# 2. 加载数据
from Data.DataManager.local_access import LocalData
loader = LocalData()
df = loader.load_excel_data('data.xlsx')

# 3. 运行策略
from Strategy.strategies import macd_oscillator_strategy
signals = macd_oscillator_strategy(df)

# 4. 执行回测
from backtest import BacktestLayer, UniData
data = UniData.from_dataframe(df)
result = BacktestLayer().set_data(data).set_strategy(MyStrategy()).run()

# 5. 生成报告
from Report.multiindex_report import multiindex_report
multiindex_report(df, 'report.xlsx')
```

---

## 📁 目录结构

```
~/LOTT/
├── data/                      # 数据目录 (TimescaleDB)
│   ├── raw/                  # 原始数据
│   ├── processed/            # 处理后的数据
│   └── backups/              # 数据备份
│
├── strategies/                # 策略代码
│   ├── cta/                 # CTA策略
│   ├── arbitrage/           # 套利策略
│   ├── intraday/            # 日内策略
│   └── ml/                  # 机器学习策略
│
├── backtests/                # 回测结果
│   ├── 2024/
│   └── 2025/
│
├── clients/                  # 客户端分发
│   └── [client-id]/
│       ├── config.json       # 客户端配置
│       └── data/            # 按需提取的数据
│
├── scripts/                 # 工具脚本
│   ├── data_ingestion.py    # 数据摄入
│   ├── data_distribution.py  # 数据分发
│   └── report_analyzer.py   # 报告分析
│
├── tests/                    # 测试用例
│   ├── unit/
│   └── integration/
│
├── config/                   # 配置文件
│   ├── database.yml
│   ├── redis.yml
│   └── strategies.yml
│
├── docs/                    # 文档
│   ├── architecture/
│   ├── api/
│   └── user_guide/
│
├── docker/                   # Docker配置
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── PROJECT_PLAN.md           # 本规划文档
└── README.md
```

---

## 🔄 下一步计划

### Phase 1: 基础设施搭建 (90% 完成)

- [x] SQLite 本地数据库环境
- [x] 数据库配置和连接管理
- [x] 本地文件访问（JSON、Excel）
- [x] 基础数据导入流程
- [x] 元数据自动计算
- [ ] TimescaleDB 环境搭建
- [ ] Redis + Redis Stream 配置
- [ ] Docker 容器环境搭建

### Phase 2: 回测框架开发 (80% 完成)

- [x] 多框架回测支持（VectorBT、Backtrader、Backtesting.py）
- [x] 统一的回测接口和配置
- [x] 策略基类和信号格式
- [x] 参数优化功能
- [x] 回测结果分析
- [ ] JSON 报告生成器
- [ ] 报告分析工具
- [ ] 适配器优化

### Phase 3: 策略开发 (85% 完成)

- [x] 趋势跟踪策略（MACD、SAR）
- [x] 均值回归策略（配对交易、布林带、RSI）
- [x] 突破策略（Dual Thrust、London Breakout）
- [x] 时间序列模型（MA、ARIMA）
- [x] 算子工具函数
- [ ] 部分策略完善和测试

### Phase 4: 服务层开发 (70% 完成)

- [x] 交易日过滤
- [x] 回测数据准备
- [x] CTP/SimNow 数据源基础支持
- [x] Redis 实时数据分发基础
- [ ] 收益率计算服务（Returns 类）
- [ ] 模拟交易完整实现
- [ ] 实盘交易接口

### Phase 5: 前端开发 (80% 完成)

- [x] 核心模块（数据管理、信号总线、配置）
- [x] 图表组件（ChartWidget、元素、标记、光标）
- [x] 数据库面板（元数据查看、列树形导航）
- [x] 变量面板（多层折线图、lagging控制）
- [x] 回测面板（价格图、仓位、收益曲线、交易列表）
- [x] 主窗口和Dock管理器
- [x] 样式系统（主题管理）
- [ ] 单元测试
- [ ] 性能优化
- [ ] 文档完善

### Phase 6: 容器化策略 (待开发)

- [ ] 策略容器模板
- [ ] 容器编排管理
- [ ] Redis 消息队列完整集成
- [ ] 熔断保护机制

### Phase 7: 监控告警 (待开发)

- [ ] 监控面板
- [ ] 告警系统
- [ ] 飞书通知集成
- [ ] 自动化运维

### Phase 8: 报告系统 (60% 完成)

- [x] DataFrame 列信息报告
- [x] MultiIndex 结构分析
- [x] Excel 格式化输出
- [x] 数据摘要统计
- [ ] 更多报告类型开发
- [ ] 可视化报告生成

---

## 💡 技术选型理由

### 为什么选择 TimescaleDB?

1. **时序数据优化** - 自动分区，冷热数据分离
2. **PostgreSQL 生态** - SQL 兼容，学习成本低
3. **压缩存储** - 高压缩比，节省存储
4. **连续聚合** - 实时计算 K 线

### 为什么选择 Redis Stream?

1. **持久化** - 消息不丢失
2. **消费者组** - 多策略负载均衡
3. **ACK 机制** - 确保消息处理
4. **低延迟** - 内存级速度

### 为什么容器化?

1. **隔离性** - 策略间互不干扰
2. **可复制** - 环境一致
3. **资源可控** - CPU/内存限制
4. **弹性** - 快速启停

---

## 🔗 参考资料

- [TimescaleDB 文档](https://docs.timescale.com/)
- [Redis Stream 教程](https://redis.io/docs/data-types/streams-tutorial/)
- [Backtrader 文档](https://www.backtrader.com/doc/)
- [CTP 接口文档](https://github.com/verajoey/ctp-python)
- [LOMP 量化开源项目](https://github.com/joe-joseph/LOMP)

---

**LOTT = Libre Open-source Trading Terminal**

*让量化交易回归开源的本质*

*数据驱动，策略分离，安全可控*
