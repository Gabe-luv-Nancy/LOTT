"""
全局配置
"""
import os
from pathlib import Path

# ====== 路径配置 ======
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"           # 小规模测试数据 (现有CSV)
RESULTS_DIR = PROJECT_ROOT / "results"     # 基准测试结果
os.makedirs(RESULTS_DIR, exist_ok=True)

# ====== 数据源配置 ======
# 现有CSV数据路径
MINUTE_HISTORY_DIR = Path("/root/.openclaw/DL/minute_history")

# 生成的测试数据路径
SYNTHETIC_DATA_DIR = RESULTS_DIR / "synthetic_data"
os.makedirs(SYNTHETIC_DATA_DIR, exist_ok=True)

# ====== 数据库连接配置 ======
DB_CONFIGS = {
    "sqlite": {
        "path": str(RESULTS_DIR / "sqlite_benchmark.db"),
        "timeout": 30,
        "check_same_thread": False,
    },
    "duckdb": {
        "path": str(RESULTS_DIR / "duckdb_benchmark.db"),
    },
    "postgresql": {
        "host": os.getenv("PG_HOST", "localhost"),
        "port": int(os.getenv("PG_PORT", "5432")),
        "database": os.getenv("PG_DB", "lott"),
        "user": os.getenv("PG_USER", "postgres"),
        "password": os.getenv("PG_PASSWORD", "postgres"),
        "pool_size": 10,
    },
    "mysql": {
        "host": os.getenv("MY_HOST", "localhost"),
        "port": int(os.getenv("MY_PORT", "3306")),
        "database": os.getenv("MY_DB", "lott"),
        "user": os.getenv("MY_USER", "root"),
        "password": os.getenv("MY_PASSWORD", ""),
        "charset": "utf8mb4",
    },
    "influxdb": {
        "url": os.getenv("INFLUX_URL", "http://localhost:8086"),
        "token": os.getenv("INFLUX_TOKEN", ""),
        "org": os.getenv("INFLUX_ORG", "lott"),
        "bucket": os.getenv("INFLUX_BUCKET", "futures"),
        "timeout": 30_000,
    },
}

# ====== 表名配置 ======
TABLE_NAME = "futures_ohlcv"

# ====== 测试数据规模配置 ======
# 用于生成大规模合成数据
SYNTHETIC_CONFIG = {
    "symbols": 50,          # 合约数量
    "days": 365,            # 数据天数
    "bars_per_day": 240,    # 每日K线数 (期货日盘+夜盘)
    "total_rows": 50 * 365 * 240,  # ~4,380,000 行
}

# ====== 基准测试参数 ======
BENCHMARK_CONFIG = {
    # 写入测试
    "bulk_insert_batch_size": 10_000,
    "incremental_insert_batch_size": 100,

    # 读取测试
    "range_query_days": 30,       # 范围查询天数
    "aggregation_interval": "1H",  # 聚合周期

    # 重复次数 (取中位数)
    "repeat_times": 5,
    "warmup_runs": 1,
}

# ====== 基准测试场景 ======
BENCHMARK_SCENARIOS = [
    "bulk_insert",           # 批量写入
    "incremental_insert",    # 增量写入
    "range_query",           # 范围查询
    "latest_by_symbol",       # 每个品种最新一条
    "aggregation",            # 时间聚合
    "mixed_workload",         # 混合读写
]
