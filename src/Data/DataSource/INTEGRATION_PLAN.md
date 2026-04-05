# DataSource 数据整合规划

> 文档版本: 1.0  
> 创建日期: 2026-03-18  
> 状态: ⚠️ **待数据库选型决策后执行**（2026-03-19 更新）

---

## 1. 项目概述

### 1.1 整合目标

将分散在多个目录、多种格式的金融数据整合为统一的数据存储架构：

| 目标格式 | 用途 | 特点 |
|----------|------|------|
| **长表 (Long Format)** | 主表存储 | `(symbol, time, value)` - 适合TimescaleDB高效存储 |
| **宽表 (Wide Format)** | 分析查询 | 按需从长表生成，支持MultiIndex列结构 |

### 1.2 设计原则

1. **保留原始数据** - 原始文件不做修改，ETL过程可重复执行
2. **数据可追溯** - 记录数据来源、导入时间、处理版本
3. **增量更新** - 支持增量数据导入，避免全量覆盖
4. **去重机制** - 基于数据哈希值防止重复导入

---

## 2. 数据源清单

### 2.1 数据源总览

| 数据源 | 路径 | 格式 | 大小 | 数据类型 |
|--------|------|------|------|----------|
| JSON数据 | `_json/` | JSON | ~1.1GB | ETF + 期货历史行情 |
| Excel数据 | `_xl/` | XLSX | - | 各交易所期货 + ETF |
| CSV数据 | `raw/akshare_daily/` | CSV | - | AkShare采集的日线数据 |
| 原始数据 | `raw/daily/`, `raw/futures/` | DAT/CSV | - | 交易所原始数据 |

### 2.2 详细数据源分析

#### 2.2.1 `_json/` 目录

```
_json/
├── etfs.json          # 893MB - ETF历史行情 (主要数据源)
├── futures.json       # 181MB - 期货历史行情
├── shrinked_ETFs.json # 精简版ETF数据
└── ...其他配置文件
```

**数据结构** (pandas JSON orient='split' 格式):
```json
{
  "columns": [["代码", "名称", "指标"], ...],  // MultiIndex 3级列名
  "index": ["2024-01-01", ...],               // 时间索引
  "data": [[值1, 值2, ...], ...]              // 数据矩阵
}
```

**列结构 (3级 MultiIndex)**:
- Level 0: 证券代码 (如 `159001.SZ`)
- Level 1: 证券名称 (如 `易方达深证100ETF`)
- Level 2: 数据指标 (如 `开盘价(元)`, `收盘价(元)`, `成交量(手)`)

**指标类型**:
| 指标类别 | 具体字段 |
|----------|----------|
| OHLCV | 开盘价, 收盘价, 最高价, 最低价, 涨跌, 涨跌幅 |
| 成交 | 成交量, 成交额, 换手率 |
| 净值 | 单位净值, 累计净值, 复权净值 |
| 其他 | 7日年化收益率, 数据回补位值 |

#### 2.2.2 `_xl/` 目录

```
_xl/
├── etfs/
│   ├── ETFs.xlsx              # ETF主数据
│   ├── ETFsbasics.xlsx        # ETF基础信息
│   ├── 黄金ETF 沪深300ETF.xlsx
│   └── ...其他ETF文件
│
└── futures/
    ├── 上期所多股输出(时间-品种)(期货).xlsx
    ├── 大商所多股输出(时间-品种)(期货).xlsx
    ├── 郑商所多股输出(时间-品种)(期货).xlsx
    ├── 中金所多股输出(时间-品种)(期货).xlsx
    ├── 上能所多股输出(时间-品种)(期货).xlsx
    ├── 广期所多股输出(时间-品种)(期货).xlsx
    ├── 上金所多股输出(时间-品种)(期货).xlsx
    └── ...境外交易所 (LME, COMEX, CBOT等)
```

**数据结构** (宽表格式):
- 行: 交易日 (时间序列)
- 列: 合约代码 (多品种)

#### 2.2.3 `raw/akshare_daily/` 目录

```
raw/akshare_daily/
├── CFFEX/  # 中金所 (IF, IC, IH, IM, T, TF, TS, TL)
├── CZCE/   # 郑商所
├── DCE/    # 大商所
├── GFEX/   # 广期所
├── INE/    # 上能所
└── SHFE/   # 上期所
```

**CSV文件格式**:
```csv
date,open,high,low,close,volume,hold,settle
2024-07-22,3501.2,3507.2,3456.8,3474.2,3461,3430,0.0
```

| 字段 | 说明 |
|------|------|
| date | 交易日期 |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| volume | 成交量 |
| hold | 持仓量 |
| settle | 结算价 |

#### 2.2.4 `raw/daily/` 目录

```
raw/daily/
├── dailydlvplacepremium_20200923.dat
├── dailydlvplacepremium_20200924.dat
└── ... (按日期组织的 .dat 文件)
```

**特点**: 交易所原始数据文件，需解析后导入

---

## 3. 目标架构设计

### 3.1 存储架构

```
┌─────────────────────────────────────────────────────────────┐
│                 源数据层 (DataSource)                        │
│  _json/  _xl/  raw/  - 原始数据完整保留                      │
└─────────────────────────────────────────────────────────────┘
                              ↓ ETL 导入
┌─────────────────────────────────────────────────────────────┐
│              主数据层 (TimescaleDB)                          │
│                                                             │
│  ┌─────────────────┐    ┌─────────────────────────────────┐│
│  │ data_metadata   │    │ timeseries_data (长表)          ││
│  │ ─────────────── │    │ ─────────────────────────────── ││
│  │ • data_hash     │←───│ • metadata_id (FK)              ││
│  │ • source_file   │    │ • symbol (代码)                  ││
│  │ • level1~4      │    │ • symbol_name (名称)             ││
│  │ • timeframe     │    │ • data_type (指标类型)           ││
│  │ • start_time    │    │ • time (时间戳) ⭐               ││
│  │ • end_time      │    │ • value (数值)                   ││
│  │ • row_count     │    │ • timeframe (时间间隔)           ││
│  └─────────────────┘    └─────────────────────────────────┘│
│                                                             │
│  TimescaleDB 超表特性:                                       │
│  • 自动分区 (按时间)                                         │
│  • 列压缩 (7天后)                                           │
│  • 高效时序查询                                              │
└─────────────────────────────────────────────────────────────┘
                              ↓ 物化视图 / 查询
┌─────────────────────────────────────────────────────────────┐
│                 分析层 (宽表/视图)                           │
│                                                             │
│  按需生成的宽表视图:                                         │
│  • v_etf_daily_wide    - ETF日线宽表                        │
│  • v_futures_daily_wide - 期货日线宽表                      │
│  • v_cross_sectional   - 截面数据视图                       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 长表 vs 宽表

#### 长表格式 (主表存储)

| metadata_id | symbol | symbol_name | data_type | time | value | timeframe |
|-------------|--------|-------------|-----------|------|-------|-----------|
| 1 | 159001.SZ | 易方达深证100ETF | 收盘价 | 2024-01-02 | 0.456 | 1d |
| 1 | 159001.SZ | 易方达深证100ETF | 开盘价 | 2024-01-02 | 0.455 | 1d |
| 1 | 159001.SZ | 易方达深证100ETF | 成交量 | 2024-01-02 | 12345 | 1d |
| 2 | IF2503 | 沪深300期货 | close | 2024-07-22 | 3474.2 | 1d |

**优点**:
- 存储高效 (稀疏数据不占空间)
- 查询灵活 (按symbol/time/data_type任意筛选)
- 扩展性强 (新增指标无需修改表结构)
- TimescaleDB优化 (时间分区、压缩)

#### 宽表格式 (分析视图)

| time | 159001.SZ_收盘价 | 159001.SZ_开盘价 | IF2503_close | ... |
|------|------------------|------------------|--------------|-----|
| 2024-01-02 | 0.456 | 0.455 | - | ... |
| 2024-07-22 | - | - | 3474.2 | ... |

**优点**:
- 分析友好 (pandas DataFrame直接使用)
- 矩阵运算高效
- 可视化便捷

---

## 4. ETL 流程设计

### 4.1 数据流图

```
                    ┌──────────────────┐
                    │   _json/etfs.json │
                    │   (893MB)         │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │   JSON Parser    │
                    │   (pandas.read_json)
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  MultiIndex解析   │
                    │  (代码/名称/指标)  │
                    └────────┬─────────┘
                             │
┌──────────────────┐        │
│   _xl/futures/   │        │
│   (Excel文件)    │────────┼───────┐
└──────────────────┘        │       │
                   ┌────────▼───────▼─────┐
                   │    Data Validator     │
                   │    (数据校验/清洗)     │
                   └────────┬──────────────┘
                            │
┌──────────────────┐       │
│ raw/akshare_daily│       │
│   (CSV文件)      │───────┤
└──────────────────┘       │
                   ┌────────▼─────────────┐
                   │   Long Format Converter│
                   │   (宽表→长表转换)       │
                   └────────┬──────────────┘
                            │
                   ┌────────▼─────────────┐
                   │   Hash Generator      │
                   │   (去重哈希计算)       │
                   └────────┬──────────────┘
                            │
                   ┌────────▼─────────────┐
                   │   TimescaleDB Writer  │
                   │   (批量写入+去重)      │
                   └────────┬──────────────┘
                            │
                   ┌────────▼─────────────┐
                   │   Metadata Recorder   │
                   │   (元数据记录)         │
                   └──────────────────────┘
```

### 4.2 ETL 阶段详解

#### Phase 1: 数据提取 (Extract)

| 数据源 | 提取方法 | 关键参数 |
|--------|----------|----------|
| JSON | `pd.read_json(path, orient='split')` | 保留MultiIndex |
| Excel | `pd.read_excel(path, sheet_name=...)` | 处理合并单元格 |
| CSV | `pd.read_csv(path, parse_dates=['date'])` | 日期解析 |

#### Phase 2: 数据转换 (Transform)

```python
# 宽表转长表
def wide_to_long(df: pd.DataFrame, symbol_col: str) -> pd.DataFrame:
    """
    将MultiIndex宽表转换为长表格式
    
    输入: MultiIndex DataFrame (time x (symbol, name, metric))
    输出: Long DataFrame (symbol, time, data_type, value)
    """
    # 1. 重置索引，将时间变为列
    df = df.reset_index()
    df = df.rename(columns={'index': 'time'})
    
    # 2. 使用 melt 转换为长表
    long_df = df.melt(
        id_vars=['time'],
        var_name=['symbol', 'symbol_name', 'data_type'],
        value_name='value'
    )
    
    # 3. 数据类型转换
    long_df['time'] = pd.to_datetime(long_df['time'])
    long_df['value'] = pd.to_numeric(long_df['value'], errors='coerce')
    
    return long_df
```

#### Phase 3: 数据加载 (Load)

```python
# 批量写入TimescaleDB
def load_to_timescaledb(
    long_df: pd.DataFrame,
    metadata: dict,
    batch_size: int = 10000
) -> int:
    """
    批量写入长表数据到TimescaleDB
    
    1. 生成数据哈希 (用于去重)
    2. 写入元数据表
    3. 批量写入主数据表
    4. 返回写入行数
    """
    pass
```

### 4.3 数据校验规则

| 校验项 | 规则 | 处理方式 |
|--------|------|----------|
| 空值检查 | `value.isna()` | 记录但不丢弃 |
| 日期有效性 | `time >= '2000-01-01'` | 跳过无效日期 |
| 数值范围 | `value > 0` (价格类) | 标记异常值 |
| 重复数据 | `data_hash` 唯一 | 跳过重复 |

---

## 5. 实施计划

> ⚠️ **前置条件**：必须先完成 DatabaseManage 数据库选型决策（路线A vs 路线B），Phase 0 及后续阶段均依赖该决策结果。

### 5.1 阶段划分

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 0: 数据库选型决策 (0天 - 必须先行)                            │
├─────────────────────────────────────────────────────────────────┤
│ □ 决策路线A（长表 / TimescaleDB/PostgreSQL）                       │
│ □ 决策路线B（分表 / MySQL/SQLite，按合约分表）                     │
│ □ 确认 TimescaleDB Docker 配置（DataFeed 共用）                   │
│ □ 确认 ETL 模式（批量 / 增量 / 流式）                             │
│ ⚠️ 未完成此决策，后续阶段无法执行                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: 环境准备 (1天)                                          │
├─────────────────────────────────────────────────────────────────┤
│ □ 部署选定的数据库                                                │
│ □ 创建目标表结构 (data_metadata, timeseries_data / 分表)         │
│ □ 准备ETL脚本目录结构                                            │
└─────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: JSON数据导入 (2-3天)                                    │
├─────────────────────────────────────────────────────────────────┤
│ □ 解析 etfs.json (893MB)                                        │
│   - MultiIndex列结构解析                                         │
│   - 宽表→长表转换                                                │
│   - 批量写入TimescaleDB                                          │
│ □ 解析 futures.json (181MB)                                     │
│ □ 验证数据完整性                                                  │
│ □ 记录导入日志                                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Excel数据导入 (1-2天)                                   │
├─────────────────────────────────────────────────────────────────┤
│ □ 遍历 _xl/etfs/ 目录                                            │
│ □ 遍历 _xl/futures/ 目录                                         │
│ □ 统一Excel格式处理                                               │
│ □ 合并到主数据表                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: CSV数据导入 (1天)                                       │
├─────────────────────────────────────────────────────────────────┤
│ □ 遍历 raw/akshare_daily/ 各交易所目录                           │
│ □ CSV格式标准化 (列名映射)                                        │
│ □ 批量导入                                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: 宽表视图创建 (1天)                                      │
├─────────────────────────────────────────────────────────────────┤
│ □ 创建 ETF 日线宽表物化视图                                       │
│ □ 创建 期货日线宽表物化视图                                       │
│ □ 创建截面数据视图                                                │
│ □ 性能测试与优化                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: 验证与文档 (1天)                                        │
├─────────────────────────────────────────────────────────────────┤
│ □ 数据完整性验证                                                  │
│ □ 查询性能测试                                                    │
│ □ 更新API文档                                                    │
│ □ 编写使用手册                                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 时间估算

| 阶段 | 预计时间 | 主要工作 |
|------|----------|----------|
| Phase 0 | 1天 | 环境配置、表结构创建 |
| Phase 1 | 2-3天 | JSON数据解析与导入 |
| Phase 2 | 1-2天 | Excel数据导入 |
| Phase 3 | 1天 | CSV数据导入 |
| Phase 4 | 1天 | 视图创建与优化 |
| Phase 5 | 1天 | 验证与文档 |
| **总计** | **7-9天** | |

### 5.3 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| JSON文件过大 (893MB) | 内存溢出 | 分块读取、流式处理 |
| 数据格式不一致 | 导入失败 | 预处理脚本、格式标准化 |
| 重复数据 | 数据冗余 | 哈希去重机制 |
| TimescaleDB连接问题 | 无法写入 | 备选SQLite方案 |

---

## 6. 代码结构规划

### 6.1 ETL 模块结构

```
src/Data/DataSource/
├── etl/
│   ├── __init__.py
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base_extractor.py    # 提取器基类
│   │   ├── json_extractor.py    # JSON提取器
│   │   ├── excel_extractor.py   # Excel提取器
│   │   └── csv_extractor.py     # CSV提取器
│   │
│   ├── transformers/
│   │   ├── __init__.py
│   │   ├── base_transformer.py   # 转换器基类
│   │   ├── wide_to_long.py       # 宽表转长表
│   │   ├── data_cleaner.py       # 数据清洗
│   │   └── validator.py          # 数据校验
│   │
│   ├── loaders/
│   │   ├── __init__.py
│   │   ├── base_loader.py        # 加载器基类
│   │   └── timescaledb_loader.py # TimescaleDB加载器
│   │
│   ├── pipeline.py               # ETL管道
│   └── config.py                 # ETL配置
│
├── scripts/
│   ├── import_json_data.py       # JSON导入脚本
│   ├── import_excel_data.py      # Excel导入脚本
│   ├── import_csv_data.py        # CSV导入脚本
│   └── run_full_import.py        # 完整导入脚本
│
└── views/
    ├── create_etf_views.sql      # ETF视图SQL
    ├── create_futures_views.sql  # 期货视图SQL
    └── view_manager.py           # 视图管理器
```

### 6.2 核心类设计

```python
# etl/pipeline.py
class ETLPipeline:
    """ETL管道"""
    
    def __init__(self, config: ETLConfig):
        self.extractor = None
        self.transformer = None
        self.loader = None
    
    def run(self, source_path: str) -> ETLResult:
        """执行ETL流程"""
        # 1. 提取
        raw_data = self.extractor.extract(source_path)
        
        # 2. 转换
        transformed = self.transformer.transform(raw_data)
        
        # 3. 加载
        result = self.loader.load(transformed)
        
        return result


# etl/transformers/wide_to_long.py
class WideToLongTransformer:
    """宽表转长表转换器"""
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """将MultiIndex宽表转换为长表"""
        pass


# etl/loaders/timescaledb_loader.py
class TimescaleDBLoader:
    """TimescaleDB加载器"""
    
    def load(self, long_df: pd.DataFrame, metadata: dict) -> int:
        """批量写入TimescaleDB"""
        pass
```

---

## 7. 数据字典

### 7.1 元数据表 (data_metadata)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | SERIAL | 主键 | 1 |
| data_hash | TEXT | 数据哈希 (去重) | "sha256:abc123..." |
| source_file | TEXT | 源文件路径 | "_json/etfs.json" |
| source_type | TEXT | 源类型 | "json" / "csv" / "excel" |
| level1 | TEXT | MultiIndex Level 1 | "159001.SZ" |
| level2 | TEXT | MultiIndex Level 2 | "易方达深证100ETF" |
| level3 | TEXT | MultiIndex Level 3 | "收盘价(元)" |
| level4 | TEXT | MultiIndex Level 4 | 备用 |
| timeframe | TEXT | 时间间隔 | "1d" / "1h" / "5min" |
| start_time | TIMESTAMPTZ | 数据起始时间 | "2020-01-01" |
| end_time | TIMESTAMPTZ | 数据结束时间 | "2024-12-31" |
| row_count | BIGINT | 数据行数 | 1234 |
| created_at | TIMESTAMPTZ | 创建时间 | "2026-03-18 10:00:00" |

### 7.2 主数据表 (timeseries_data)

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| id | SERIAL | 主键 | 1 |
| metadata_id | INTEGER | 元数据外键 | 1 |
| symbol | TEXT | 证券代码 | "159001.SZ" |
| symbol_name | TEXT | 证券名称 | "易方达深证100ETF" |
| data_type | TEXT | 数据类型 | "收盘价" / "成交量" |
| timeframe | TEXT | 时间间隔 | "1d" |
| time | TIMESTAMPTZ | 时间点 ⭐ | "2024-01-02 00:00:00" |
| value | DOUBLE | 数值 | 0.456 |
| created_at | TIMESTAMPTZ | 创建时间 | "2026-03-18 10:00:00" |

### 7.3 数据类型枚举

```python
class DataType(Enum):
    """数据类型枚举"""
    # OHLCV
    OPEN = "开盘价"
    HIGH = "最高价"
    LOW = "最低价"
    CLOSE = "收盘价"
    VOLUME = "成交量"
    AMOUNT = "成交额"
    
    # 期货专用
    SETTLE = "结算价"
    OPEN_INTEREST = "持仓量"
    
    # ETF专用
    NAV = "单位净值"
    ACCUMULATED_NAV = "累计净值"
    
    # 其他
    TURNOVER_RATE = "换手率"
    CHANGE_PCT = "涨跌幅"
```

---

## 8. 查询示例

### 8.1 长表查询

```sql
-- 查询单个ETF的收盘价历史
SELECT time, value as close_price
FROM timeseries_data
WHERE symbol = '159001.SZ'
  AND data_type = '收盘价'
  AND time BETWEEN '2024-01-01' AND '2024-12-31'
ORDER BY time;

-- 查询多个期货合约的最新价格
SELECT DISTINCT ON (symbol) 
    symbol, time, value as close
FROM timeseries_data
WHERE symbol IN ('IF2503', 'IC2503', 'IH2503')
  AND data_type = 'close'
ORDER BY symbol, time DESC;
```

### 8.2 宽表视图查询

```sql
-- 使用物化视图查询ETF宽表
SELECT time, 
       "159001.SZ_收盘价", 
       "159001.SZ_成交量"
FROM v_etf_daily_wide
WHERE time >= '2024-01-01'
ORDER BY time;

-- 刷新物化视图
REFRESH MATERIALIZED VIEW v_etf_daily_wide;
```

---

## 9. 后续扩展

### 9.1 增量更新机制

```python
class IncrementalUpdater:
    """增量更新器"""
    
    def detect_new_data(self, source_path: str) -> pd.DataFrame:
        """检测新增数据"""
        # 1. 获取源文件最新时间
        # 2. 查询数据库最新时间
        # 3. 返回差异数据
        pass
    
    def incremental_load(self, new_data: pd.DataFrame) -> int:
        """增量加载"""
        pass
```

### 9.2 数据质量监控

```python
class DataQualityMonitor:
    """数据质量监控"""
    
    def check_completeness(self, symbol: str) -> float:
        """检查数据完整性"""
        pass
    
    def check_timeliness(self, symbol: str) -> int:
        """检查数据时效性 (延迟天数)"""
        pass
    
    def detect_anomalies(self, symbol: str) -> List[dict]:
        """检测异常值"""
        pass
```

### 9.3 API 接口

```python
# 对外数据访问接口
class DataAPI:
    """数据访问API"""
    
    def get_bars(
        self, 
        symbol: str, 
        start: str, 
        end: str,
        fields: List[str] = None
    ) -> pd.DataFrame:
        """获取K线数据"""
        pass
    
    def get_cross_section(
        self, 
        date: str,
        symbols: List[str] = None,
        field: str = "收盘价"
    ) -> pd.DataFrame:
        """获取截面数据"""
        pass
    
    def get_wide_table(
        self,
        symbols: List[str],
        start: str,
        end: str,
        field: str = "收盘价"
    ) -> pd.DataFrame:
        """获取宽表数据"""
        pass
```

---

## 10. 附录

### 10.1 相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| DataSource README | `DataSource/README.md` | 数据源模块概述 |
| TimescaleDB配置 | `DataFeed/TimescaleDB/README.md` | TimescaleDB配置指南 |
| 数据库表结构 | `DatabaseManage/database_tables.py` | 现有表结构定义 |
| 数据导入脚本 | `DataManage/import_data.py` | 现有导入流程 |

### 10.2 依赖清单

```toml
# pyproject.toml
[project.dependencies]
pandas = ">=2.0.0"
numpy = ">=1.24.0"
sqlalchemy = ">=2.0.0"
psycopg2-binary = ">=2.9.0"
openpyxl = ">=3.1.0"  # Excel读取
tqdm = ">=4.65.0"     # 进度条
```

### 10.3 执行命令

```bash
# 完整导入流程
python -m Data.DataSource.scripts.run_full_import

# 单独导入JSON
python -m Data.DataSource.scripts.import_json_data --file _json/etfs.json

# 单独导入Excel
python -m Data.DataSource.scripts.import_excel_data --dir _xl/futures/

# 创建视图
python -m Data.DataSource.views.view_manager --create-all
```

---

> **注意**: 本文档仅为规划文档，所有实施工作需在确认后执行。
+++++++ REPLACE
<task_progress>- [x] 探索 src/Data 目录结构
- [x] 分析各数据源格式 (_json/, _xl/, raw/)
- [x] 理解现有数据架构
- [x] 制定整合规划
- [x] 输出 INTEGRATION_PLAN.md</task_progress>
</write_to_file>