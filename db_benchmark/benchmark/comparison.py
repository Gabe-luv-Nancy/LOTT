"""
结果比较 & 可视化
"""

import json
from pathlib import Path
from typing import List

import pandas as pd

from .runner import BenchmarkRunner
from ..adapters.base import BenchmarkReport


def compare_results(reports: List[BenchmarkReport], output_dir: Path = None) -> pd.DataFrame:
    """汇总对比所有数据库结果"""
    dfs = []
    for report in reports:
        dfs.append(report.to_dataframe())

    if not dfs:
        return pd.DataFrame()

    combined = pd.concat(dfs, ignore_index=True)

    # 透视表：行=场景，列=数据库
    pivot = combined.pivot_table(
        index="scenario",
        columns="db",
        values="duration_ms",
        aggfunc="first",
    )

    # 计算加速比（以最慢的为基准）
    for col in pivot.columns:
        baseline = pivot[col].max()
        if baseline > 0:
            pivot[f"{col}_speedup"] = baseline / pivot[col]

    return combined, pivot


def print_comparison(reports: List[BenchmarkReport]):
    """打印对比表格"""
    if not reports:
        print("No reports to compare")
        return

    combined, pivot = compare_results(reports)

    print(f"\n{'='*90}")
    print(f"  数据库基准测试对比")
    print(f"{'='*90}")

    dbs = [r.db_name for r in reports]
    header = f"{'场景':<22}" + "".join(f"{db:>14}" for db in dbs)
    print(header)
    print("-" * 90)

    for scenario in pivot.index:
        row = f"{scenario:<22}"
        for db in dbs:
            if db in pivot.columns:
                val = pivot.loc[scenario, db]
                if pd.notna(val) and val > 0:
                    row += f"{val:>13.1f}ms"
                else:
                    row += f"{'N/A':>14}"
            else:
                row += f"{'N/A':>14}"
        print(row)

    print("-" * 90)

    # 打印写入吞吐
    print(f"\n{'写入吞吐量 (行/秒):':<22}")
    for db in dbs:
        db_df = combined[combined["db"] == db]
        bulk = db_df[db_df["scenario"] == "bulk_insert"]
        if not bulk.empty:
            rps = bulk["rows_per_sec"].values[0]
            print(f"  {db:<20}: {rps:>15,.0f} 行/秒")

    # 打印结论
    print(f"\n{'结论摘要:'}")
    for scenario in ["bulk_insert", "range_query", "aggregation"]:
        row = pivot.xs(scenario)
        if row.notna().any():
            best = row.idxmin()
            best_val = row.min()
            print(f"  {scenario:<22}: {best} 最快 ({best_val:.1f}ms)")


def save_results(reports: List[BenchmarkReport], output_dir: Path):
    """保存结果到文件"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    data = [r.summary() for r in reports]
    with open(output_dir / "benchmark_results.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # CSV
    combined, _ = compare_results(reports)
    combined.to_csv(output_dir / "benchmark_results.csv", index=False)

    print(f"\n结果已保存: {output_dir}")
