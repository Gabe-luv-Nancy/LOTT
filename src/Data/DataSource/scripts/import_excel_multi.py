"""
金融终端 Excel（多股输出格式）批量导入脚本
=============================================
将 _xl/futures/ 和 _xl/etfs/ 目录下的多股输出 Excel 文件
转换为长表格式并导入 TimescaleDB ohlcv_data 表。

【多股输出格式规范】（2026-03-25 分析确定）
──────────────────────────────────────────────
行0:  (NaN)  合约A  合约A  合约A  ...  合约B  合约B  合约B  ...
行1:  (NaN)  合约名  合约名  合约名  ...  合约名  合约名  合约名  ...
行2:  (NaN)  开盘价  收盘价  最高价  最低价  结算价  前结算价  成交均价
                振幅  涨跌(元)  涨跌(结算价)  涨跌幅  涨跌幅(结算价)  前收盘价
                成交额  成交量  持仓量  持仓量变化  价差  ...
行3+: 日期    OHLCV数据（同上19列/合约）...

每个合约占 19 列，列0固定为日期。
合约代码在行0，数据类型在行2。
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ── 日志 ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ── 常量 ──────────────────────────────────────────────────────────────
COLS_PER_CONTRACT = 20   # 每合约列数：列0（日期） + 19个数据字段
HEADER_ROWS      = 3     # 表头行数（行0~2）

# 标准 OHLCV + settle 字段（列索引相对偏移，列1起算）
METRIC_OFFSET = {
    "open":     0,   # 开盘价
    "high":     2,   # 最高价
    "low":      3,   # 最低价
    "close":    1,   # 收盘价
    "settle":   4,   # 结算价
    "volume":   15,  # 成交量
    "turnover": 13,  # 成交额
    "hold":     16,  # 持仓量
}

# 交易所映射（文件名 → exchange代码）
EXCHANGE_MAP = {
    "上期所":   "SHFE",
    "大商所":   "DCE",
    "郑商所":   "CZCE",
    "中金所":   "CFFEX",
    "上能所":   "INE",
    "上金所":   "SHFE",   # 黄金现货，归入SHFE
    "广期所":   "GFEX",
}

DB_CONFIG = {
    "host":     "localhost",
    "port":     5432,
    "dbname":   "lott",
    "user":     "postgres",
    "password": "1211",
}

BATCH_SIZE = 5000


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def detect_contract_columns(filepath: str) -> list[dict]:
    """
    分析 Excel 文件表头，返回合约列表。
    每个合约: {start_col, code, name, metrics: [str,...]}
    """
    # 只读前3行（表头）
    df_header = pd.read_excel(filepath, header=None, nrows=HEADER_ROWS, usecols=range(0, 200))
    row_code = df_header.iloc[0]  # 行0: 合约代码
    row_name = df_header.iloc[1]  # 行1: 合约名称
    row_type = df_header.iloc[2]  # 行2: 数据类型

    contracts = []
    col = 1  # 列0是日期，跳过
    while col < len(row_code):
        code = str(row_code.iloc[col]) if not pd.isna(row_code.iloc[col]) else ""
        if code in ("nan", "None", ""):
            break
        # 收集该合约的19个指标
        metrics = [str(row_type.iloc[col + j]) if col + j < len(row_type) and not pd.isna(row_type.iloc[col + j]) else f"col_{j}"
                   for j in range(19)]
        contracts.append({
            "start_col": int(col),
            "code":      code,
            "name":      str(row_name.iloc[col]) if not pd.isna(row_name.iloc[col]) else code,
            "metrics":   metrics,
        })
        col += COLS_PER_CONTRACT  # 每个合约占 COLS_PER_CONTRACT 列

    return contracts


def load_excel_long(filepath: str, exchange: str, contract: dict) -> pd.DataFrame:
    """
    读取单个合约数据，转换为长表 DataFrame。
    返回: DataFrame with columns [symbol, exchange, timeframe, time, open, high, low, close, volume, settle]
    """
    start = contract["start_col"]
    # 列0=日期, 列start~start+17=18个数据字段 (共1+18=19列，与列名数匹配)
    col_indices = [0] + list(range(start, start + 18))

    # Excel 不支持 chunksize，需要一次性读（选中的列数少，内存可控）
    df = pd.read_excel(filepath, header=None, usecols=col_indices)

    # 跳过表头行（行0~2）
    df = df.iloc[HEADER_ROWS:].copy()
    if len(df) == 0:
        return pd.DataFrame()

    df.columns = ["time", "open", "close", "high", "low", "settle",
                  "pre_settle", "avg_price", "amplitude", "change",
                  "change_settle", "pct_change", "pct_change_settle",
                  "pre_close", "turnover", "volume", "hold", "hold_change",
                  "spread"]

    # 日期解析
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    # 过滤无效行
    df = df.dropna(subset=["time"])
    df = df[(df["time"].dt.year >= 1990) & (df["time"].dt.year <= 2030)]

    # 数值列处理（-- → NaN）
    for col in ["open", "high", "low", "close", "settle", "volume", "turnover", "hold"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace("--", pd.NA), errors="coerce")

    # 统一大写 + 去除空格
    symbol_code = contract["code"].strip().upper()
    # 去除 .SHF / .DCE 等后缀（如 bc2601.INE → BC2601）
    symbol_code = symbol_code.split(".")[0]

    df["symbol"]    = symbol_code
    df["exchange"]  = exchange
    df["timeframe"] = "1d"

    return df[["symbol", "exchange", "timeframe", "time",
               "open", "high", "low", "close", "volume", "turnover", "settle"]]


def insert_batch(conn, records: list[dict]) -> int:
    if not records:
        return 0
    cols = ["symbol", "exchange", "timeframe", "time",
            "open", "high", "low", "close", "volume", "turnover", "settle"]
    values = [
        (r["symbol"], r["exchange"], r["timeframe"],
         r["time"], r.get("open"), r.get("high"), r.get("low"),
         r.get("close"), r.get("volume"), r.get("turnover", 0), r.get("settle"))
        for r in records
    ]
    cur = conn.cursor()
    execute_values(
        cur,
        f"""INSERT INTO public.ohlcv_data ({','.join(cols)}) VALUES %s
            ON CONFLICT (symbol, exchange, timeframe, time)
            DO UPDATE SET open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
                          close=EXCLUDED.close, volume=EXCLUDED.volume, settle=EXCLUDED.settle""",
        values, page_size=1000
    )
    conn.commit()
    cur.close()
    return len(values)


def process_file(filepath: str, exchange: str, dry_run: bool = False) -> dict:
    """处理单个Excel文件，返回统计"""
    logger.info(f"  分析格式: {os.path.basename(filepath)}")
    contracts = detect_contract_columns(filepath)
    logger.info(f"  发现 {len(contracts)} 个合约: {[c['code'] for c in contracts[:5]]}...")

    total_rows    = 0
    inserted_rows = 0
    errors        = 0

    conn = get_connection()
    for i, contract in enumerate(contracts, 1):
        try:
            df = load_excel_long(filepath, exchange, contract)
        except Exception as e:
            logger.warning(f"    [{i}/{len(contracts)}] ❌ {contract['code']}: {e}")
            errors += 1
            continue

        if len(df) == 0:
            logger.warning(f"    [{i}/{len(contracts)}] ⚠️  {contract['code']}: 无有效数据")
            continue

        total_rows += len(df)
        if not dry_run:
            # 分批插入
            batch = []
            for _, row in df.iterrows():
                batch.append(row.to_dict())
                if len(batch) >= BATCH_SIZE:
                    inserted_rows += insert_batch(conn, batch)
                    batch = []
            if batch:
                inserted_rows += insert_batch(conn, batch)

        logger.info(f"    [{i}/{len(contracts)}] ✅ {contract['code']}: {len(df)} 行" +
                    (" [DRY-RUN]" if dry_run else ""))

    conn.close()
    return {
        "contracts":   len(contracts),
        "total_rows":  total_rows,
        "inserted":    inserted_rows,
        "errors":      errors,
    }


def run_import(xl_dir: str, futures_dir: str, exchange: str, dry_run: bool = False):
    """导入某个交易所的Excel文件"""
    futures_dir = futures_dir or "/mnt/x/LOTT/src/Data/DataSource/_xl/futures"
    # 先尝试精确文件名
    path = os.path.join(futures_dir, f"{exchange}多股输出(时间-品种)(期货).xlsx")
    if not os.path.exists(path):
        # 尝试模糊匹配
        path = None
        for fname in os.listdir(futures_dir):
            if exchange in fname and fname.endswith(".xlsx"):
                path = os.path.join(futures_dir, fname)
                break
    if not path or not os.path.exists(path):
        logger.error(f"找不到 {exchange} 的Excel文件，请确认目录和文件名")
        return

    exchange_code = EXCHANGE_MAP.get(exchange, exchange)
    logger.info(f"\n>>> 导入 {exchange} ({exchange_code}): {os.path.basename(path)}")
    result = process_file(path, exchange_code, dry_run=dry_run)
    logger.info(f"  完成: {result['contracts']}合约 {result['total_rows']}行 | 写入={result['inserted']} 错={result['errors']}")


def run_all(xl_dir: str = None, futures_dir: str = None, etfs_dir: str = None, dry_run: bool = False):
    """批量导入所有交易所"""
    futures_dir = futures_dir or "/mnt/x/LOTT/src/Data/DataSource/_xl/futures"
    logger.info(f"扫描目录: {futures_dir}")
    logger.info(f"发现文件: {os.listdir(futures_dir)}")

    for exchange in EXCHANGE_MAP:
        fname = None
        for f in os.listdir(futures_dir):
            if exchange in f and f.endswith(".xlsx"):
                fname = f
                break
        if fname:
            path = os.path.join(futures_dir, fname)
            exchange_code = EXCHANGE_MAP[exchange]
            logger.info(f"\n{'='*60}\n>>> {exchange} ({exchange_code}): {fname}\n{'='*60}")
            result = process_file(path, exchange_code, dry_run=dry_run)
            logger.info(f"  ✅ 完成: {result['contracts']}合约 {result['total_rows']}行")
        else:
            logger.warning(f"未找到 {exchange} 的文件")


# ── CLI ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="金融终端 Excel 批量导入 TimescaleDB")
    parser.add_argument("--xl-dir",    default=None,   help="Excel文件目录")
    parser.add_argument("--exchange",  default=None,   help="指定交易所（如 上期所）")
    parser.add_argument("--dry-run",   action="store_true", help="模拟运行")
    args = parser.parse_args()

    if args.exchange:
        run_import(args.xl_dir, None, args.exchange, dry_run=args.dry_run)
    else:
        run_all(xl_dir=args.xl_dir, dry_run=args.dry_run)
