"""
基准测试运行器
"""

import time
import statistics
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import numpy as np

from ..adapters.base import BaseAdapter, BenchmarkResult, BenchmarkReport
from ..config import BENCHMARK_SCENARIOS, BENCHMARK_CONFIG, RESULTS_DIR


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, adapter: BaseAdapter, name: str = None):
        self.adapter = adapter
        self.name = name or adapter.DB_NAME
        self.report = BenchmarkReport(db_name=self.name)
        self.cfg = BENCHMARK_CONFIG

    def run_all(self, test_data: pd.DataFrame, scenarios: List[str] = None) -> BenchmarkReport:
        """运行所有基准测试场景"""
        scenarios = scenarios or BENCHMARK_SCENARIOS
        total_start = time.perf_counter()

        print(f"\n{'='*60}")
        print(f"  {self.name} 基准测试")
        print(f"{'='*60}")

        # Setup
        t0 = time.perf_counter()
        self.adapter.connect()
        self.adapter.truncate()
        self.report.setup_duration_ms = (time.perf_counter() - t0) * 1000
        print(f"[Setup] 表结构创建: {self.report.setup_duration_ms:.1f}ms")

        # 测试数据准备
        test_data = self.adapter.normalize_df(test_data.copy())
        if "symbol" not in test_data.columns:
            test_data["symbol"] = "SC"
        if "exchange" not in test_data.columns:
            test_data["exchange"] = "INE"

        total_rows = len(test_data)
        print(f"[Data]  {total_rows:,} 行")

        # ====== 场景1: 批量写入 ======
        if "bulk_insert" in scenarios:
            r = self._bench_bulk_insert(test_data)
            self.report.results.append(r)
            self._print_result(r)

        # ====== 场景2: 范围查询 ======
        if "range_query" in scenarios:
            r = self._bench_range_query(test_data)
            self.report.results.append(r)
            self._print_result(r)

        # ====== 场景3: 最新数据查询 ======
        if "latest_by_symbol" in scenarios:
            r = self._bench_latest(test_data)
            self.report.results.append(r)
            self._print_result(r)

        # ====== 场景4: 时间聚合 ======
        if "aggregation" in scenarios:
            r = self._bench_aggregation(test_data)
            self.report.results.append(r)
            self._print_result(r)

        # ====== 场景5: 增量写入 ======
        if "incremental_insert" in scenarios:
            r = self._bench_incremental(test_data)
            self.report.results.append(r)
            self._print_result(r)

        # ====== 场景6: 混合读写 ======
        if "mixed_workload" in scenarios:
            r = self._bench_mixed(test_data)
            self.report.results.append(r)
            self._print_result(r)

        self.report.total_duration_ms = (time.perf_counter() - total_start) * 1000
        print(f"\n[Total] {self.report.total_duration_ms:.0f}ms ({self.report.total_duration_ms/1000:.1f}s)")

        self.adapter.disconnect()
        return self.report

    # ====== 各场景实现 ======

    def _bench_bulk_insert(self, df: pd.DataFrame) -> BenchmarkResult:
        """批量写入"""
        def run():
            self.adapter.truncate()
            self.adapter.bulk_insert(df)

        r = self.adapter.benchmark(
            scenario="bulk_insert",
            fn=run,
            rows_affected=len(df),
            repeat=self.cfg["repeat_times"],
            warmup=self.cfg["warmup_runs"],
        )
        return r

    def _bench_range_query(self, df: pd.DataFrame) -> BenchmarkResult:
        """范围查询：取最近 N 天数据"""
        if df.empty:
            return BenchmarkResult(scenario="range_query", db_name=self.name, duration_ms=0)

        dates = pd.to_datetime(df["datetime"])
        start_dt = (dates.max() - pd.Timedelta(days=self.cfg["range_query_days"])).strftime("%Y-%m-%d")

        def run():
            self.adapter.query_range(start_dt=start_dt)

        n_rows = len(df[dates >= start_dt])
        r = self.adapter.benchmark(
            scenario="range_query",
            fn=run,
            rows_affected=n_rows,
            repeat=self.cfg["repeat_times"],
            warmup=self.cfg["warmup_runs"],
            query_days=self.cfg["range_query_days"],
        )
        return r

    def _bench_latest(self, df: pd.DataFrame) -> BenchmarkResult:
        """查询每个品种最新1条"""
        if df.empty:
            return BenchmarkResult(scenario="latest_by_symbol", db_name=self.name, duration_ms=0)

        symbols = df["symbol"].unique()
        n = len(symbols)

        def run():
            for sym in symbols:
                self.adapter.query_latest(sym, n=1)

        r = self.adapter.benchmark(
            scenario="latest_by_symbol",
            fn=run,
            rows_affected=n,
            repeat=self.cfg["repeat_times"],
            warmup=self.cfg["warmup_runs"],
            n_symbols=n,
        )
        return r

    def _bench_aggregation(self, df: pd.DataFrame) -> BenchmarkResult:
        """时间聚合查询"""
        if df.empty:
            return BenchmarkResult(scenario="aggregation", db_name=self.name, duration_ms=0)

        dates = pd.to_datetime(df["datetime"])
        end_dt = dates.max().strftime("%Y-%m-%d")
        start_dt = (dates.max() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")

        def run():
            self.adapter.query_aggregate(freq=self.cfg["aggregation_interval"],
                                        start_dt=start_dt, end_dt=end_dt)

        r = self.adapter.benchmark(
            scenario="aggregation",
            fn=run,
            rows_affected=0,
            repeat=self.cfg["repeat_times"],
            warmup=self.cfg["warmup_runs"],
            interval=self.cfg["aggregation_interval"],
        )
        return r

    def _bench_incremental(self, df: pd.DataFrame) -> BenchmarkResult:
        """增量写入（分小批）"""
        batch_size = self.cfg["incremental_insert_batch_size"]
        if len(df) < batch_size:
            batch_size = max(10, len(df) // 10)

        def run():
            self.adapter.truncate()
            self.adapter.incremental_insert(df.head(1000), batch_size=batch_size)

        r = self.adapter.benchmark(
            scenario="incremental_insert",
            fn=run,
            rows_affected=min(1000, len(df)),
            repeat=self.cfg["repeat_times"],
            warmup=self.cfg["warmup_runs"],
            batch_size=batch_size,
        )
        return r

    def _bench_mixed(self, df: pd.DataFrame) -> BenchmarkResult:
        """混合读写：10次查询 + 5次写入"""
        if df.empty:
            return BenchmarkResult(scenario="mixed_workload", db_name=self.name, duration_ms=0)

        dates = pd.to_datetime(df["datetime"])
        symbols = df["symbol"].unique()
        start_dt = (dates.max() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")

        def run():
            # 读多写少
            for _ in range(10):
                self.adapter.query_range(symbol=symbols[0], start_dt=start_dt, limit=100)
            # 写入新数据
            self.adapter.bulk_insert(df.head(100))

        r = self.adapter.benchmark(
            scenario="mixed_workload",
            fn=run,
            rows_affected=100,
            repeat=self.cfg["repeat_times"],
            warmup=self.cfg["warmup_runs"],
        )
        return r

    @staticmethod
    def _print_result(r: BenchmarkResult):
        rps = f"{r.rows_per_second:,.0f}" if r.rows_per_second else "-"
        print(f"  [{r.scenario:25s}] {r.duration_ms:8.2f}ms  {rps:>12} 行/秒  ({r.rows_affected:,}行)")
