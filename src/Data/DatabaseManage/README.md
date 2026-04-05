# DatabaseManage 模块文档

> **更新时间**: 2026-03-22
> **角色调整**: 本模块已降级为**其他数据库配置的备份脚本**存放目录，**不推荐在新代码中使用**。
> - **主数据层**: DataManage + TimescaleDB（推荐）
> - **备份/特殊场景**: 本目录下的脚本（SQLite / PostgreSQL / MySQL）

---

## ⚠️ 重要说明

| 模块 | 数据库 | 用途 |
|------|--------|------|
| **DataManage** | ✅ TimescaleDB | 中频数据（1min+）批量导入读写（推荐） |
| **DatabaseManage** | ⚠️ SQLite/PG/MySQL | 备份脚本，仅特殊场景使用 |

**2026-03-22 决策**：DataManage 技术选型已统一转向 TimescaleDB，方便与 DataFeed 共用同一实例。本模块保留作为其他数据库配置的备份。

---

## 一、备份脚本说明

本目录下的脚本主要用于以下**特殊场景**：
- SQLite：本地开发调试（轻量、无依赖）
- PostgreSQL：已有 PostgreSQL 基础设施的团队
- MySQL：分表方案（按合约分表 vs TimescaleDB 长表）

**一般情况请使用 DataManage + TimescaleDB**。

## 二、目录结构

```
DatabaseManage/
├── README.md              # 本文档
├── __init__.py            # 模块入口
├── database_config.py     # 数据库配置（SQLite/PG/MySQL）
├── database_connect.py    # 数据库连接管理
├── database_operation.py  # CRUD 操作
├── database_tables.py    # 表结构管理
├── column_selector.py     # 列选择器
├── utils.py              # 工具函数
└── backup_scripts/        # ⭐ 备份脚本存放
    ├── sqlite_backup.py   # SQLite 备份
    ├── pg_backup.py       # PostgreSQL 备份
    └── mysql_backup.py    # MySQL 备份
```

## 三、备份脚本用法

```python
# SQLite 备份
from backup_scripts.sqlite_backup import backup_sqlite
backup_sqlite(source_db, dest_file)

# PostgreSQL 备份
from backup_scripts.pg_backup import backup_pg
backup_pg(host, port, dbname, user, password, dest_dir)
```

## 四、技术框架（备份用）

| 组件 | 说明 |
|------|------|
| **SQLite3** | Python 标准库 |
| **psycopg2** | PostgreSQL |
| **pymysql** | MySQL |
| **pandas** | 数据处理 |
| **SQLAlchemy** | ORM + 连接管理 |

## 五、已实现功能（备份）

- [x] SQLite 数据库配置与连接
- [x] PostgreSQL 连接实现
- [x] MySQL 分表管理实现
- [x] 批量数据插入、更新、删除
- [x] 备份脚本（SQLite / PG / MySQL）

## 六、核心类定义

| 类名 | 职责 |
|------|------|
| DatabaseConfig | 数据库配置管理 |
| DatabaseConnect | 连接管理 |
| DatabaseOperation | CRUD 操作 |
| DatabaseTables | 表结构管理 |
| ColumnSelector | 动态列选择 |
| Utils | 工具函数 |

---

*本文档仅作备份参考，新项目请使用 DataManage + TimescaleDB*
