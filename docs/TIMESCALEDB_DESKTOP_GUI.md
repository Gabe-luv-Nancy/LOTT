# TimescaleDB Docker Desktop 图形界面部署教程

> 目标：通过 Docker Desktop 可视化界面完成所有操作，不需要任何命令行

---

## 一、拉取镜像（Images 页面）

打开 Docker Desktop → 顶部菜单栏点击 **Images**

1. 点击右上角 **Pull** 按钮
2. 在 "Image name" 输入框填入：
   ```
   timescale/timescaledb:2.17.0-pg16
   ```
3. 点击 **Pull** 按钮
4. 等待下载完成（约 500MB），进度条走完即可

> 验证：下载完成后，Images 列表里会出现 `timescale/timescaledb` 这行

---

## 二、创建并运行容器（Containers 页面）

打开 Docker Desktop → 左侧点击 **Containers**

### 步骤 1：点击新建

点击右上角 **Create** 按钮（或者 **New** 按钮）

### 步骤 2：选择镜像

在弹出的镜像列表里，找到 `timescale/timescaledb:2.17.0-pg16`，点击右边的 **Run**

> 如果没有出现，点击 "Image name" 手动输入 `timescale/timescaledb:2.17.0-pg16` 然后 Run

### 步骤 3：填写容器配置（核心界面）

弹出的配置面板填写以下内容：

| 配置项 | 填写内容 |
|--------|---------|
| **Container name** | `timescaledb` |
| **Host port** | `5432` |
| **Container port** | `5432` |

> 端口映射：将容器的 5432（PG默认端口）映射到主机的 5432

### 步骤 4：设置环境变量

点击 **Advanced** 或 **Environment variables** 展开，找到或添加以下变量：

| 变量名 | 值 |
|--------|---|
| `POSTGRES_DB` | `lott` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | `你的密码`（自己设一个强密码）|

### 步骤 5：设置数据持久化（Volumes）

点击 **Volumes** → **New volume**

| 配置项 | 填写内容 |
|--------|---------|
| **Volume name** | `timescaledb_data` |
| **Container mount path** | `/var/lib/postgresql/data` |

> 作用：删除容器后数据不会丢失

### 步骤 6：设置自动重启

点击 **Restart policy** 下拉菜单，选择 `unless-stopped`

### 步骤 7：完成创建

点击 **Run** 或 **Create**

> 如果 "Host port" 那行要求输入格式是 `5432:5432`（宿主机:容器），就按这个格式填

---

## 三、验证容器运行状态

回到 **Containers** 页面，找到 `timescaledb` 容器：

| 状态颜色 | 含义 |
|---------|------|
| 🟢 绿色 | 运行中 ✅ |
| 🔴 红色 | 已停止 |
| 🟡 黄色 | 启动中 |

点击容器名字 `timescaledb`，可以看到详情：

- **Logs** 标签页 → 查看启动日志
- **Terminal** 标签页 → 打开容器内的命令行
- **Inspect** 标签页 → 查看容器完整配置

---

## 四、初始化 TimescaleDB 扩展

### 方式一：界面 Terminal（推荐）

在容器详情页点击 **Terminal** 标签页

输入：
```bash
psql -U postgres -d lott
```

然后输入 SQL（注意分号）：

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
\dx timescaledb
\q
```

### 方式二：Windows/macOS 本地 psql

在电脑的终端（不是容器内）执行：

```bash
# Windows：打开 PowerShell 或 CMD
# macOS：打开 Terminal

psql -h localhost -p 5432 -U postgres -d lott
```

然后同样输入：
```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

> 如果提示 `psql: command not found`，需要先安装 PostgreSQL 客户端：
> - macOS: `brew install postgresql`
> - Windows: 下载 https://www.postgresql.org/download/windows/

---

## 五、从 Python 连接（任意目录）

安装 Python 包（任意虚拟环境）：
```bash
pip install psycopg2-binary
```

然后在任意 .py 文件里：
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="lott",
    user="postgres",
    password="你设的密码"
)
print(conn)  # 打印成功则连接正常
conn.close()
```

---

## 六、界面各按钮说明

### Containers 页面
| 按钮 | 作用 |
|------|------|
| **Run / Start** | 启动容器 |
| **Stop** | 停止容器 |
| **Restart** | 重启容器 |
| **Delete** | 删除容器（数据卷没挂载则数据丢失）|
| **Logs** | 查看日志 |
| **Terminal** | 打开容器命令行 |

### 容器详情页（点击容器名进入）
| 标签页 | 作用 |
|--------|------|
| **Logs** | 实时日志流 |
| **Inspect** | 完整 JSON 配置 |
| **Terminal** | bash 命令行 |
| **Bind ports** | 查看端口映射 |
| **Volumes** | 查看数据卷挂载 |

### 创建容器时的配置项对照

| 界面名称 | 对应命令行参数 | 说明 |
|---------|--------------|------|
| Container name | `--name` | 容器标识名 |
| Host port / Host port : Container port | `-p 5432:5432` | 端口映射 |
| POSTGRES_PASSWORD | `-e POSTGRES_PASSWORD=` | 数据库密码 |
| POSTGRES_DB | `-e POSTGRES_DB=` | 数据库名 |
| POSTGRES_USER | `-e POSTGRES_USER=` | 用户名 |
| Volumes | `-v timescaledb_data:/var/lib/postgresql/data` | 数据持久化 |
| Restart policy | `--restart=unless-stopped` | 关机重启 |

---

## 七、常见问题

**Q: 容器起不来（红色状态）**
→ 点击容器 → Logs，看报错信息。常见原因：
- 端口 5432 已被占用（关掉本地其他 PostgreSQL）
- 密码没设（必须填 POSTGRES_PASSWORD）

**Q: Python 连接报错 `connection refused`**
→ 确认容器状态是绿色运行中
→ 确认 Docker Desktop 没在暂停状态

**Q: 怎么改密码**
→ 删除容器重建，或在容器 Terminal 里执行：
```sql
ALTER USER postgres WITH PASSWORD '新密码';
```

**Q: 怎么完全删除重装**
→ Containers 页面 → 点容器 → Delete（勾选 "Delete volumes" 清除数据）
→ Images 页面 → 点镜像 → Delete（清除镜像）
