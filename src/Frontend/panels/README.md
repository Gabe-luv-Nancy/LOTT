# Panels 面板模块

三层面板架构，每层可独立使用，也可组合在 MainWindow 中。

## 三层架构

| 图层 | 面板 | 功能 | 核心组件 |
|------|------|------|---------|
| 1 | `database/DatabasePanel` | 数据库总表浏览 | ColumnTreeWidget, MetadataViewWidget, TableViewWidget |
| 2 | `variables/VariablePanel` | 策略变量可视化 | VariableListWidget, MultiLineChartWidget, LaggingControlWidget |
| 3 | `backtest/BacktestPanel` | 回测结果可视化 | PriceChart, PositionChart, ReturnChart, TradeList |

## 公共组件

| 文件 | 类 | 说明 |
|------|-----|------|
| `base_panel.py` | `BasePanel` | 抽象基类（QDockWidget + ABC），定义 `setup_ui()`/`connect_signals()` 模板 |
| `info_panel.py` | `InfoPanel` | K线/仓位/信号信息展示面板 |
| `toolbar.py` | `ChartToolbar` | 图表工具栏（周期/类型/指标/主题/缩放控制） |

## 图层1：数据库面板 (`database/`)

- **DatabasePanel**: 主面板，整合列树+元数据+数据预览
- **ColumnTreeWidget**: 三级树（品种代码→名称→指标），列哈希为叶节点标识
- **MetadataViewWidget**: 显示 `_metacoldata` 表的行统计/数据质量
- **TableViewWidget**: 数据预览表格，支持分页/排序

## 图层2：变量面板 (`variables/`)

- **VariablePanel**: 主面板，整合变量列表+多折线图+lagging控制
- **VariableListWidget**: 变量管理列表（添加/删除/颜色/可见性/右键菜单）
- **MultiLineChartWidget**: 多变量折线图（多Y轴，同一时间轴）
- **LaggingControlWidget**: 滞后阶数控制（滑块+快捷按钮）
- **VariableConfig**: 变量配置数据类（颜色/lagging/线型/Y轴/置信区间）

## 图层3：回测面板 (`backtest/`)

- **BacktestPanel**: 主面板，接收 `BacktestResult` 数据包
- **PriceChart**: 价格折线图 + 交易标记（买卖点箭头）
- **PositionChart**: 持仓柱状图（多头正值/空头负值）
- **ReturnChart**: 累计收益曲线 + 基准对比 + 最大回撤标注
- **TradeList**: 交易明细表格（时间/方向/价格/数量/盈亏）
