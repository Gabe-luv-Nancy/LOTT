# TimescaleDB Docker 部署完整教程

> 目标：在 Docker Desktop 中运行 TimescaleDB，从电脑任意目录的 Python 脚本连接使用
> 适用系统：macOS / Windows (Docker Desktop)

---

## 一、Docker Desktop 安装与准备

### 1.1 安装 Docker Desktop

**macOS:**
```bash
# 方法1: Homebrew
brew install --cask docker

# 方法2: 官网下载
# https://www.docker.com/products/docker-desktop/
# 下载 .dmg 文件，双击安装
```

**Windows:**
```bash
# 官网下载 Docker Desktop
# https://www.docker.com/products/docker-desktop/
# 运行安装程序，开启 WSL 2 后端（推荐）
```

安装完成后启动 Docker Desktop，等待状态栏显示 "Docker Desktop is running"。

### 1.2 验证安装

```bash
docker --version
# Docker version 27.x.x, build xxxxxx

docker compose version
# Docker Compose version v2.x.x
```

### 1.3 配置 Docker Desktop 资源（重要）

打开 Docker Desktop → Settings → Resources：

| 设置项 | 推荐值 | 说明 |
|--------|--------|------|
| **Memory** | 至少 4 GB | TimescaleDB 最低要求 256MB，建议 4-8GB |
| **CPUs** | 至少 2 核 | 越多查询越快 |
| **Disk image size** | 至少 60 GB | 数据会持续增长 |
| **Disk image location** | 空间充足的盘 | 默认在系统盘 |

---

## 二、拉取 TimescaleDB 镜像

### 2.1 拉取官方镜像

```bash
# 拉取 TimescaleDB 最新版（基于 PostgreSQL 16）
docker pull timescale/timescaledb:latest-pg16

# 或指定版本（推荐锁定版本，生产环境不要用 latest）
docker pull timescale/timescaledb:2.17.0-pg16
```

验证镜像：
```bash
docker images | grep timescale
# timescale/timescaledb   2.17.0-pg16   xxxxxx   xxx MB
```

### 2.2 确认镜像可用

```bash
docker run --rm timescale/timescaledb:2.17.0-pg16 pg_lsversion
# TimescaleDB 2.17.0 (with PostgreSQL 16.6)
```

---

## 三、创建并启动容器

### 3.1 方式一：快速启动（命令行）

```bash
docker run -d \
  --name timescaledb \
  -e POSTGRES_DB=lott \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 \
  -v timescaledb_data:/var/lib/postgresql/data \
  -v /your/data/path:/data \
  --restart=unless-stopped \
  timescale/timescaledb:2.17.0-pg16
```

**参数说明：**

| 参数 | 含义 |
|------|------|
| `-d` | 后台运行 |
| `--name timescaledb` | 容器名字，后续用这个名字管理 |
| `-e POSTGRES_DB=lott` | 创建名为 lott 的数据库 |
| `-e POSTGRES_USER=postgres` | 用户名 |
| `-e POSTGRES_PASSWORD=xxx` | **密码**，必须改成强密码 |
| `-p 5432:5432` | 容器5432端口映射到主机5432（PostgreSQL默认端口） |
| `-v timescaledb_data:/var/lib/postgresql/data` | 数据持久化存储（Docker卷） |
| `-v /your/data/path:/data` | 把主机某个目录挂载进容器的 /data |
| `--restart=unless-stopped` | Docker重启时自动启动容器 |
| `-p 5432:5432` | 暴露端口供外部访问 |

### 3.2 方式二：docker-compose 管理（推荐）

在项目目录下创建 `docker-compose.yml`：

```yaml
version: "3.8"

services:
  timescaledb:
    image: timescale/timescaledb:2.17.0-pg16
    container_name: timescaledb
    environment:
      POSTGRES_DB: lott              # 数据库名
      POSTGRES_USER: postgres         # 用户名
      POSTGRES_PASSWORD: your_strong_password  # 改成你自己的密码
      # 时区设置
      TZ: Asia/Shanghai
    ports:
      - "5432:5432"                  # PostgreSQL 端口
    volumes:
      - timescaledb_data:/var/lib/postgresql/data  # 数据持久化
      - /your/data/path:/data        # 数据导入导出目录（改成你的实际路径）
      - ./init-scripts:/docker-entrypoint-initdb.d  # 初始化脚本目录
    restart: unless-stopped
    # 资源限制（可选）
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 2G

volumes:
  timescaledb_data:
```

启动：
```bash
docker compose up -d
```

停止：
```bash
docker compose down        # 停止，保留数据卷
docker compose down -v     # 停止并删除数据（危险！）
```

### 3.3 等待容器启动完成

```bash
# 查看容器状态
docker ps

# 查看启动日志，确认 TimescaleDB 扩展初始化成功
docker logs -f timescaledb
# 看到类似下面的输出说明成功：
# database system is ready to accept connections
# TimescaleDB extension initialization complete
```

### 3.4 初始化 TimescaleDB 扩展（首次运行）

等容器启动完成后，进入数据库执行：

```bash
# 进入容器内的 psql 命令行
docker exec -it timescaledb psql -U postgres -d lott

# 在 SQL 命令行里执行：
CREATE EXTENSION IF NOT EXISTS timescaledb;

# 验证扩展是否安装成功：
\dx timescaledb
# 应该看到 timescaledb 版本信息

# 退出：
\q
```

---

## 四、从任意目录的 Python 连接 TimescaleDB

### 4.1 安装 Python 客户端

```bash
# 在任意虚拟环境或系统环境安装
pip install psycopg2-binary sqlalchemy timescaledb

# 或只装 psycopg2（最轻量）
pip install psycopg2-binary
```

### 4.2 基础连接（psycopg2）

在任何目录下创建 Python 文件都可以使用：

```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",      # Docker Desktop 在本机，固定写 localhost
    port=5432,            # 容器映射的端口
    database="lott",       # 数据库名
    user="postgres",       # 用户名
    password="your_password"  # 改成你设置的密码
)

cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone())

# 验证 TimescaleDB 扩展
cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
print("TimescaleDB version:", cur.fetchone()[0])

cur.close()
conn.close()
```

### 4.3 使用 SQLAlchemy（ORM，推荐）

```python
from sqlalchemy import create_engine, text

# 连接字符串格式：
# postgresql://用户名:密码@主机:端口/数据库名
engine = create_engine(
    "postgresql://postgres:your_password@localhost:5432/lott",
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最多额外多少连接
    pool_pre_ping=True,   # 使用前检测连接是否有效
)

# 测试连接
with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("连接成功:", result.fetchone())

# 创建 Hypertable（TimescaleDB 核心）
with engine.connect() as conn:
    # 先创建普通表
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS futures_ohlcv (
            id          BIGSERIAL,
            symbol      VARCHAR(32) NOT NULL,
            exchange    VARCHAR(16) NOT NULL DEFAULT '',
            datetime    TIMESTAMPTZ NOT NULL,
            open        NUMERIC(12,4) NOT NULL,
            high        NUMERIC(12,4) NOT NULL,
            low         NUMERIC(12,4) NOT NULL,
            close       NUMERIC(12,4) NOT NULL,
            volume      BIGINT NOT NULL DEFAULT 0,
            hold        BIGINT NOT NULL DEFAULT 0
        )
    """))

    # 转为 Hypertable（TimescaleDB 核心：按时间自动分区）
    conn.execute(text("""
        SELECT create_hypertable(
            'futures_ohlcv',
            'datetime',
            if_not_exists => TRUE
        )
    """))
    conn.commit()

print("Hypertable 创建成功！")
```

### 4.4 配置环境变量（更安全）

不要把密码写死在代码里。在项目根目录创建 `.env` 文件：

```bash
# .env 文件（不要提交到 git！）
PG_HOST=localhost
PG_PORT=5432
PG_DB=lott
PG_USER=postgres
PG_PASSWORD=your_strong_password
```

Python 中使用：

```python
import os
from dotenv import load_dotenv
load_dotenv()  # 加载 .env 文件

from sqlalchemy import create_engine

engine = create_engine(
    f"postgresql://{os.getenv('PG_USER')}:{os.getenv('PG_PASSWORD')}"
    f"@{os.getenv('PG_HOST')}:{os.getenv('PG_PORT')}/{os.getenv('PG_DB')}"
)
```

安装 dotenv：
```bash
pip install python-dotenv
```

---

## 五、Docker Desktop 的资源与网络配置

### 5.1 为什么键盘鼠标参数和数据库有关？

如果你看到的是 Docker Desktop 界面里的设置向导，这是 Docker Desktop 的 **Resources 配置面板**，用于分配容器可用的硬件资源（不是键鼠输入）。设置建议：

**macOS:** Docker Desktop → Settings → Resources:
- Memory: 8 GB（最低 4 GB）
- CPUs: 4
- Swap: 2 GB
- Disk image size: 100 GB

**Windows (WSL 2):** Docker Desktop → Settings → Resources:
- WSL integration: 开启
- Memory: 8 GB
- CPUs: 4

### 5.2 端口冲突检查

如果主机 5432 端口已被占用（其他 PostgreSQL 正在运行），换一个端口：

```yaml
# docker-compose.yml 中
ports:
  - "5433:5432"    # 主机5433映射到容器5432
```

然后 Python 连接时改端口：
```python
host="localhost", port=5433
```

---

## 六、导入现有 CSV 数据到 TimescaleDB

```python
import pandas as pd
from sqlalchemy import create_engine, text

engine = create_engine(
    "postgresql://postgres:your_password@localhost:5432/lott"
)

# 读取 CSV
df = pd.read_csv("/root/.openclaw/DL/minute_history/INE/sc2604_1m_history.csv")
df["datetime"] = pd.to_datetime(df["datetime"])
df["symbol"] = "sc2604"
df["exchange"] = "INE"

# 批量导入（10万行/秒级别）
df.to_sql(
    name="futures_ohlcv",
    con=engine,
    if_exists="append",   # 追加，不覆盖
    index=False,
    method="multi",
    chunksize=10000,      # 每批1万行
)
print(f"导入完成: {len(df)} 行")
```

---

## 七、日常管理命令

```bash
# 查看容器状态
docker ps

# 查看实时日志
docker logs -f timescaledb

# 进入 psql 命令行
docker exec -it timescaledb psql -U postgres -d lott

# 备份数据库
docker exec timescaledb pg_dump -U postgres lott > lott_backup.sql

# 恢复数据库
docker exec -i timescaledb psql -U postgres -d lott < lott_backup.sql

# 重启容器
docker restart timescaledb

# 完全重建（清空数据）
docker compose down -v && docker compose up -d

# 查看数据卷大小
docker system df -v
```

---

## 八、常见问题

**Q: 容器启动后立刻退出**
```bash
docker logs timescaledb
# 看具体报错，可能是密码格式问题或端口占用
```

**Q: Python 连接报 `connection refused`**
- 确认容器在运行: `docker ps`
- 确认端口映射: `docker port timescaledb`
- 确认防火墙: Windows 防火墙可能阻止 5432 端口

**Q: 数据导入很慢**
- 批量插入: 每次 5000-10000 行
- 关闭索引后再导入，建完数据再开索引
- Docker Desktop 分配更多内存

**Q: 如何从其他电脑连接？**
```yaml
# docker-compose.yml 中，把 localhost 改成 0.0.0.0
ports:
  - "0.0.0.0:5432:5432"
```
然后 Python 的 host 改成那台电脑的 IP。

---

## 九、完整 docker-compose.yml 模板

```yaml
version: "3.8"

services:
  timescaledb:
    image: timescale/timescaledb:2.17.0-pg16
    container_name: timescaledb
    environment:
      POSTGRES_DB: lott
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: your_strong_password
      TZ: Asia/Shanghai
    ports:
      - "5432:5432"
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
      - /root/.openclaw/DL:/data:ro
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G

volumes:
  timescaledb_data:
```

启动：
```bash
docker compose up -d
```
