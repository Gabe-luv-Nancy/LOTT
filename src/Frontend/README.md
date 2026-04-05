# Frontend — LOTT 可视化前端

> LOTT 交易终端的图形界面模块，基于 PyQt5 + pyqtgraph。

---

## 架构概览

```
src/Frontend/
├── chart/           K线图、折线图、标记、光标组件
├── panels/          三层面板（DatabasePanel / VariablePanel / BacktestPanel）
├── core/            核心（SignalBus / DataProxy / DataManager）
├── ui/              主窗口、Dock管理器
├── styles/          主题系统（暗色主题）
├── utils/           工具函数
└── tests/           单元测试
```

---

## 核心功能

### Chart 模块（图表）
- **CandleItem** — K线蜡烛图
- **LineItem** — 折线图（支持多 Series 叠加）
- **BarItem** — 柱状图
- **Crosshair** — 十字光标
- **MarkerManager** — 11种交易标记（入场/出场/止损/止盈等）
- **ConfidenceBand** — 置信区间

### 三层面板
| 面板 | 功能 |
|------|------|
| DatabasePanel | 元数据树形导航 + 列信息 + 数据预览 |
| VariablePanel | 多折线图 + Lagging 滞后控制 |
| BacktestPanel | 回测价格图 + 持仓图 + 收益曲线 + 交易明细 |

### SignalBus（事件总线）
- 模块间解耦通信
- 支持 `trade_signal` / `data_update` / `backtest_result` 等事件

---

## 快速开始

```python
from ui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication
import sys

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec_()
```

---

## 接口定义

详见 `INTERFACE_DEFINITION.md`

---

## 状态

v0.2.0 — 核心功能完成，单元测试补全中
