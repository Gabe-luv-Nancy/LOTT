# Service 模块需求文档

## 1. 概述

Service 模块是 LOTT 项目的数据处理服务层，负责将上游数据库查询结果转换为下游可操作的 DataFrame。作为数据层和策略层的桥梁，本模块提供数据转换、缓存管理、质量分析和收益率计算等核心服务。

**核心职责**：
- 将数据库 SELECT 查询结果转换为标准化 DataFrame
- 提供 DataFrame 格式转换和预处理功能
- 管理数据缓存以提升访问效率
- 生成数据质量分析报告
- 支持收益率计算和交易日过滤

## 2. 技术框架

- **Python 版本**: 3.8+
- **核心依赖**:
  - pandas >= 1.3.0 (DataFrame 处理)
  - numpy >= 1.20.0 (数值计算)
  - redis >= 4.0.0 (缓存服务)
  - holidays >= 0.18.0 (节假日处理)

## 3. 已实现功能

- [x] DataFrame 转换器：支持数据库查询结果到 DataFrame 的转换
- [x] MultiIndex 列名处理：自动识别和构建多级列名
- [x] 数据缓存管理：LRU 淘汰策略、TTL 过期支持
- [x] 数据质量分析：缺失值统计、数据范围报告
- [x] 收益率计算：简单收益率和对数收益率
- [x] 累计收益率：支持再投资和年化处理
- [x] 交易日过滤：自动过滤周末和法定节假日

## 4. 待实现功能 (PENDING)

- [ ] P0 支持更多数据库类型的查询结果转换（PostgreSQL、MySQL）
- [ ] P0 DataFrame 列名映射和标准化配置
- [ ] P1 数据清洗管道：异常值检测和处理
- [ ] P1 数据对齐：多源数据的时间对齐
- [ ] P2 分布式缓存：Redis 集群支持
- [ ] P2 数据预聚合：支持多周期聚合

## 5. 核心类定义

| 类名 | 职责 |
|------|------|
| DataFrameTransformer | 数据库查询结果到 DataFrame 的转换器 |
| DataCache | 数据缓存管理器，支持 LRU 和 TTL |
| DataQualityAnalyzer | 数据质量分析器，生成数据报告 |
| Returns | 收益率计算器，支持多种收益率类型 |

## 6. 接口说明

### 6.1 供外部调用 (In)

| 接口名 | 输入 | 输出 | 说明 |
|--------|------|------|------|
| transform_query_result | (query_result, column_mapping) | pd.DataFrame | 转换数据库查询结果 |
| transform_to_multiindex | (df, level_names) | pd.DataFrame | 转换为 MultiIndex DataFrame |
| normalize_columns | (df, schema) | pd.DataFrame | 标准化列名 |
| cache_get | (key) | Any | 获取缓存数据 |
| cache_set | (key, value, ttl) | None | 设置缓存 |
| analyze_quality | (df) | Dict | 分析数据质量 |
| generate_report | (df, output_format) | str | 生成质量报告 |
| cumulative_returns | (df, columns, return_type) | pd.DataFrame | 计算累计收益率 |
| filter_trading_days | (df, country) | pd.DataFrame | 过滤非交易日 |

### 6.2 调用外部 (Out)

| 接口名 | 目标模块 | 输入 | 输出 | 说明 |
|--------|----------|------|------|------|
| query_data | Data.DatabaseManager | (sql, params) | List[Dict] | 执行数据库查询 |
| get_connection | Data.DatabaseManager | (config) | Connection | 获取数据库连接 |

### 6.3 核心接口详细定义

```
接口: transform_query_result(query_result: List[Dict], column_mapping: Dict) -> pd.DataFrame
调用方向: 外部模块 -> 本模块
说明: 将数据库 SELECT 查询结果转换为标准化 DataFrame

输入:
  - query_result: List[Dict]   # 数据库查询结果，每行一个字典
  - column_mapping: Dict       # 列名映射配置，可选
输出:
  - pd.DataFrame               # 标准化后的 DataFrame
异常:
  - ValueError                 # 查询结果为空或格式错误
  - TypeError                  # 输入类型不正确
```

```
接口: analyze_quality(df: pd.DataFrame) -> Dict
调用方向: 外部模块 -> 本模块
说明: 分析 DataFrame 数据质量

输入:
  - df: pd.DataFrame           # 待分析的 DataFrame
输出:
  - Dict                       # 包含缺失率、数据范围等统计信息
异常:
  - ValueError                 # DataFrame 为空
```

```
接口: DataCache.get(key: str) -> Any
调用方向: 外部模块 -> 本模块
说明: 从缓存获取数据

输入:
  - key: str                   # 缓存键名
输出:
  - Any                        # 缓存的数据，不存在或过期返回 None
```

## 7. 用例示例

### 用例1: 数据库查询结果转换

1. 上游模块执行 SELECT 语句获取数据
2. 调用 transform_query_result() 转换为 DataFrame
3. 自动处理 MultiIndex 列名和日期索引
4. 返回标准化 DataFrame 供下游使用

### 用例2: 数据缓存加速

1. 首次查询时调用 cache_set() 缓存结果
2. 后续查询先调用 cache_get() 检查缓存
3. 缓存命中直接返回，未命中则查询数据库
4. 缓存自动过期（TTL）或淘汰（LRU）

### 用例3: 数据质量分析

1. 获取 DataFrame 后调用 analyze_quality()
2. 自动统计缺失值、异常值、数据范围
3. 生成数据质量报告供策略参考

## 8. 文件结构

```
Service/
├── __init__.py              # 模块入口
├── README.md                # 本文档
├── returns.py               # 收益率计算服务
├── transformer.py           # DataFrame 转换器
├── cache.py                 # 数据缓存管理
├── quality.py               # 数据质量分析
└── data_service/            # 实时数据服务子模块
    ├── __init__.py
    ├── config.py            # 服务配置
    ├── service.py           # 数据服务主类
    ├── redis_client.py      # Redis 客户端
    └── datasource.py        # 数据源接口
```

## 9. 对外接口

```python
# DataFrame 转换
from Service import (
    DataFrameTransformer,     # DataFrame 转换器
    transform_query_result,   # 快捷转换函数
)

# 数据缓存
from Service import (
    DataCache,                # 缓存管理类
)

# 数据质量
from Service import (
    DataQualityAnalyzer,      # 质量分析类
    analyze_quality,          # 快捷分析函数
)

# 收益率服务
from Service import (
    Returns,                  # 收益率计算类
    filter_trading_days,      # 交易日过滤
    advanced_filter_trading_days,  # 高级交易日过滤
)

# 实时数据服务
from Service.data_service import (
    DataService,              # 数据服务主类
    DataServiceConfig,        # 服务配置
)