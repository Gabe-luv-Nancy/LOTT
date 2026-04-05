# Styles 样式模块

主题管理和图表样式配置。

## 文件清单

| 文件 | 类 | 说明 |
|------|-----|------|
| `theme.py` | `ThemeManager`, `Theme`, `ColorScheme` | 全局主题管理（单例），暗色/亮色主题，颜色方案 |
| `chart_style.py` | `ChartStyle`, `CandleStyle`, `VolumeStyle`, `LineStyle` | 图表元素样式配置 |

## ThemeManager

- **单例模式**：全局唯一
- **预设主题**：`DARK_THEME`（默认）、`LIGHT_THEME`
- **颜色方案**：`ColorScheme` 定义背景色、前景色、涨/跌色、网格色等
- **切换信号**：`sigThemeChanged` 通知所有组件刷新样式
- **自定义主题**：支持注册自定义 Theme 对象

## ChartStyle

- **CandleStyle**: 涨色/跌色/影线/填充/边框配置
- **VolumeStyle**: 成交量柱状图的颜色/透明度
- **LineStyle**: 折线的颜色/宽度/虚线模式

## 与 qdarkstyle 的关系

- `qdarkstyle` 管理 Qt Widget 的全局 QSS 样式（按钮、列表、输入框等）
- `ThemeManager` 管理 pyqtgraph 图表的颜色配置（独立于 QSS）
- 两者协同：切换主题时同时更新 QSS 和图表颜色
