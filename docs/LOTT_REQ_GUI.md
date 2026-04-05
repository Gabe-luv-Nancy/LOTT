# LOTT_REQ_GUI — 前端需求文档

> 版本：v0.1.0 | 更新：2026-04-03 | 维护：LOTTDirector

---

## 一、现状

Frontend 模块完成度 80%，vnpy 风格三层面板核心功能已实现。

### 已有能力

| 组件 | 状态 |
| ---- | ---- |
| MainWindow + DockManager | ✅ 完成 |
| ChartWidget + CandleItem + LineItem + BarItem | ✅ 完成 |
| MarkerManager（11种交易标记） | ✅ 完成 |
| ChartCursor（十字光标） | ✅ 完成 |
| DatabasePanel（三级列树 + 元数据 + 预览） | ✅ 完成 |
| VariablePanel（多折线图 + Lagging 控制） | ✅ 完成 |
| BacktestPanel（价格图 + 持仓 + 收益曲线 + 交易明细） | ✅ 完成 |
| SignalBus（事件总线） | ✅ 完成 |
| ThemeManager（暗色主题） | ✅ 完成 |
| DataProxy（缓存 + LTTB 降采样） | ✅ 完成 |

---

## 二、已有文档（必读）

FDM 上岗前必须通读：
- `X:\LOTT\src\Frontend\FRONTEND_REQUIREMENTS.md` — 完整需求说明（vnpy 风格三层面板）
- `X:\LOTT\src\Frontend\ARCHITECTURE_COMPARISON.md` — VNPY vs VeighNa Studio 对比
- `X:\LOTT\src\Frontend\INTERFACE_DEFINITION.md` — 接口定义规范
- `X:\LOTT\src\Frontend\reference\vnpy_reference\README.md` — vnpy 参考

---

## 三、v0.2.0 待完成事项

### P0（必须）

1. **单元测试**
   - chart 模块测试
   - core 模块测试
   - panels 模块测试

2. **性能优化**
   - 大数据量渲染优化
   - LTTB 降采样参数调优

### P1（重要）

3. **文档完善**
   - API 文档补全
   - 用户使用指南

4. **报告导出扩展**
   - PDF 报告生成
   - Excel 报告扩展

### P2（扩展）

5. **VS Code 插件**
   - Jupyter Notebook 集成
   - 策略脚本编辑 + 即时交互

---

## 四、FDM 权限范围

```
读：X:\LOTT\src\ 所有模块（理解上下文）
写：X:\LOTT\src\Frontend\
写：X:\LOTT\src\Report\
禁止：X:\LOTT\src\Data\ / X:\LOTT\src\Engine\
```

---

## 五、交付物规范

每个任务完成后：
1. 代码写到 `X:\LOTT\src\Frontend\` 或 `X:\LOTT\src\Report\`
2. 执行记录追加到 `src/Frontend/FDM_TASK_LOG.md`
3. 测试脚本放到 `src/Frontend/tests/`
