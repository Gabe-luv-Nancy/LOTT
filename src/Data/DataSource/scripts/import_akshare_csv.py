"""
AkShare CSV 批量导入脚本
============================
将 raw/akshare_daily/ 目录下的所有 CSV 文件导入 TimescaleDB。

每张CSV格式: date,open,high,low,close,volume,hold,settle
目标表: ohlcv_data (symbol, exchange, timeframe='1d', time, open, high, low, close, volume, turnover=0, settle)

【使用方式】
    python -m Data.DataSource.scripts.import_akshare_csv --dir /path/to/raw/akshare_daily/ --exchange SHFE --dry-run
    python -m Data.DataSource.scripts.import_akshare_csv --dir /path/to/raw/akshare_daily/ --exchange SHFE

【交易所映射】
    CFFEX → 中金所 (IF/IC/IH/IM/T/TF/TS/TL)
    CZCE  → 郑商所
    DCE   → 大商所
    GFEX  → 广期所
    INE   → 上能所
    SHFE  → 上期所
"""

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ── 日志配置 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── 交易所映射表 ────────────────────────────────────────────────────────────
EXCHANGE_MAP = {
    "CFFEX": "CFFEX",
    "CZCE":  "CZCE",
    "DCE":   "DCE",
    "GFEX":  "GFEX",
    "INE":   "INE",
    "SHFE":  "SHFE",
}

# ── 数据库配置 ──────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "lott",
    "user":     "postgres",
    "password": "1211",
}

# ── 表名 ───────────────────────────────────────────────────────────────────
TABLE_OHLCV     = "ohlcv_data"
TABLE_METADATA  = "data_metadata"

# ── 导入批次大小 ───────────────────────────────────────────────────────────
BATCH_SIZE = 5000


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def file_hash(filepath: str) -> str:
    """计算文件 MD5 哈希（用于去重判断）"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_table_exists(conn):
    """检查并创建 ohlcv_data 表（如不存在）"""
    cur = conn.cursor()
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ohlcv_data'
        );
    """)
    exists = cur.fetchone()[0]

    if not exists:
        logger.info("表 ohlcv_data 不存在，创建中...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.ohlcv_data (
                id          BIGSERIAL,
                symbol      TEXT        NOT NULL,
                exchange    TEXT        NOT NULL,
                timeframe   TEXT        NOT NULL DEFAULT '1d',
                time        TIMESTAMPTZ NOT NULL,
                open        DOUBLE PRECISION,
                high        DOUBLE PRECISION,
                low         DOUBLE PRECISION,
                close       DOUBLE PRECISION,
                volume      DOUBLE PRECISION,
                turnover    DOUBLE PRECISION DEFAULT 0,
                settle      DOUBLE PRECISION,
                created_at  TIMESTAMPTZ DEFAULT NOW(),
                PRIMARY KEY (symbol, exchange, timeframe, time)
            );

            SELECT create_hypertable(
                'public.ohlcv_data',
                'time',
                if_not_exists => TRUE,
                migrate_data  => TRUE,
                chunk_time_interval => INTERVAL '1 month'
            );

            CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_time
                ON public.ohlcv_data (symbol, timeframe, time DESC);
        """)
        conn.commit()
        logger.info("表 ohlcv_data 创建完成")
    else:
        logger.info("表 ohlcv_data 已存在，跳过创建")

    cur.close()


def load_csv(filepath: str) -> pd.DataFrame | None:
    """加载单个CSV文件，返回 DataFrame 或 None（失败时）"""
    try:
        df = pd.read_csv(filepath, parse_dates=["date"])
    except Exception as e:
        logger.warning(f"  解析失败 {filepath}: {e}")
        return None

    # 列名标准化
    rename_map = {
        "date":    "time",
        "open":    "open",
        "high":    "high",
        "low":     "low",
        "close":   "close",
        "volume":  "volume",
        "hold":    "hold",   # 持仓量 → 暂存，不写单独列
        "settle":  "settle",
    }
    df = df.rename(columns=rename_map)

    # 从文件名推断 symbol
    symbol = Path(filepath).stem.upper()   # e.g. "IF2503"
    return df, symbol


def insert_batch(conn, records: list[dict]):
    """批量插入记录（upsert 方式）"""
    if not records:
        return 0

    cols = ["symbol", "exchange", "timeframe", "time", "open", "high", "low", "close", "volume", "turnover", "settle"]
    values = [
        (r["symbol"], r["exchange"], r["timeframe"],
         r["time"], r["open"], r["high"], r["low"],
         r["close"], r["volume"], r.get("turnover", 0), r.get("settle"))
        for r in records
    ]

    cur = conn.cursor()
    query = f"""
        INSERT INTO public.{TABLE_OHLCV}
            ({','.join(cols)})
        VALUES %s
        ON CONFLICT (symbol, exchange, timeframe, time)
        DO UPDATE SET
            open   = EXCLUDED.open,
            high   = EXCLUDED.high,
            low    = EXCLUDED.low,
            close  = EXCLUDED.close,
            volume = EXCLUDED.volume,
            settle = EXCLUDED.settle
    """
    execute_values(cur, query, values, page_size=1000)
    conn.commit()
    cur.close()
    return len(values)


def process_file(conn, filepath: str, exchange: str, dry_run: bool = False) -> dict:
    """处理单个文件，返回统计 dict"""
    symbol = Path(filepath).stem.upper()
    result = {
        "symbol":     symbol,
        "exchange":   exchange,
        "total_rows": 0,
        "inserted":   0,
        "skipped":    0,
        "errors":     0,
        "status":     "ok",
    }

    loaded = load_csv(filepath)
    if loaded is None:
        result["status"] = "parse_error"
        result["errors"] = 1
        return result

    df, inferred_symbol = loaded
    result["total_rows"] = len(df)

    # 批量处理
    records = []
    for _, row in df.iterrows():
        try:
            time_val = pd.to_datetime(row["time"])
        except Exception:
            result["errors"] += 1
            continue

        # 跳过无效日期
        if pd.isna(time_val) or time_val.year < 1990 or time_val.year > 2030:
            result["errors"] += 1
            continue

        records.append({
            "symbol":    inferred_symbol,
            "exchange":  exchange,
            "timeframe": "1d",
            "time":      time_val,
            "open":      float(row["open"]) if pd.notna(row.get("open")) else None,
            "high":      float(row["high"]) if pd.notna(row.get("high")) else None,
            "low":       float(row["low"])  if pd.notna(row.get("low"))  else None,
            "close":     float(row["close"]) if pd.notna(row.get("close")) else None,
            "volume":    float(row["volume"]) if pd.notna(row.get("volume")) else None,
            "turnover":  0.0,
            "settle":    float(row["settle"]) if pd.notna(row.get("settle")) else None,
        })

    if dry_run:
        logger.info(f"  [DRY-RUN] {symbol}: {len(records)} 条记录（跳过实际写入）")
        result["inserted"] = len(records)
        return result

    if records:
        inserted = insert_batch(conn, records)
        result["inserted"] = inserted

    return result


def run_import(root_dir: str, exchange: str, dry_run: bool = False):
    """主入口：扫描目录，导入所有 CSV"""
    root = Path(root_dir)
    exchange_code = EXCHANGE_MAP.get(exchange.upper())
    if not exchange_code:
        logger.error(f"未知交易所: {exchange}，支持的: {list(EXCHANGE_MAP.keys())}")
        return

    csv_files = sorted(root.glob(f"{exchange}/*.csv"))
    logger.info(f"发现 {len(csv_files)} 个 CSV 文件 (exchange={exchange_code})")

    if not csv_files:
        logger.warning("没有找到 CSV 文件，检查目录路径是否正确")
        return

    conn = get_connection()
    ensure_table_exists(conn)

    total_ok = 0
    total_err = 0
    total_rows = 0

    for i, filepath in enumerate(csv_files, 1):
        result = process_file(conn, str(filepath), exchange_code, dry_run=dry_run)

        status_icon = "✅" if result["status"] == "ok" else "❌"
        logger.info(
            f"  [{i}/{len(csv_files)}] {status_icon} {result['symbol']} "
            f"| 总行={result['total_rows']} 写入={result['inserted']} 错={result['errors']}"
        )
        total_rows += result["total_rows"]
        if result["status"] == "ok":
            total_ok += 1
        else:
            total_err += 1

    conn.close()

    logger.info("=" * 60)
    logger.info(f"导入完成: ✅成功={total_ok} ❌失败={total_err} 总行={total_rows}")
    if dry_run:
        logger.info("【DRY-RUN 模式】以上仅为模拟，未实际写入数据库")


def run_all_exchanges(root_dir: str, dry_run: bool = False):
    """扫描根目录，自动识别所有子目录（交易所）并导入"""
    root = Path(root_dir)
    all_exchanges = [d.name for d in root.iterdir() if d.is_dir() and d.name in EXCHANGE_MAP]
    logger.info(f"自动发现交易所: {all_exchanges}")

    for exchange in all_exchanges:
        logger.info(f"\n{'='*60}\n>>> 开始导入 {exchange}\n{'='*60}")
        run_import(root_dir, exchange, dry_run=dry_run)


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AkShare CSV 批量导入 TimescaleDB")
    parser.add_argument("--dir",      required=True,  help="raw/akshare_daily/ 根目录路径")
    parser.add_argument("--exchange", default=None,   help="指定单个交易所（如 SHFE），不指定则自动扫描全部")
    parser.add_argument("--dry-run",  action="store_true", help="仅模拟，不写入数据库")
    args = parser.parse_args()

    if args.exchange:
        run_import(args.dir, args.exchange, dry_run=args.dry_run)
    else:
        run_all_exchanges(args.dir, dry_run=args.dry_run)
