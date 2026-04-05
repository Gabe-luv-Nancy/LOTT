# LOTT_REQ_DATA — 数据层需求文档

> 版本：v0.1.0 | 更新：2026-04-03 | 维护：LOTTDirector

---

## 一、现状

Data 模块完成度 90%，核心功能已实现，TimescaleDB 待完整测试。

### 已有能力

| 组件 | 状态 |
| ---- | ---- |
| DatabaseConfig | ✅ 完成 |
| DatabaseConnection（单例） | ✅ 完成 |
| Schema（表结构管理） | ✅ 完成 |
| MetaColData / TimeSeriesData 表 | ✅ 完成 |
| DatabaseOperations | ✅ 完成 |
| TimescaleDBOperations（核心功能） | ⚠️ 部分完成 |
| DataOperation | ✅ 完成 |
| LocalData（JSON/Excel） | ✅ 完成 |
| import_data | ✅ 完成 |

---

## 二、已有 README（必读）

DDB 上岗前必须通读：
- `X:\LOTT\src\Data\DatabaseManage\README.md` — 数据库基础设施详细接口
- `X:\LOTT\src\Data\DataManage\README.md` — 数据操作层说明
- `X:\LOTT\src\Data\DataSource\README.md` — 源数据层说明
- `X:\LOTT\src\Data\DatabaseManage\TimescaleDB\README.md` — TimescaleDB 专项说明

---

## 三、v0.2.0 待完成事项

### P0（必须）

1. **TimescaleDB 完整测试**
   - 超表创建和分区策略验证
   - 压缩策略和保留策略配置
   - 连续聚合（Continuous Aggregate）验证

2. **数据版本控制**
   - 实现 Data Version Control 机制
   - 版本间增量同步

### P1（重要）

3. **断点续传机制**
   - 网络中断后从断点恢复
   - 已有部分设计，需实现

4. **数据备份恢复**
   - 自动备份策略
   - 指定时间点恢复

5. **实时行情接入（CTP/SimNow）**
   - DataFeed 子模块 Docker 已就绪
   - 待配置 SimNow 连接参数

---

## 四、DDB 权限范围

```
读：X:\LOTT\src\Data\ 所有文件（理解上下文）
写：X:\LOTT\src\Data\（业务代码）
写：src/Data/ddb_output/（交付物）
写：src/Data/issues/（异常记录）
禁止：X:\LOTT\src\Engine\ / X:\LOTT\src\GUI\
```

---

## 五、交付物规范

每个任务完成后：
1. 代码写到 `X:\LOTT\src\Data\`
2. 执行记录追加到 `src/Data/DDB_TASK_LOG.md`
3. 数据交付物放到 `src/Data/ddb_output/`
4. 异常写入 `src/Data/issues/`
