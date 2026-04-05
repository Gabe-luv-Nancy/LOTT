# Utils 工具模块

通用工具函数集合。

## 文件清单

| 文件 | 主要函数/类 | 说明 |
|------|------------|------|
| `data_utils.py` | `downsample_lttb()`, `to_ohlc_arrays()`, `normalize()` | 数据转换、LTTB降采样、归一化 |
| `date_utils.py` | `format_datetime()`, `parse_daterange()`, `trading_days()` | 日期格式化、交易日历 |
| `export_utils.py` | `export_chart_png()`, `export_data_csv()`, `export_data_excel()` | 图表和数据导出 |

## LTTB 降采样算法

Largest-Triangle-Three-Buckets 算法，在保持视觉保真度的同时将数据点数降低到指定数量：

```python
from Frontend.utils import downsample_lttb

# 将 10000 个数据点降采样到 500 个
x_down, y_down = downsample_lttb(x_array, y_array, target_points=500)
```

## 导出功能

```python
from Frontend.utils import export_chart_png, export_data_csv

# 导出图表为 PNG
export_chart_png(chart_widget, 'output.png', width=1920, height=1080)

# 导出数据为 CSV
export_data_csv(dataframe, 'output.csv')
```
