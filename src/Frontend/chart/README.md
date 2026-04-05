# Chart 图表引擎模块

基于 pyqtgraph 的高性能金融图表引擎，支持 K 线、折线、柱状图、交易标记、叠加层等。

## 子模块结构

```
chart/
├── chart_widget.py      # ChartWidget 图表主容器（整合所有子组件）
├── items/               # 图表绘制元素
│   ├── base_item.py     # ChartItem 抽象基类（定义 bindData/bindRange 接口）
│   ├── candle_item.py   # CandleItem K线蜡烛图（红涨绿跌 + 影线）
│   ├── line_item.py     # LineItem 折线图（均线/指标叠加）
│   └── bar_item.py      # BarItem 柱状图（成交量/持仓量）
├── markers/             # 交易标记系统
│   ├── base_marker.py   # BaseMarker + 枚举（MarkerType/Shape/Position/Style）
│   ├── trade_marker.py  # TradeMarker 交易信号标记（11种形状 ×4向上下左右= 多方向）
│   └── marker_manager.py # MarkerManager 批量管理（类型索引+策略索引+时间索引）
├── overlays/            # 叠加层
│   └── confidence_band.py # ConfidenceBand 置信区间带（半透明填充，支持多区间）
└── cursor/              # 光标系统
    └── crosshair.py     # ChartCursor 十字光标 + OHLCV 实时坐标标签
```

## 设计模式

- **组合模式**：ChartWidget 包含多个 ChartItem，每个 Item 独立绑定数据
- **工厂模式**：MarkerManager 根据 MarkerType 自动创建对应 Marker 实例
- **抽象模板**：ChartItem 定义 `bindData()`、`bindRange()` 等模板方法

## 性能优化

- pyqtgraph 硬件加速（OpenGL 可选）
- LTTB 降采样算法（大数据量时自动触发）
- Picture 缓存（避免重复绘制不变区域）
- 增量更新（新增 Bar 只绘制新增部分）
