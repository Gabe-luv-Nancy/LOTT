# Report 模块文档

## 模块概述

Report 模块是 LOTT 项目的报告生成层，负责生成各类数据分析和回测报告。该模块提供 DataFrame 列信息报告、多级索引报告等功能，支持导出为 Excel 格式。

### 核心特性

- **列信息报告**: 自动分析 DataFrame 列的结构和统计信息
- **多级索引支持**: 原生支持 MultiIndex 列名分析
- **Excel 导出**: 生成格式化的 Excel 报告
- **数据摘要**: 自动生成数据概览统计

## 文件结构

```
Report/
├── __init__.py              # 模块入口
├── multiindex_report.py     # 多级索引报告生成
└── README.md                # 本文档
```

## 核心组件说明

### 1. multiindex_report（多级索引报告）

**文件**: `multiindex_report.py`

**函数**: `multiindex_report(df, filename)`

**功能**: 生成 DataFrame 列信息报告，输出为 Excel 文件

**参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `df` | pd.DataFrame | 必填 | 要分析的 DataFrame |
| `filename` | str | "multiindex_report.xlsx" | 输出文件路径 |

**返回值**: `pd.DataFrame` - 列信息数据框

**生成的报告内容**:

| 列名 | 说明 |
|------|------|
| 列索引 | 列的序号 |
| 级别_0 | 第一级列名（代码） |
| 级别_1 | 第二级列名（名称） |
| 级别_2 | 第三级列名（指标） |
| ... | 更多级别（如有多级索引） |
| 非空值数量 | 该列非空值的数量 |
| 空值数量 | 该列空值的数量 |
| 总行数 | 数据总行数 |
| 空值比例(%) | 空值占比百分比 |

**摘要信息**:

| 统计项目 | 数值示例 |
|----------|----------|
| 总行数 | 252 |
| 总列数 | 50 |
| 数据形状 | 252行×50列 |

**使用示例**:

```python
import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *
from multiindex_report import multiindex_report

# 基本用法
result = multiindex_report(data, "X:/LOTT/my_reports/analysis.xlsx")

# 查看返回的列信息
print(result.head())

# 自定义输出路径
multiindex_report(
    df, 
    filename="X:/LOTT/reports/etf_data_report.xlsx"
)
```

**Excel 输出格式**:

报告生成一个 Excel 文件，包含一个工作表"列信息报告"：

```
┌─────────────────────────────────────────────────────┐
│ DataFrame列信息报告 - 共50列                         │
├─────────────────────────────────────────────────────┤
│ 列索引 │ 级别_0 │ 级别_1 │ 级别_2 │ 非空值数量 │ ... │
├─────────────────────────────────────────────────────┤
│   0    │ 510050 │ 50ETF  │ 收盘价 │    252    │ ... │
│   1    │ 510050 │ 50ETF  │ 成交量 │    250    │ ... │
│  ...   │  ...   │  ...   │  ...   │    ...    │ ... │
├─────────────────────────────────────────────────────┤
│                                                      │
│ 数据摘要                                             │
├─────────────────────────────────────────────────────┤
│ 统计项目    │ 数值                                   │
│ 总行数      │ 252                                    │
│ 总列数      │ 50                                     │
│ 数据形状    │ 252行×50列                             │
└─────────────────────────────────────────────────────┘
```

## 技术框架

- **Python 版本**: 3.8+
- **核心依赖**:
  - pandas >= 1.3.0
  - openpyxl >= 3.0.0 (Excel 写入)

## 现有代码实现情况

| 组件 | 实现状态 | 说明 |
|------|----------|------|
| multiindex_report | ✅ 完成 | 基本功能已实现 |
| Excel 格式化 | ✅ 完成 | 标题和摘要格式化 |
| 多级索引支持 | ✅ 完成 | 支持任意级别 |
| __init__.py | ✅ 完成 | 新增模块入口文件 |

### 最近修复

1. **新增 __init__.py**: 创建了模块入口文件，支持 `from Report import multiindex_report`

## 尚未完成的需求

1. **更多报告类型**: 
   - 数据质量报告
   - 回测结果报告
   - 策略性能报告

2. **报告模板**: 支持自定义报告模板

3. **图表嵌入**: 在 Excel 中嵌入数据可视化图表

4. **PDF 导出**: 支持 PDF 格式报告

5. **定时报告**: 支持定时生成和发送报告

## 下一步修改需求

1. **报告类重构**: 将函数封装为报告类，支持链式调用
2. **样式定制**: 支持自定义 Excel 样式
3. **多格式支持**: 支持 HTML、Markdown 等格式
4. **批量报告**: 支持批量生成多个报告
5. **报告管理**: 报告历史记录和版本管理

## 对外接口

```python
from Report import (
    multiindex_report,    # 多级索引报告生成函数
)
```

## 使用场景

### 场景 1: ETF 数据质量检查

```python
# 加载 ETF 数据
etf_data = pd.read_excel("etf_data.xlsx", header=[0,1,2], index_col=0)

# 生成报告
multiindex_report(etf_data, "reports/etf_quality_report.xlsx")
```

### 场景 2: 回测结果分析

```python
# 获取回测结果
backtest_result = backtest.run()

# 生成报告
multiindex_report(
    backtest_result.trades, 
    "reports/backtest_trades_report.xlsx"
)
```

### 场景 3: 数据导入验证

```python
# 导入数据后验证
data_op.add(new_data)
report = multiindex_report(new_data, "reports/import_validation.xlsx")

# 检查空值比例过高的列
high_missing = report[report['空值比例(%)'] > 50]
if len(high_missing) > 0:
    print(f"警告: {len(high_missing)} 列空值比例超过 50%")
```

## 注意事项

1. **输出目录**: 确保输出目录存在，函数会自动创建
2. **文件覆盖**: 同名文件会被覆盖
3. **大文件**: 大型 DataFrame 可能需要较长处理时间
4. **编码**: Excel 文件使用 UTF-8 编码