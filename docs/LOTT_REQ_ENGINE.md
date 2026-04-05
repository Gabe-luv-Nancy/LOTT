# LOTT_REQ_ENGINE — 回测与引擎需求文档

> 版本：v0.1.0 | 更新：2026-04-03 | 维护：LOTTDirector

---

## 一、现状

Backtest 模块完成度 80%，三大框架适配器均已实现。Service 模块完成度 70%，Returns 类待完善。

### 已有能力

| 组件 | 状态 |
| ---- | ---- |
| BacktestLayer（统一入口） | ✅ 完成 |
| UniConfig / UniData / UniStrategy / Signal / UniResult | ✅ 完成 |
| VectorBT Adapter | ✅ 完成 |
| Backtrader Adapter | ✅ 完成 |
| Backtesting.py Adapter | ✅ 完成 |
| DataFrameTransformer | ✅ 完成 |
| DataCache（LRU + TTL） | ✅ 完成 |
| DataQualityAnalyzer | ✅ 完成 |
| Returns（收益率计算） | ⚠️ 部分完成 |
| 交易日过滤（filter_trading_days） | ✅ 完成 |

---

## 二、已有 README（必读）

SSM 上岗前必须通读：
- `X:\LOTT\src\Backtest\README.md` — 适配器架构 + 接口规范详细
- `X:\LOTT\src\Service\README.md` — 服务层接口定义
- `X:\LOTT\src\Strategy\README.md` — 策略库索引

---

## 三、v0.2.0 待完成事项

### P0（必须）

1. **JSON 报告生成器**
   - 按 `src/README.md` 定义的 JSON Schema 生成结构化回测报告
   - 字段：`strategy_info` / `parameters` / `results.performance` / `trade_log` 等

2. **多资产组合回测**
   - 支持多品种同时回测
   - 组合保证金计算

### P1（重要）

3. **高级订单类型**
   - 止损单 / 止盈单 / 冰山订单 / 条件单

4. **并行回测**
   - 多策略 / 多参数并行执行
   - 使用 asyncio 或 celery 任务队列

5. **Returns 类完善**
   - 实现完整对数收益率计算
   - 支持复杂持仓期计算

### P2（扩展）

6. **实盘接口对接**
   - CTP 实盘交易接口
   - SimNow 模拟交易

---

## 四、SSM 权限范围

```
读：X:\LOTT\src\ 所有模块（理解上下文）
写：X:\LOTT\src\Backtest\
写：X:\LOTT\src\Service\
写：X:\LOTT\src\Strategy\
写：src/Strategy/（策略文件）
写：src/Backtest/results/（回测结果）
禁止：X:\LOTT\src\Data\ / X:\LOTT\src\Frontend\
```

---

## 五、交付物规范

每个任务完成后：
1. 代码写到对应模块目录
2. 执行记录追加到 `shared/docs/SSM_TASK_LOG.md`
3. 回测结果 JSON 输出到 `src/Backtest/results/`
4. 策略文件输出到 `src/Strategy/`

---

## 交付记录

| 日期 | 任务编号 | 变更内容 |
| ---- | -------- | -------- |
| 2026-04-05 | SSM-20260405-001 | 修正文档内三处共享路径引用为 LOTT 标准路径 |
