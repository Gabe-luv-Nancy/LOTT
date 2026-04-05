# DataSource 子模块文档

> ⚠️ **2026-03-19 澄清**：本模块处理**中频数据**（1分钟线及以上）的 ETL 导入，与 DataFeed 的 Tick 高频数据完全独立。

## 模块概述

DataSource 子模块是 LOTT 项目的**源数据层**，负责从外部数据源采集期货和ETF市场数据，并保留原始数据的完整性。

### 🏗️ 混合架构中的定位

DataSource 是**中频数据**的源数据层，与 DataFeed 的 Tick 高频层完全分离：

```
┌─────────────────────────────────────────────────────────────┐
│          高频数据层（DataFeed）← 与本模块无关 ⛔               │
│  SimNow CTP → DataFeed → TimescaleDB（Tick 级）             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│          中频数据层（DataSource）← 本模块 ⭐                  │
│  原始文件 → ETL → DatabaseManage → 目标数据库（待选型）       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              主数据层（DatabaseManager）                      │
│   • 路线A：长表（TimescaleDB/PostgreSQL，全量一表）           │
│   • 路线B：分表（MySQL/SQLite，按合约数百张表）               │
│   ⚠️ 选型未锁定，P0 待决策                                   │
└─────────────────────────────────────────────────────────────┘
```

### 数据规模

| 数据源 | 路径 | 格式 | 规模 |
|--------|------|------|------|
| JSON数据 | `_json/` | JSON | ~1.1GB（ETF + 期货） |
| Excel数据 | `_xl/` | XLSX | 各交易所期货 + ETF |
| CSV数据 | `raw/akshare_daily/` | CSV | 按交易所分目录 |
| DAT原始 | `raw/daily/` | DAT | 交易所原始文件 |

**总规模预估**：ETF 全市场 + 期货历史 > **上千万行**，CSV 无法安全储存。

### 源数据层设计原则

| 原则 | 说明 |
|------|------|
| **完整性** | 保留原始数据的所有字段，不做任何过滤 |
| **可追溯** | 记录数据来源、采集时间，便于审计 |
| **可重处理** | 原始数据保留，ETL 逻辑可随时重新执行 |
| **格式多样** | 支持 CSV、JSON、Excel、数据库等多种格式 |

### 核心功能

- **多数据源支持**: CTP、AkShare、Tushare、东方财富等
- **实时数据采集**: 期货实时Tick和K线数据
- **历史数据获取**: 期货和ETF历史行情
- **数据格式转换**: MultiIndex支持、K线合成
- **本地文件访问**: JSON、Excel、CSV等格式
- **源数据归档**: 原始数据完整保存，支持重新处理

## 文件结构

```
DataSource/
├── README.md                        # 本文档
├── DATA_COLLECTION_REQUIREMENTS.md  # 📋 综合需求文档（主文档）
├── CTP_Data_Requirements.md         # CTP 数据采集详细需求
├── CTP_Windows_Plan.md              # Windows 环境部署方案
├── tushare_README.md                # Tushare 数据源配置
├── vnpy_simnow_CONFIG.md            # VN.py + SimNow 配置
│
├── ### collectors/（已废弃，归 DataFeed）                      # 数据采集器（待开发）
│   ├── __init__.py
│   ├── base_collector.py           # 采集器基类
│   ├── ctp_collector.py            # CTP 采集器
│   ├── akshare_collector.py        # AkShare 采集器
│   └── etf_collector.py            # ETF 采集器
│
├── _db/                            # SQLite 数据库
│   └── data.db
│
├── _json/                          # JSON 数据文件
│   ├── data.json
│   ├── futures.json                # 期货合约列表
│   ├── etfs.json                   # ETF 列表
│   └── config.json                 # 配置文件
│
├── _xl/                            # Excel 数据文件
│   ├── etfs/
│   ├── futures/
│   └── macros/
│
└── vnpy-master/                    # VN.py 源码参考
```

## 📋 综合需求文档

**请首先阅读**: [DATA_COLLECTION_REQUIREMENTS.md](./DATA_COLLECTION_REQUIREMENTS.md)

该文档整合了所有数据采集需求，包括：
- 项目目标和设计原则
- 数据源方案对比
- 技术架构设计
- 功能需求清单
- 实施计划

## 数据源概览

| 数据源 | 类型 | 费用 | 用途 |
|--------|------|------|------|
| **CTP (vnpy_ctp)** | 期货实时 | 免费 | 主要数据源 |
| **AkShare** | 期货+ETF | 免费 | 历史数据补充 |
| **Tushare** | 期货+ETF | ¥2000/年 | 备选方案 |
| **东方财富** | ETF | 免费 | ETF数据源 |

## 快速开始

### 1. 安装依赖

```bash
# 核心依赖
pip install pandas numpy

# CTP 数据源（Windows）
pip install vnpy vnpy_ctp

# AkShare（跨平台）
pip install akshare

# 数据库
pip install sqlalchemy
```

### 2. 配置 SimNow 账户

编辑 `vnpy_simnow_CONFIG.md` 中的账户信息：

```yaml
broker_id: "9999"
user_id: "你的账号"
password: "你的密码"
md_address: "tcp://218.202.237.33:10010"
```

### 3. 运行数据采集

```python
# 示例：使用 AkShare 获取 ETF 数据
import akshare as ak

# 获取 ETF 列表
etf_list = ak.fund_etf_spot_sina()

# 获取历史数据
history = ak.fund_etf_hist_sina(symbol="510300")
```

## 核心组件说明

### 1. 数据采集器（规划中）

**基类**: `BaseCollector`

```python
class BaseCollector:
    """数据采集器基类"""
    
    def connect(self):
        """连接数据源"""
        raise NotImplementedError
        
    def subscribe(self, symbols: list):
        """订阅数据"""
        raise NotImplementedError
        
    def collect(self):
        """采集数据"""
        raise NotImplementedError
        
    def save(self, data):
        """保存数据"""
        raise NotImplementedError
```

### 2. 数据导入器（现有）

**类**: `DataImporter`

**功能**: 从本地文件导入数据到系统

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `import_from_excel(filepath, **kwargs)` | 从 Excel 导入 | pd.DataFrame |
| `import_from_csv(filepath, **kwargs)` | 从 CSV 导入 | pd.DataFrame |
| `import_from_api(url, params)` | 从 API 导入 | pd.DataFrame |
| `validate_data(df)` | 验证数据格式 | bool |

### 3. 格式转换器（现有）

**类**: `DataConverter`

**功能**: 数据格式转换和处理

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `to_multiindex(df, levels)` | 转换为 MultiIndex | pd.DataFrame |
| `flatten_columns(df)` | 展平多级列名 | pd.DataFrame |
| `resample_ohlcv(df, timeframe)` | 重采样 OHLCV 数据 | pd.DataFrame |

## 技术框架

| 组件 | 版本要求 | 用途 |
|------|----------|------|
| Python | 3.10+ | 运行环境 |
| pandas | >= 1.3.0 | 数据处理 |
| numpy | >= 1.20.0 | 数值计算 |
| requests | >= 2.26.0 | HTTP请求 |
| akshare | >= 1.10.0 | 数据源 |
| vnpy_ctp | latest | CTP接口 |
| sqlalchemy | >= 1.4.0 | 数据库 |

## 相关文档

| 文档 | 说明 |
|------|------|
| [DATA_COLLECTION_REQUIREMENTS.md](./DATA_COLLECTION_REQUIREMENTS.md) | **综合需求文档（主文档）** |
| [CTP_Data_Requirements.md](./CTP_Data_Requirements.md) | CTP 数据采集详细需求 |
| [CTP_Windows_Plan.md](./CTP_Windows_Plan.md) | Windows 环境部署方案 |
| [tushare_README.md](./tushare_README.md) | Tushare 数据源配置 |
| [vnpy_simnow_CONFIG.md](./vnpy_simnow_CONFIG.md) | VN.py + SimNow 配置 |
| [../DatabaseManager/README.md](../DatabaseManager/README.md) | 数据库管理模块 |
| [../DataManager/README.md](../DataManager/README.md) | 数据操作模块 |

## 对外接口

```python
# 数据采集器（规划中）
from Data.DataSource.collectors import (
    CTPCollector,       # CTP 采集器
    AkShareCollector,   # AkShare 采集器
    ETFCollector,       # ETF 采集器
)

# 数据导入（现有）
from Data.DataSource import (
    DataImporter,       # 数据导入器
    DataConverter,      # 格式转换器
)
```

## 开发状态

| 功能 | 状态 | 说明 |
|------|------|------|
| 本地文件导入 | ✅ 已完成 | Excel/CSV/JSON |
| 数据库存储 | ✅ 已完成 | SQLite/TimescaleDB |
| CTP 采集器 | 🚧 规划中 | vnpy_ctp |
| AkShare 采集器 | 🚧 规划中 | 免费数据源 |
| ETF 采集器 | 🚧 规划中 | 东方财富/AkShare |
| 定时任务 | 📋 待开发 | APScheduler |

---

*最后更新：2026-03-06*
