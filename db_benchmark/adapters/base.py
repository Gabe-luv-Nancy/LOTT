"""
Base Adapter - 所有数据库适配器的基类
定义统一接口
"""

import time
import statistics
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager

import pandas as pd

# 全局适配器注册表
ADAPTERS = {}


def register_adapter(name: str):
    """装饰器：注册数据库适配器"""
    def deco(cls):
        ADAPTERS[name] = cls
        return cls
    return deco


@dataclass
class BenchmarkResult:
    """单次基准测试结果"""
    scenario: str
    db_name: str
    duration_ms: float
    rows_affected: int = 0
    rows_per_second: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.rows_affected > 0 and self.duration_ms > 0:
            self.rows_per_second = self.rows_affected / (self.duration_ms / 1000)


@dataclass
class BenchmarkReport:
    """完整基准测试报告"""
    db_name: str
    results: List[BenchmarkResult] = field(default_factory=list)
    total_duration_ms: float = 0.0
    setup_duration_ms: float = 0.0

    def summary(self) -> Dict[str, Any]:
        summary = {"db": self.db_name, "total_ms": self.total_duration_ms}
        for r in self.results:
            summary[r.scenario] = {
                "ms": round(r.duration_ms, 2),
                "rows": r.rows_affected,
                "rps": round(r.rows_per_second, 0),
            }
        return summary

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for r in self.results:
            rows.append({
                "db": r.db_name,
                "scenario": r.scenario,
                "duration_ms": round(r.duration_ms, 2),
                "rows_affected": r.rows_affected,
                "rows_per_sec": round(r.rows_per_second, 0),
                **r.metadata,
            })
        return pd.DataFrame(rows)


class BaseAdapter(ABC):
    """数据库适配器基类"""

    DB_NAME: str = "base"
    SUPPORTS_BULK_INSERT: bool = True
    SUPPORTS_UPSERT: bool = False

    def __init__(self, **kwargs):
        self.config = kwargs
        self._connected = False

    # ====== 连接管理 ======

    @abstractmethod
    def connect(self):
        """建立连接"""
        pass

    @abstractmethod
    def disconnect(self):
        """关闭连接"""
        pass

    @contextmanager
    def session(self):
        """上下文管理器：自动连接/断开"""
        try:
            if not self._connected:
                self.connect()
            yield self
        finally:
            pass  # 不在 session 内关闭，让实例复用

    # ====== Schema 管理 ======

    @abstractmethod
    def create_schema(self):
        """创建表结构和索引"""
        pass

    @abstractmethod
    def drop_schema(self):
        """删除表"""
        pass

    def truncate(self):
        """清空表数据（保留结构）"""
        self.drop_schema()
        self.create_schema()

    # ====== 数据写入 ======

    @abstractmethod
    def bulk_insert(self, df: pd.DataFrame) -> int:
        """
        批量插入 DataFrame
        返回插入行数
        """
        pass

    def incremental_insert(self, df: pd.DataFrame, batch_size: int = 100) -> int:
        """增量插入（分批）"""
        total = 0
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            total += self.bulk_insert(batch)
        return total

    # ====== 数据查询 ======

    @abstractmethod
    def query_range(
        self,
        symbol: Optional[str] = None,
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """范围查询"""
        pass

    @abstractmethod
    def query_latest(self, symbol: str, n: int = 1) -> pd.DataFrame:
        """查询某品种最新 n 条"""
        pass

    @abstractmethod
    def query_aggregate(
        self,
        symbol: Optional[str] = None,
        freq: str = "1H",
        start_dt: Optional[str] = None,
        end_dt: Optional[str] = None,
    ) -> pd.DataFrame:
        """时间聚合查询"""
        pass

    def count(self) -> int:
        """总行数"""
        df = self.query_range(limit=1)
        # 用 LIMIT 1 估算：实际用 SELECT COUNT(*)
        return self._count_fast()

    @abstractmethod
    def _count_fast(self) -> int:
        """快速计数（不走完整查询）"""
        pass

    # ====== 基准测试辅助 ======

    def benchmark(
        self,
        scenario: str,
        fn,
        rows_affected: int = 0,
        repeat: int = 5,
        warmup: int = 1,
        **metadata,
    ) -> BenchmarkResult:
        """运行基准测试并计时"""
        # Warmup
        for _ in range(warmup):
            fn()

        # 正式测试（取中位数）
        durations = []
        for _ in range(repeat):
            start = time.perf_counter()
            fn()
            durations.append((time.perf_counter() - start) * 1000)

        duration_ms = statistics.median(durations)
        return BenchmarkResult(
            scenario=scenario,
            db_name=self.DB_NAME,
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            metadata=metadata,
        )

    # ====== 工具方法 ======

    @staticmethod
    def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
        """规范化 DataFrame 列名和类型"""
        df = df.copy()
        # 统一列名
        rename = {
            "datetime": "datetime",
            "date": "datetime",
            "timestamp": "datetime",
        }
        for old, new in rename.items():
            if old in df.columns and old != new:
                df.rename(columns={old: new}, inplace=True)

        # 确保必需列存在
        required = ["datetime", "open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}. Got: {list(df.columns)}")

        # 类型转换
        df["datetime"] = pd.to_datetime(df["datetime"])
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
        if "hold" in df.columns:
            df["hold"] = pd.to_numeric(df["hold"], errors="coerce").fillna(0).astype(int)

        return df[["datetime", "open", "high", "low", "close", "volume", "hold"]].copy()
