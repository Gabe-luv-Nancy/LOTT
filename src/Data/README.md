# Data 模块文档

> ⚠️ **2026-03-19 架构澄清**：Data 模块按数据频率分为**两个独立子系统**，职责清晰分开，**不得混淆**。

| 子模块                             | 数据频率      | 数据库         | 数据源                      | 状态             |
| ------------------------------- | --------- | ----------- | ------------------------ | -------------- |
| **DataFeed**                    | Tick（毫秒级） | TimescaleDB | SimNow CTP               | Docker 已就绪，待配置 |
| **DatabaseManage + DataSource** | 中频（1min+） | TimescaleDB | `_json`/`_xl`/`raw` 原始文件 | Docker 已就绪，待配置 |

Data 模块是 LOTT 项目的数据管理层，负责数据的存储、读取、转换和管理。该模块采用**混合架构**设计，实现存储与分析分离，是业界推荐的最佳实践。

### 🏗️ 混合架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                   源数据层（原始数据）                        │
│  • 保留原始行情完整性                                         │
│  • CSV/JSON/Excel 原始文件                                   │
│  • 可追溯、可重新处理                                         │
├─────────────────────────────────────────────────────────────┤
│                   主数据层（长表）                            │
│  • 按品种+时间索引，规范化的长表格式                          │
│  • TimescaleDB 超表存储                                      │
│  • 灵活应对品种变化                                           │
├─────────────────────────────────────────────────────────────┤
│                   分析层（宽表/物化视图）                      │
│  • 按需生成分析宽表                                           │
│  • 物化视图自动刷新                                           │
│  • 高性能查询                                                 │
└─────────────────────────────────────────────────────────────┘
```

### 架构优势

| 优势      | 说明                       |
| ------- | ------------------------ |
| **灵活性** | 长表可以灵活应对品种变化，新增品种无需修改表结构 |
| **可追溯** | 源数据保留，方便重新处理和数据校验        |
| **性能**  | 分析时用宽表/物化视图，查询速度快        |
| **解耦**  | 存储与分析分离，各层独立优化           |

### 核心特性

- **多数据库支持**: 支持 SQLite 和 TimescaleDB/PostgreSQL
- **统一数据操作**: 提供一致的 CRUD 接口
- **长表存储**: 规范化的长表格式，便于维护和扩展
- **物化视图**: TimescaleDB 连续聚合，自动生成分析宽表
- **MultiIndex 支持**: 原生支持三级列索引结构
- **元数据管理**: 自动计算和存储数据质量统计
- **本地文件访问**: 支持 JSON、Excel 等多种格式
- **数据导入工具**: 提供完整的数据导入流程

## 文件结构

Data/
├── DatabaseManage/              # 数据库基础设施（Notebook 驱动）
│   ├── __init__.py
│   ├── database_config.py       # 数据库配置（SQLite / PostgreSQL / TimescaleDB）
│   ├── database_connect.py     # 数据库连接管理（单例引擎）
│   ├── database_operation.py   # 数据库 CRUD 操作
│   ├── database_tables.py     # 表结构定义（MetaColData / TimeSeriesData）
│   ├── column_selector.py     # 列选择器（哈希三元组映射）
│   └── utils.py               # 工具函数（无效值 / 哈希 / 日志）
│
├── DataManage/                 # 数据操作层（生产代码）
│   ├── __init__.py
│   ├── data_operation.py       # DataFrame ↔ 数据库读写
│   ├── import_data.py          # 原始文件导入（含 ETL 逻辑）
│   ├── local_access.py         # 本地文件访问（JSON / Excel / CSV）
│   └── cache.py                # 数据缓存
│
├── DataFeed/                   # 高频数据层（Tick → TimescaleDB）
│   ├── README.MD
│   ├── Gateway/                # CTP 行情网关
│   ├── Recorder/               # 数据记录器
│   └── TimescaleDB/            # TimescaleDB 工具集
│
├── DataSource/                 # 源数据层（原始文件 + ETL 规划）
│   ├── README.md
│   ├── INTEGRATION_PLAN.md
│   ├── _json/                 # JSON 原始数据
│   ├── _xl/                   # Excel 原始数据
│   ├── _db/                   # SQLite 数据库文件
│   ├── raw/                   # CSV / DAT 原始数据
│   └── processed/              # 处理后数据
│
└── README.md                  # 本文档

**注意**: DataManage（数据操作层）从 Jupyter Notebook 开始开发，先跑通再固化到 .py 脚本。详见各模块 README。

## 子模块职责边界（2026-03-19 确认）

| 模块             | 数据频率      | 数据库         | 定位                   |
| -------------- | --------- | ----------- | -------------------- |
| DataFeed       | Tick（毫秒级） | TimescaleDB | 高频实时，SimNow CTP 接入   |
| DataManage     | 中频（1min+） | 待选型         | 数据读写层（import + CRUD） |
| DatabaseManage | 中频（1min+） | 待选型         | 数据库基础设施（建表/索引/分区）    |

## 子模块说明

### 1. DatabaseManager（数据库管理）

#### 1.1 database_config.py（数据库配置）

**类**: `DatabaseConfig`

**功能**: 数据库配置类，两组，分别支持 SQLite 和 TimescaleDB

**主要属性**:

| 属性                     | 类型   | 默认值                     | 说明            |
| ---------------------- | ---- | ----------------------- | ------------- |
| `db_type`              | str  | "sqlite"                | 数据库类型         |
| `db_url`               | str  | "sqlite:///.../data.db" | 数据库连接 URL     |
| `sqlite_optimizations` | Dict | {...}                   | SQLite 优化配置   |
| `pg_host`              | str  | "localhost"             | PostgreSQL 主机 |
| `pg_port`              | int  | 5432                    | PostgreSQL 端口 |
| `pg_database`          | str  | "futures_data"          | 数据库名          |
| `pg_user`              | str  | "postgres"              | 用户名           |
| `pg_password`          | str  | ""                      | 密码            |
| `commit_frequency`     | int  | 10                      | 提交频率          |
| `invalid_values`       | List | [...]                   | 无效值列表         |

**SQLite 优化配置**:

```python
sqlite_optimizations = {
    "journal_mode": "WAL",      # 写前日志模式
    "cache_size": -10000,       # 约 10MB 缓存
    "synchronous": "NORMAL",    # 同步模式
    "temp_store": "memory",     # 临时存储在内存
    "mmap_size": 268435456      # 内存映射大小
}
```

**使用示例**:

```python
from database_config import DatabaseConfig

# SQLite 配置
config = DatabaseConfig(
    db_type="sqlite",
    db_url="sqlite:///X:/LOTT/src/Data/DataSource/_db/data.db"
)

# TimescaleDB 配置
config = DatabaseConfig(db_type="timescaledb")
config.to_timescaledb(
    host="localhost", 
    port=5432, 
    database="futures_data",
    user="postgres", 
    password="your_password"
)
```

#### 1.2 database_connect.py（数据库连接）

**类**: `DatabaseConnection`

**功能**: 数据库连接管理器，单例模式

**主要方法**:

| 方法                         | 说明       | 返回值          |
| -------------------------- | -------- | ------------ |
| `create_engine()`          | 创建数据库引擎  | Engine       |
| `create_session_factory()` | 创建会话工厂   | sessionmaker |
| `get_session()`            | 获取数据库会话  | Session      |
| `get_connection()`         | 获取原始连接   | Connection   |
| `test_connection()`        | 测试连接是否有效 | bool         |
| `close()`                  | 关闭数据库连接  | None         |

**类**: `Schema`

**功能**: 表结构管理器

**主要方法**:

| 方法                                                     | 说明      |
| ------------------------------------------------------ | ------- |
| `initialize_tables()`                                  | 初始化所有表  |
| `table_exists(table_name)`                             | 检查表是否存在 |
| `column_exists(table_name, colname)`                   | 检查列是否存在 |
| `add_dynamic_column(table_name, colname, column_type)` | 动态添加列   |
| `get_table_info(table_name)`                           | 获取表信息   |

**使用示例**:

```python
from database_connect import DatabaseConnection, Schema
from database_config import DatabaseConfig

config = DatabaseConfig()
connection = DatabaseConnection(config)

# 创建引擎和会话
connection.create_engine()
connection.create_session_factory()

# 测试连接
if connection.test_connection():
    print("数据库连接成功")

# 获取会话
session = connection.get_session()

# 使用 Schema 管理表结构
schema = Schema(connection)
schema.initialize_tables()
```

#### 1.3 database_tables.py（表结构定义）

**表**: `MetaColData`

**功能**: 元数据表，存储列的统计信息

**表结构**:

| 列名               | 类型         | 说明         |
| ---------------- | ---------- | ---------- |
| id               | Integer    | 主键         |
| original_colname | Text       | 原始列名       |
| colname_hash     | String(64) | 列名哈希（唯一索引） |
| level_0          | String(10) | 第一级（代码）    |
| level_1          | String(20) | 第二级（名称）    |
| level_2          | String(20) | 第三级（指标）    |
| invalid_count    | Integer    | 无效值数量      |
| total_count      | Integer    | 总数量        |
| mean             | Float      | 平均值        |
| std              | Float      | 标准差        |
| variance         | Float      | 方差         |
| skewness         | Float      | 偏度         |
| kurtosis         | Float      | 峰度         |
| min              | Float      | 最小值        |
| max              | Float      | 最大值        |
| unique_count     | Integer    | 唯一值数量      |
| unique_ratio     | Float      | 唯一值比例      |
| first_valid_date | DateTime   | 第一个有效日期    |
| last_valid_date  | DateTime   | 最后一个有效日期   |
| data_type        | String(50) | 数据类型       |
| created_at       | DateTime   | 创建时间       |
| updated_at       | DateTime   | 更新时间       |
| update_count     | Integer    | 更新次数       |

**表**: `TimeSeriesData`

**功能**: 时间序列主数据表

**表结构**:

| 列名         | 类型        | 说明                |
| ---------- | --------- | ----------------- |
| id         | Integer   | 主键                |
| date_index | DateTime  | 日期索引（唯一约束）        |
| [动态列]      | REAL/TEXT | 通过 ALTER TABLE 添加 |

#### 1.4 database_operation.py（数据库操作）

**类**: `DatabaseOperations`

**功能**: 数据库操作接口

**主要方法**:

| 方法                                                             | 说明        |
| -------------------------------------------------------------- | --------- |
| `execute_sql(sql, params)`                                     | 执行 SQL 语句 |
| `fetch_all(sql, params)`                                       | 查询所有结果    |
| `fetch_one(sql, params)`                                       | 查询单个结果    |
| `table_exists(table_name)`                                     | 检查表是否存在   |
| `col_exists(table_name, colname)`                              | 检查列是否存在   |
| `table_add_col(table_name, colname, column_type)`              | 添加列       |
| `ensure_date_records(date_index)`                              | 确保日期记录存在  |
| `check_existing_data(colname_hash, dates)`                     | 检查数据冲突    |
| `update_metadata(col_info, hashed_name, stats, existing_info)` | 更新元数据     |
| `insert_column_data(hashed_name, update_data)`                 | 插入列数据     |

**类**: `TimescaleDBOperations`

**功能**: TimescaleDB 特有操作

**主要方法**:

| 方法                                              | 说明       |
| ----------------------------------------------- | -------- |
| `create_hypertable(table_name, time_column)`    | 创建超表     |
| `insert_time_series(table, data_list)`          | 批量插入时序数据 |
| `query_range(table, start_time, end_time, ...)` | 按时间范围查询  |
| `get_latest_records(table, time_column, limit)` | 获取最新记录   |
| `downsample(source_table, dest_table, ...)`     | 数据降采样    |
| `create_compression_policy(table_name, ...)`    | 创建压缩策略   |
| `create_retention_policy(table_name, ...)`      | 创建保留策略   |
| `get_chunk_stats(table_name)`                   | 获取分块统计   |

#### 1.5 utils.py（工具函数）

**常量**:

```python
INVALID_VALUES = ['--', '-', '空', 'na', 'null', 'NULL', 'NaN', 
                  'nan', 'N/A', 'None', 'none', '', ' ', '  ',
                  None, np.nan, np.inf, -np.inf]
```

**主要函数**:

| 函数                                                 | 说明          | 返回值           |
| -------------------------------------------------- | ----------- | ------------- |
| `IF_INVALID(value)`                                | 检查值是否为无效值   | bool/Series   |
| `_now()`                                           | 获取当前时间字符串   | str           |
| `hashit(colname_tuple, print_details, backquoted)` | SHA256 哈希列名 | str/List[str] |
| `setup_logging(config)`                            | 统一日志设置      | None          |

### 2. DataManager（数据管理）

#### 2.1 data_operation.py（数据操作主类）

**类**: `DataOperation`

**功能**: 数据操作管理器，整合数据库操作

**主要方法**:

| 方法                                           | 说明                | 返回值          |
| -------------------------------------------- | ----------------- | ------------ |
| `add(df, overwrite_strategy)`                | 添加 DataFrame 到数据库 | bool         |
| `query(columns, start_date, end_date, ...)`  | 查询数据              | pd.DataFrame |
| `get_data_quality_report()`                  | 获取数据质量报告          | pd.DataFrame |
| `get_table_stats()`                          | 获取表统计信息           | Dict         |
| `get_column_info(level_0, level_1, level_2)` | 获取列信息             | pd.DataFrame |
| `close()`                                    | 关闭数据库连接           | None         |

**覆盖策略**:

| 策略          | 说明            |
| ----------- | ------------- |
| `abort`     | 发现重复数据时放弃插入   |
| `skip`      | 跳过重复数据，只插入新数据 |
| `overwrite` | 覆盖重复数据        |

**使用示例**:

```python
from data_operation import DataOperation
from database_config import DatabaseConfig

# 创建配置和操作实例
config = DatabaseConfig()
data_op = DataOperation(config)

# 添加数据
success = data_op.add(df, overwrite_strategy='skip')

# 查询数据
result = data_op.query(
    columns=['col_hash_1', 'col_hash_2'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)

# 获取数据质量报告
quality_report = data_op.get_data_quality_report()

# 获取表统计
stats = data_op.get_table_stats()
```

#### 2.2 local_access.py（本地文件访问）

**类**: `LocalData`

**功能**: 本地数据文件访问，支持 JSON、Excel

**主要方法**:

| 方法                                                 | 说明          | 返回值          |
| -------------------------------------------------- | ----------- | ------------ |
| `load_json_data(file_path, orient, if_multiindex)` | 加载 JSON 数据  | pd.DataFrame |
| `save_to_json(df, file_path, ...)`                 | 保存到 JSON    | bool         |
| `load_excel_data(file_path, sheet_name, ...)`      | 加载 Excel 数据 | pd.DataFrame |
| `export_to_excel(df, output_path, sheet_name)`     | 导出到 Excel   | None         |

**Excel 加载参数**:

| 参数                  | 默认值       | 说明      |
| ------------------- | --------- | ------- |
| `header`            | [0, 1, 2] | 多级表头行位置 |
| `index_col`         | [0]       | 索引列位置   |
| `parse_dates`       | True      | 是否解析日期  |
| `skip_tail_rows`    | 0         | 跳过末尾行数  |
| `merge_method`      | 'outer'   | 多文件合并方式 |
| `optimize_memory`   | True      | 是否优化内存  |
| `drop_na_threshold` | 0.8       | 缺失值阈值   |

**使用示例**:

```python
from local_access import LocalData

loader = LocalData()

# 加载 JSON 数据
df = loader.load_json_data('data.json', orient='split', if_multiindex=True)

# 保存到 JSON
loader.save_to_json(df, 'output.json', overwrite=True)

# 加载 Excel 数据
df = loader.load_excel_data(
    'data.xlsx',
    sheet_name='Sheet1',
    header=[0, 1, 2],
    parse_dates=True
)

# 从文件夹加载所有 Excel
df = loader.load_excel_data('./data_folder/', merge_method='outer')

# 导出到 Excel
loader.export_to_excel(df, 'output.xlsx', sheet_name='data')
```

#### 2.3 import_data.py（数据导入脚本）

**功能**: 完整的数据导入流程脚本

**主要函数**:

| 函数                              | 说明         |
| ------------------------------- | ---------- |
| `load_json_data(file_path)`     | 加载 JSON 数据 |
| `init_database(config)`         | 初始化数据库     |
| `import_data_to_db(df, config)` | 导入数据到数据库   |
| `main()`                        | 主函数        |

**使用方式**:

```python
# 命令行运行
python import_data.py

# 或作为模块使用
from import_data import load_json_data, init_database, import_data_to_db
```

## 技术框架

- **Python 版本**: 3.8+
- **核心依赖**:
  - SQLAlchemy >= 1.4.0
  - pandas >= 1.3.0
  - numpy >= 1.20.0
  - openpyxl >= 3.0.0 (Excel 支持)
  - xlrd >= 1.2.0 (旧版 Excel 支持)

## 现有代码实现情况

| 组件                    | 实现状态  | 说明             |
| --------------------- | ----- | -------------- |
| DatabaseConfig        | ✅ 完成  | 配置类已实现         |
| DatabaseConnection    | ✅ 完成  | 连接管理已实现        |
| Schema                | ✅ 完成  | 表结构管理已实现       |
| MetaColData 表         | ✅ 完成  | 元数据表已定义        |
| TimeSeriesData 表      | ✅ 完成  | 时间序列表已定义       |
| DatabaseOperations    | ✅ 完成  | 基本操作已实现        |
| TimescaleDBOperations | ⚠️ 部分 | 核心功能完成，高级功能待测试 |
| DataOperation         | ✅ 完成  | 数据操作主类已实现      |
| LocalData             | ✅ 完成  | 本地文件访问已实现      |
| import_data           | ✅ 完成  | 导入脚本已实现        |

## 尚未完成的需求

1. **数据验证增强**: 更严格的数据类型验证
2. **批量导入优化**: 大数据量导入性能优化
3. **数据备份恢复**: 数据库备份和恢复功能
4. **数据同步**: 多数据源同步功能
5. **缓存层**: 查询结果缓存机制

## 下一步修改需求

1. **连接池优化**: 改进数据库连接池管理MySQLInfluxDB
2. 
3. **异步支持**: 增加异步数据库操作
4. **数据分区**: TimescaleDB 数据分区优化
5. **监控告警**: 数据质量监控和告警
6. **API 扩展**: RESTful 数据访问接口

## 对外接口

```python
# 数据库管理
from Data.DatabaseManager import (
    DatabaseConfig,      # 数据库配置
    DatabaseConnection,  # 数据库连接
    Schema,              # 表结构管理
    DatabaseOperations,  # 数据库操作
    TimescaleDBOperations,  # TimescaleDB 操作
    MetaColData,         # 元数据表
    TimeSeriesData,      # 时间序列表
)

# 数据管理
from Data.DataManager import (
    DataOperation,       # 数据操作主类
    LocalData,           # 本地文件访问
)

# 工具函数
from Data.DatabaseManager.utils import (
    INVALID_VALUES,      # 无效值列表
    IF_INVALID,          # 无效值检查
    hashit,              # 列名哈希
    _now,                # 当前时间
)
```

## 对内接口

```python
# 内部依赖
from Data.DatabaseManager.utils import *
from Data.DatabaseManager.database_config import DatabaseConfig
from Data.DatabaseManager.database_tables import Base, MetaColData, TimeSeriesData
from Data.DatabaseManager.database_operation import DatabaseOperations
from Data.DatabaseManager.database_connect import DatabaseConnection, Schema
```

## 数据流程

```
数据导入流程:
JSON/Excel → LocalData.load_*() → DataFrame (MultiIndex)
    ↓
DataOperation.add() → 重复检查 → 元数据计算
    ↓
DatabaseOperations.insert_column_data() → SQLite/TimescaleDB

数据查询流程:
用户请求 → DataOperation.query()
    ↓
SQL 查询 → DatabaseOperations.fetch_*()
    ↓
DataFrame 返回
```

## 注意事项

1. **MultiIndex 要求**: 所有列名必须是三元组格式 `(level_0, level_1, level_2)`
2. **列名哈希**: 列名通过 SHA256 哈希后存储，避免特殊字符问题
3. **无效值处理**: 使用统一的 `INVALID_VALUES` 列表进行无效值判断
4. **事务管理**: 批量操作时注意事务提交频率，避免数据丢失
