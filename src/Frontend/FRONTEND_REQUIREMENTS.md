# LOTT Frontend 需求与架构说明

## 一、概述

LOTT Frontend 是一个基于 **PyQt5 + pyqtgraph** 的量化交易可视化桌面客户端，采用 **三层面板结构** 设计，使用户能快速从数据浏览到回测结果分析全流程操作。

## 二、三层面板架构

```
┌──────────────────────────────────────────────────────────────┐
│                     MainWindow (主窗口)                       │
│  ┌──────────────────┬──────────────────┬───────────────────┐ │
│  │  图层1            │  图层2            │  图层3             │ │
│  │  DatabasePanel   │  VariablePanel   │  BacktestPanel    │ │
│  │  数据库总表浏览    │  策略变量分析      │  回测结果可视化     │ │
│  │                  │                  │                   │ │
│  │  • 列树导航       │  • 多折线图       │  • 价格图+标记     │ │
│  │  • 元数据查看     │  • Lagging控制    │  • 仓位柱状图     │ │
│  │  • 数据表预览     │  • 多Y轴         │  • 累计收益曲线    │ │
│  │  • 日期范围选择   │  • 变量列表管理    │  • 交易明细表     │ │
│  └──────────────────┴──────────────────┴───────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  辅助面板: InfoPanel (K线信息) + ChartToolbar (工具栏)     │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## 三、技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| GUI 框架 | PyQt5 | 跨平台桌面应用，成熟稳定 |
| 图表引擎 | pyqtgraph | 高性能实时绘图，比 matplotlib 快 10-100x |
| 暗色主题 | qdarkstyle | Qt 暗色主题样式表（可选依赖） |
| 数据处理 | pandas + numpy | DataFrame 操作 + 数值计算 |
| 数据库 | SQLAlchemy ORM | 通过 Data 层连接 SQLite/TimescaleDB |
| 配置管理 | JSON | FrontendConfig 单例 |
| 事件通信 | Qt Signal/Slot | SignalBus 单例统一管理 |

## 四、目录结构

```
src/Frontend/
├── __init__.py              # 包初始化，导出核心组件
├── run_frontend.py          # 🚀 启动入口（命令行 + 快捷函数）
├── ARCHITECTURE_COMPARISON.md  # VNPY vs VeighNa Studio 架构对比
├── FRONTEND_REQUIREMENTS.md    # 本文档
├── INTERFACE_DEFINITION.md     # 接口定义规范
├── BACKTEST_INTERFACE.md       # 回测接口数据结构
│
├── core/                    # 核心基础设施
│   ├── __init__.py
│   ├── config.py            # FrontendConfig 全局配置（单例）
│   ├── signal_bus.py        # SignalBus 信号总线（单例）
│   ├── data_manager.py      # DataManager 数据管理 + BarData 数据结构
│   └── data_proxy.py        # DataProxy 数据代理（缓存+降采样）
│
├── chart/                   # 图表引擎
│   ├── __init__.py
│   ├── chart_widget.py      # ChartWidget 图表主容器
│   ├── items/               # 图表元素
│   │   ├── base_item.py     # ChartItem 抽象基类
│   │   ├── candle_item.py   # CandleItem K线蜡烛图
│   │   ├── line_item.py     # LineItem 折线图
│   │   └── bar_item.py      # BarItem 柱状图（成交量）
│   ├── markers/             # 标记系统
│   │   ├── base_marker.py   # BaseMarker + MarkerType/Shape/Style 枚举
│   │   ├── trade_marker.py  # TradeMarker 交易信号标记（11种形状）
│   │   └── marker_manager.py # MarkerManager 批量管理+索引
│   ├── overlays/            # 叠加层
│   │   └── confidence_band.py # ConfidenceBand 置信区间带
│   └── cursor/              # 光标系统
│       └── crosshair.py     # ChartCursor 十字光标+坐标信息
│
├── panels/                  # 面板组件
│   ├── __init__.py          # 统一导出所有面板
│   ├── base_panel.py        # BasePanel 抽象基类（QDockWidget + ABC）
│   ├── info_panel.py        # InfoPanel K线/仓位/信号信息
│   ├── toolbar.py           # ChartToolbar 图表工具栏
│   ├── database/            # 📊 图层1：数据库面板
│   │   ├── __init__.py
│   │   ├── database_panel.py   # DatabasePanel 主面板
│   │   ├── column_tree.py      # ColumnTreeWidget 三级列树
│   │   ├── metadata_view.py    # MetadataViewWidget 元数据表
│   │   └── table_view.py       # TableViewWidget 数据预览表
│   ├── variables/           # 📈 图层2：变量面板
│   │   ├── __init__.py
│   │   ├── variable_panel.py   # VariablePanel 主面板
│   │   ├── variable_list.py    # VariableListWidget 变量列表管理
│   │   ├── multi_line_chart.py # MultiLineChartWidget 多折线图
│   │   ├── types.py            # VariableConfig 配置数据类
│   │   └── lagging_control.py  # LaggingControlWidget 滞后阶数控制
│   └── backtest/            # 📉 图层3：回测面板
│       ├── __init__.py
│       ├── backtest_panel.py   # BacktestPanel 主面板 + BacktestResult
│       ├── price_chart.py      # PriceChart 价格图+交易标记
│       ├── position_chart.py   # PositionChart 持仓柱状图
│       ├── return_chart.py     # ReturnChart 累计收益曲线
│       └── trade_list.py       # TradeList 交易明细表 + Trade 数据类
│
├── ui/                      # 用户界面
│   ├── __init__.py
│   ├── main_window.py       # MainWindow 主窗口
│   └── dock_manager.py      # DockManager Dock布局管理器
│
├── styles/                  # 样式系统  
│   ├── __init__.py
│   ├── theme.py             # ThemeManager + Theme + ColorScheme
│   └── chart_style.py       # ChartStyle + CandleStyle + VolumeStyle
│
├── utils/                   # 工具函数
│   ├── __init__.py
│   ├── data_utils.py        # 数据转换/降采样/LTTB算法
│   ├── date_utils.py        # 日期格式化/范围计算
│   └── export_utils.py      # 图表导出（PNG/CSV/Excel）
│
├── tests/                   # 测试用例
│   ├── __init__.py
│   ├── test_chart.py        # 图表模块测试
│   ├── test_core.py         # 核心模块测试
│   └── test_panels.py       # 面板模块测试
│
└── reference/               # 参考代码（vnpy 源码摘录）
    └── vnpy_reference/
```

## 五、启动方式

### 命令行启动

```bash
# 完整界面
python src/Frontend/run_frontend.py

# 仅数据库浏览器
python src/Frontend/run_frontend.py --mode database

# 仅回测可视化
python src/Frontend/run_frontend.py --mode backtest

# 仅变量分析
python src/Frontend/run_frontend.py --mode variables

# 指定数据库
python src/Frontend/run_frontend.py --mode database --db-path path/to/data.db
```

### Python / Notebook 调用

```python
# 方式1：完整界面
from Frontend.ui import MainWindow
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()

# 方式2：快捷启动数据库浏览器
from Frontend.run_frontend import quick_database
quick_database('path/to/data.db')

# 方式3：快捷启动回测可视化
from Frontend.run_frontend import quick_backtest
quick_backtest(backtest_result)
```

## 六、核心设计原则

1. **三层可独立使用**：每个面板可单独启动，不依赖其他图层
2. **信号驱动解耦**：SignalBus 单例通过 Qt 信号槽实现模块间通信
3. **缓存优先性能**：DataProxy 提供 LRU 缓存和 LTTB 降采样
4. **主题可切换**：ThemeManager 管理暗色/亮色/自定义主题
5. **与后端松耦合**：通过 DataOperation 接口连接 Data 层，支持 None 降级

## 七、依赖项

### 必需

```
PyQt5>=5.15.0
pyqtgraph>=0.13.0
pandas>=1.5.0
numpy>=1.21.0
```

### 可选

```
qdarkstyle>=3.0.0     # 暗色主题
scipy>=1.9.0          # 置信区间计算
```
