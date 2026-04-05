#!/usr/bin/env python3
"""
LOTT 数据库基准测试 - 主程序

用法:
    python3 run_benchmark.py              # 使用现有CSV数据测试
    python3 run_benchmark.py --synthetic  # 生成并使用大规模合成数据
    python3 run_benchmark.py --sqlite      # 仅测试 SQLite
    python3 run_benchmark.py --all         # 测试所有可用的数据库
"""

import argparse
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_benchmark.adapters import get_adapter
from db_benchmark.benchmark import BenchmarkRunner, print_comparison, save_results
from db_benchmark.data import load_csv_data, generate_synthetic_data, load_synthetic_data
from db_benchmark.config import RESULTS_DIR


def main():
    parser = argparse.ArgumentParser(description="LOTT 数据库基准测试")
    parser.add_argument("--timescale", action="store_true", help="测试 TimescaleDB (亿级推荐)")
    parser.add_argument("--sqlite", action="store_true", help="仅测试 SQLite")
    parser.add_argument("--duckdb", action="store_true", help="仅测试 DuckDB")
    parser.add_argument("--postgres", action="store_true", help="测试 PostgreSQL")
    parser.add_argument("--mysql", action="store_true", help="测试 MySQL")
    parser.add_argument("--influxdb", action="store_true", help="测试 InfluxDB")
    parser.add_argument("--all", action="store_true", help="测试所有数据库")
    parser.add_argument("--synthetic", action="store_true", help="使用大规模合成数据 (50品种×365天)")
    parser.add_argument("--size", type=int, default=10, help="合成数据规模: 品种数")
    args = parser.parse_args()

    # ====== 加载测试数据 ======
    print("加载测试数据...")
    if args.synthetic:
        df = load_synthetic_data()
        if df.empty:
            print(f"未找到合成数据，正在生成...")
            df = generate_synthetic_data(n_symbols=args.size)
    else:
        df = load_csv_data()

    if df.empty:
        print("ERROR: 没有可用的测试数据")
        return

    print(f"数据量: {len(df):,} 行, {df['symbol'].nunique()} 个品种")

    # ====== 选择要测试的数据库 ======
    if args.all:
        targets = ["sqlite", "duckdb", "timescale", "postgres", "mysql", "influxdb"]
    elif args.timescale:
        targets = ["timescaledb"]
    elif args.sqlite:
        targets = ["sqlite"]
    elif args.duckdb:
        targets = ["duckdb"]
    else:
        # 默认: SQLite + TimescaleDB（亿级推荐）
        targets = ["sqlite", "timescaledb"]
        if args.postgres:
            targets.append("postgres")

    # ====== 运行基准测试 ======
    reports = []
    for db_name in targets:
        try:
            adapter = get_adapter(db_name)
            runner = BenchmarkRunner(adapter, name=db_name)
            report = runner.run_all(df)
            reports.append(report)
        except ImportError as e:
            print(f"[跳过] {db_name}: {e}")
        except Exception as e:
            print(f"[错误] {db_name}: {e}")

    # ====== 结果对比 ======
    if reports:
        print_comparison(reports)
        save_results(reports, RESULTS_DIR)
    else:
        print("没有成功完成任何基准测试")


if __name__ == "__main__":
    main()
