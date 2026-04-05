# DataManage 数据操作层文档

> **更新时间**: 2026-03-22
> **技术选型**: TimescaleDB（与 DataFeed 统一，方便复用）

---

## 一、概述

本模块负责**中频数据**（1min 及以上 K 线）的批量导入与读写操作，数据统一写入 **TimescaleDB** 时序数据库。

> ⚠️ **与 DataFeed 的分工（2026-03-22 明确）**
> 
> - **DataFeed**: Tick 高频数据（毫秒级实时行情）→ TimescaleDB
> - **DataManage**: 中频数据（1min+ K 线）→ TimescaleDB（同一实例）
> - **两者共用 TimescaleDB框架**，但是不一定是一个数据库啊！tick应该是一个数据库，然后中频数据是一个数据库，按数据频率分层存储

**核心职责**：

- 原始文件（JSON / Excel / CSV）批量导入 TimescaleDB：
- 【原始文件中表格可能存在各异的格式问题，例如：金融终端提取出来的数据可能有逐股输出，那就很像是正确的格式，代码、简称、OHLCV分别是字段/列名，但是也有可能是宽表“多股输出”，就比较复杂，首先他会在excel中占用三行，从上到下按次序写明代码、简称和数据类型（例如OHLCV数据等），然后第四行开始才是真正的数据，同时时间会默认记录在第一列，第一列也没有列名，第二列向右才是真正的数据；类似情况还有：excel占用一行或是占用你十多行，写明各种数据来源等，数据也是同样排列。】所以DataManage这里需要再导入数据库前设置专用的脚本，基于规则的脚本，来处理各种常见（基于规则肯定就不能穷尽）的excel数据表。
- 中频 K 线数据的增删查改
- 数据查询缓存加速

## 二、技术框架

| 组件              | 说明                               |
| --------------- | -------------------------------- |
| **TimescaleDB** | 时序数据库（与 DataFeed 共用实例）           |
| **pandas**      | >= 1.5.0，数据处理                    |
| **SQLAlchemy**  | >= 1.4.0，连接管理                    |
| **psycopg2**    | PostgreSQL/TimescaleDB Python 驱动 |

> **数据库地址**: TimescaleDB Docker 镜像，Host `localhost:5432`，数据库名 `lott`

## 三、目录结构

```
DataManage/
├── README.md              # 本文档
├── __init__.py           # 模块入口
├── timeseries_io.py      # TimescaleDB 读写操作 ⭐ 新增
├── local_access.py        # 本地文件读取（统一接口）
├── import_data.py        # 批量导入（JSON/Excel/CSV → TimescaleDB）
├── cache.py              # 数据查询缓存
└── data_operation.py     # 高级数据操作（供外部调用）
```

## 四、工作流程

```
原始文件（_json / _xl / _db / raw）
    ↓
import_data（加载为 DataFrame）
    ↓
timeseries_io（写入 TimescaleDB，长表格式）
    ↓
data_operation.query()（查询，支持缓存）
```

## 五、TimescaleDB 长表设计

### 中频数据表 (ohlcv_data)

| 列名        | 类型          | 说明                 |
| --------- | ----------- | ------------------ |
| symbol    | TEXT        | 合约代码（如 IF2406）     |
| exchange  | TEXT        | 交易所（如 CFFEX）       |
| timeframe | TEXT        | 周期（1min/5min/1day） |
| time      | TIMESTAMPTZ | K 线开始时间            |
| open      | DOUBLE      | 开盘价                |
| high      | DOUBLE      | 最高价                |
| low       | DOUBLE      | 最低价                |
| close     | DOUBLE      | 收盘价                |
| volume    | DOUBLE      | 成交量                |

> 与 DataFeed 的 `tick_data` 表完全独立，通过 `symbol + time` 组合查询。

## 六、核心类定义

| 类名            | 职责                                   |
| ------------- | ------------------------------------ |
| TimescaleIO   | TimescaleDB 读写操作（insert/query OHLCV） |
| DataOperation | 高级数据操作（add/query，外部调用入口）             |
| LocalData     | 本地文件读取（JSON/Excel/CSV）               |
| DataCache     | 数据查询缓存                               |

## 七、对外接口

```python
from Data.DataManage import DataOperation, LocalData

# 1. 加载文件
loader = LocalData()
df = loader.load_json_data('path/to/data.json')

# 2. 写入 TimescaleDB
from Data.DataManage.timeseries_io import TimescaleIO
ts_io = TimescaleIO()
ts_io.insert_ohlcv(df)

# 3. 查询
result = ts_io.query_ohlcv(symbol='IF2406', timeframe='1min', start='2024-01-01')
```

## 八、待实现功能 (PENDING)

- [ ] P0 timeseries_io.py: TimescaleDB 读写核心实现
- [ ] P0 import_data.py: 重构为 TimescaleDB 批量导入
- [ ] P1 data_operation.py: 适配 TimescaleDB 接口
- [ ] P1 缓存层优化

## 九、Notebook 验证状态

| Notebook                      | 状态                  |
| ----------------------------- | ------------------- |
| 02_data_manage_handbook.ipynb | 📋 待更新为 TimescaleDB |
| 04_test_data_io.ipynb         | 📋 待更新为 TimescaleDB |

---

*本文档遵循 README_PROTOTYPE.md 规范*
