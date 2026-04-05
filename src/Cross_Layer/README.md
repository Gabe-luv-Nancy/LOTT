# Cross_Layer 模块文档

> LOTT 项目核心公共层，被所有其他模块依赖。

---

## 文件结构

```
Cross_Layer/
├── __init__.py              # 模块入口，统一导出
├── global_config.py          # 全局路径配置 + TSDB/日志/数据源常量
├── global_imports.py         # 常用模块统一导入（pd / np / os / json 等）
├── detail.py                # 数据详情分析（Series / DataFrame 统计报告）
├── json_storage.py          # JSON 文件读写（原子写入、原子更新）
├── logger.py                # 日志系统（ContextLogger / setup_logger / dir_exist）
├── timestamp_engine.py       # 时间戳解析与标准化引擎
└── README.md               # 本文档
```

---

## 模块说明

### detail.py — 数据详情分析

提供 Series 和 DataFrame 的稳健描述性统计，支持分位数计算。

```python
from Cross_Layer.detail import detail

stats = detail(df, include_numeric=True, include_object=True, show_report=True)
```

**输出统计量：**

| 类别 | 统计量 |
|------|--------|
| 基本 | dtype, count, missing_count, missing_pct |
| 数值 | mean, std, min, max, median, sum, variance |
| 高级 | skewness, kurtosis, range, cv（变异系数） |
| 分位 | percentile_25, percentile_50, percentile_75 |
| 对象 | unique_count, most_frequent, avg_length |

---

### json_storage.py — JSON 文件读写

原子写入（写临时文件再替换），支持默认数据、验证器、自定义编码器。

```python
from Cross_Layer.json_storage import JSONStorage

storage = JSONStorage('data/config.json', default_data={'version': 1})
config = storage.read()
storage.write(config)

# 原子更新
storage.update(lambda d: d.update({'counter': d.get('counter', 0) + 1}))
```

**主要类：**
- `JSONStorage` — 主读写类
- `JSONValidator` — 数据验证（schema / type）
- `CustomJSONEncoder` — 支持 datetime 等非标准类型的编码器

---

### logger.py — 日志系统

带调用上下文（文件名、类名、函数名、行号）的日志记录器，自动注入 extra 信息。

```python
from Cross_Layer.logger import setup_logger, dir_exist

# 配置日志系统
log = setup_logger("my_module", level=logging.INFO)
log.info("操作完成")  # 自动附带 [filename:123 - MyClass.method] 信息

# 路径验证与创建
dir_exist("./data/output.txt", create_if_missing=True)
```

**主要函数：**
- `setup_logger(name, level, log_dir)` — 配置日志，返回 ContextLogger 实例
- `dir_exist(path, ...)` — 路径验证/创建，支持删除、异常控制
- `ContextLogger` — 带上下文注入的日志类
- `logger` — 模块级默认日志器

---

### timestamp_engine.py — 时间戳解析与标准化

自动识别 7 种时间格式，统一转换为 UTC DatetimeIndex，支持去重和重采样。

```python
from Cross_Layer.timestamp_engine import TimestampEngine

engine = TimestampEngine()

# 标准化时间列 → UTC DatetimeIndex
df = engine.normalize(df, 'timestamp')

# 清洗（处理重复值、时区）
df = engine.clean(df, 'timestamp', strategy={'duplicates': 'keep_last'})

# 重采样
df = engine.resample(df, freq='1h', method='linear')

# 金融数据（跳过周末）
df = engine.process_financial(df)
```

**支持格式：** ISO 8601、斜杠日期、文本月份、Unix 时间戳（秒/毫秒）、带时区格式

**重采样方法：** linear / ffill / bfill / nearest / zero / mean

---

### global_config.py — 全局配置（不改动）

```python
from Cross_Layer.global_config import setup_paths, ROOT_DIR, TSDB_HOST

setup_paths()          # 把 src 加入 sys.path
print(ROOT_DIR)        # X:\LOTT
print(TSDB_HOST)       # localhost
```

包含：路径常量、TSDB 连接参数、数据源默认值、日志配置。

---

### global_imports.py — 常用模块统一导入（不改动）

```python
from Cross_Layer.global_imports import *

pd.DataFrame(...)   # pandas
np.mean(arr)        # numpy
os.path.join(...)  # os
json.dumps(...)     # json
```

包含：numpy、pandas、datetime、os、json、requests、typing 常用类型。

---

## 依赖关系

```
notebooks / 其他模块
        │
        ▼
  global_config.py  ──→ setup_paths() 把 src 加入 sys.path
        │
        ▼
  global_imports.py ──→ pd / np / os / json 等常用模块
        │
        ▼
  detail.py          ──→ pandas, numpy
  json_storage.py    ──→ json, os, tempfile, shutil, logging
  logger.py          ──→ logging, os, pathlib, inspect
  timestamp_engine.py ──→ pandas, logging
```

---

## 已被删除的旧文件

| 旧文件 | 说明 |
|--------|------|
| `enhanceddataframe.py` | 多级列索引切片，已迁移至 `Data/DatabaseManage/column_selector.py` |
| `invaplot.py` | 无效值绘图组件，已废弃，使用 `Frontend/chart/ChartWidget` |
| `private_imports.py` | 私有导入聚合，已废弃，直接使用各模块自身 |

---

## 环境要求

```bash
pip install pandas numpy
pip install python-dateutil pytz   # timestamp_engine 依赖
pip install jsonschema            # JSONValidator schema 验证（可选）
```
