# vnpy 参考代码说明

## 概述

本文件夹包含 vnpy 的图表实现参考代码，用于指导 Frontend 图表模块的开发。

## 文件结构

```
vnpy_reference/
├── README.md           # 本文档
├── widget.py           # 主图表组件参考
├── base.py             # 图表元素基类参考
├── item.py             # 具体图表元素参考
├── cursor.py           # 光标系统参考
└── manager.py          # 管理器参考
```

## 核心参考点

### 1. ChartWidget (widget.py)

参考要点：
- 使用 `pg.GraphicsLayout` 支持多绘图区域
- `add_plot()` 方法添加绘图区域
- `add_item()` 方法添加图表元素
- X 轴联动实现

### 2. ChartItem (base.py)

参考要点：
- 继承 `pg.GraphicsObject`
- 使用 `QPicture` 缓存绘制结果
- `_draw_bar_picture()` 绘制单个数据点
- `paint()` 方法实现高效绘制

### 3. 具体元素 (item.py)

参考要点：
- `CandleItem`: K线绘制
- `VolumeItem`: 成交量柱状图
- 涨跌颜色区分

### 4. ChartCursor (cursor.py)

参考要点：
- 十字线绘制
- 多图表联动
- 信息面板显示

## 使用方式

这些参考代码仅用于学习参考，不应直接复制使用。开发时应：

1. 理解设计思路
2. 结合 LOTT 项目需求进行调整
3. 遵循 Frontend 模块的接口规范
4. 正确引用上游模块（Data、Cross_Layer 等）

## 注意事项

1. vnpy 代码采用 MIT 许可证
2. 需要适配 LOTT 的数据结构（BarData）
3. 需要集成 SignalBus 信号系统
4. 需要支持 Frontend 的标记系统