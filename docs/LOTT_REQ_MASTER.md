# LOTT_REQ_MASTER — 需求总纲

> 版本：v0.1.0 | 更新：2026-04-03 | 维护：LOTTDirector

---

## 一、项目概述

**LOTT = Libre Open-source Trading Terminal**

核心定位：开源免费 + AI 编程 + 本地运行，数据驱动的量化交易终端。

**技术栈**（已有）：
- Python 3.12 + pandas + numpy
- TimescaleDB（时序数据库）
- Redis + Redis Stream（缓存/消息队列）
- Backtrader / VectorBT / Backtesting.py（回测框架）
- PyQt5 + pyqtgraph（前端）

---

## 二、模块完成度

| 模块 | 完成度 | 状态 |
| ---- | ------ | ---- |
| Cross_Layer | 95% | 基本完成 |
| Data | 90% | 核心完成，TimescaleDB 待测试 |
| Backtest | 80% | 核心完成，适配器待优化 |
| Strategy | 85% | 策略库丰富，部分待完善 |
| Service | 70% | 核心完成，Returns 类待完善 |
| Frontend | 80% | 核心完成，测试与优化待开发 |
| Report | 60% | 基本完成，更多报告类型待开发 |

---

## 三、模块间依赖关系

```
Frontend ← Backtest + Service + Strategy
Backtest ← Service + Strategy
Service ← Data
Strategy ← Data
```

---

## 四、安全原则

1. **开源且内化** — AI 编程，用户全面认知系统
2. **自定义数据** — 自有数据库和数据源
3. **本地运行** — 数据本地存储
4. **完全隔离** — 在 `X:\LOTT\` 中运行

---

## 五、Human Gate 机制

```
代码 → Programmer 编写 → TestManager 验证 → Director 审查 → Gabriel 确认
```

Gabriel（你）只在以下情况介入：
1. 新需求/大变更
2. 版本发布前最终确认
3. Programmer 阻塞 > 2 小时
4. 紧急干预

---

## 六、下一步计划（v0.2.0 里程碑）

详见 `LOTT_ROADMAP.md`
