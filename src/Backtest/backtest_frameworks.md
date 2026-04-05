<!--
  文档定位: 回测框架选型对比文档
  职责: 对比主流开源回测框架，说明LOTT选择VN.py的原因
  相关文档: README.md (UniBacktest统一回测框架实现)
  更新时间: 2026-03-18
-->

# 开源免费回测框架梳理

## Python 主流回测框架

| 框架 | 语言 | 优点 | 缺点 | 适合场景 |
|------|------|------|------|----------|
| **Backtrader** | Python | 简洁、文档全、扩展性强 | 无GUI、需自己搭建数据 | 中高频策略 |
| **VN.py** | Python | 中文文档丰富、实盘能力强 | 较重、安装复杂 | 国内实盘交易 |
| **Zipline** | Python | Quantopian 出品、严谨 | 已停止维护 | 学术研究 |
| **FreqTrade** | Python | 专注加密货币、Docker部署 | 加密货币专用 | 数字货币 |
| **QuantConnect** | Python/C# | 云端运行、数据丰富 | 免费有限制 | 多资产 |
| **Backtesting.py** | Python | 轻量、简单 | 功能有限 | 快速原型 |
| **VectorBT** | Python | 速度快、向量化 | 复杂策略难实现 | 高频分析 |

## 推荐：VN.py

### 优势
- ✅ 国内社区活跃，中文文档全
- ✅ 支持实盘对接（CTP、证券公司等）
- ✅ 模块化设计，回测/实盘一套代码
- ✅ 丰富的策略模板

### 安装
```bash
pip install vnpy
```

### 基础结构
```python
from vnpy.app.cta_backtester import CtaBacktesterApp
```

## LOTT 采用 VN.py

### 原因
1. 用户熟悉 VN.py 策略语法
2. 支持国内期货市场（AkShare 数据可对接）
3. 可扩展实盘交易

### 下一步
- [x] 安装 VN.py
- [x] 跑通示例策略
- [ ] 对接 AkShare 数据
- [ ] 开发自定义策略