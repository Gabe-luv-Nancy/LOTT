from typing import Union, Dict, Any
import numpy as np
import pandas as pd

def detail(data: Union[pd.Series, pd.DataFrame],
           include_numeric: bool = True,
           include_object: bool = False,
           percentiles: list = [0.25, 0.5, 0.75],
           show_report: bool = True) -> Dict[str, Any]:
    """
    综合数据详情分析函数：提供稳健的描述性统计信息

    参数:
        data: 输入数据，可以是Series或DataFrame
        include_numeric: 是否包含数值型统计（默认True）
        include_object: 是否包含对象型统计（默认False）
        percentiles: 要计算的分位数列表（默认[0.25, 0.5, 0.75]）
        show_report: 是否在控制台显示详细报告（默认True）

    返回:
        包含统计信息的字典，结构因输入类型而异
    """
    if not isinstance(data, (pd.Series, pd.DataFrame)):
        raise TypeError("输入必须是pandas Series或DataFrame")

    if data.empty:
        if show_report:
            print("警告: 输入数据为空")
        return {}

    stats_summary = {}

    if isinstance(data, pd.Series):
        stats_summary = _detail_series(data, include_numeric, include_object, percentiles, show_report)
    elif isinstance(data, pd.DataFrame):
        stats_summary = _detail_dataframe(data, include_numeric, include_object, percentiles, show_report)

    return stats_summary


def _detail_series(series: pd.Series,
                   include_numeric: bool = True,
                   include_object: bool = False,
                   percentiles: list = [0.25, 0.5, 0.75],
                   show_report: bool = True) -> Dict[str, Any]:
    stats = {}
    stats['dtype'] = str(series.dtype)
    stats['count'] = series.count()
    stats['missing_count'] = series.isnull().sum()
    stats['missing_pct'] = (stats['missing_count'] / len(series)) * 100 if len(series) > 0 else 0

    if include_numeric and pd.api.types.is_numeric_dtype(series):
        stats.update(_calculate_numeric_stats(series, percentiles))

    if include_object and series.dtype == 'object':
        stats.update(_calculate_object_stats(series))

    if show_report:
        _print_series_report(series, stats)

    return stats


def _detail_dataframe(df: pd.DataFrame,
                      include_numeric: bool = True,
                      include_object: bool = False,
                      percentiles: list = [0.25, 0.5, 0.75],
                      show_report: bool = True) -> Dict[str, Dict[str, Any]]:
    stats_summary = {}

    df_info = {
        'shape': df.shape,
        'total_cells': df.size,
        'total_missing': df.isnull().sum().sum(),
        'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
        'columns': list(df.columns),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()}
    }
    stats_summary['dataframe_info'] = df_info

    for column in df.columns:
        col_stats = _detail_series(df[column], include_numeric, include_object, percentiles, False)
        stats_summary[column] = col_stats

    if show_report:
        _print_dataframe_report(df, stats_summary)

    return stats_summary


def _calculate_numeric_stats(series: pd.Series, percentiles: list) -> Dict[str, Any]:
    stats = {}
    valid_data = series.dropna()
    if len(valid_data) == 0:
        return stats

    safe_stats_methods = {
        'mean': lambda x: x.mean() if callable(getattr(x, 'mean', None)) else None,
        'std':  lambda x: x.std()  if callable(getattr(x, 'std',  None)) else None,
        'min':  lambda x: x.min()  if callable(getattr(x, 'min',  None)) else None,
        'max':  lambda x: x.max()  if callable(getattr(x, 'max',  None)) else None,
        'median': lambda x: x.median() if callable(getattr(x, 'median', None)) else None,
        'sum':  lambda x: x.sum()  if callable(getattr(x, 'sum',  None)) else None,
    }

    for stat_name, calc in safe_stats_methods.items():
        try:
            result = calc(valid_data)
            if result is not None and not (isinstance(result, (int, float)) and np.isnan(result)):
                stats[stat_name] = result
        except (AttributeError, TypeError):
            continue

    for p in percentiles:
        try:
            if 0 <= p <= 1:
                stats[f'percentile_{int(p*100)}'] = valid_data.quantile(p)
        except (AttributeError, TypeError):
            continue

    try:
        if len(valid_data) > 1:
            stats['variance'] = valid_data.var()
            stats['skewness'] = getattr(valid_data, 'skew', lambda: None)()
            stats['kurtosis'] = getattr(valid_data, 'kurtosis', lambda: None)()
            stats['range'] = stats.get('max', 0) - stats.get('min', 0)
            if stats.get('mean') and stats['mean'] != 0:
                stats['cv'] = stats.get('std', 0) / stats['mean']
    except (AttributeError, TypeError, ZeroDivisionError):
        pass

    return stats


def _calculate_object_stats(series: pd.Series) -> Dict[str, Any]:
    stats = {}
    valid_data = series.dropna()
    if len(valid_data) == 0:
        return stats

    try:
        stats['unique_count'] = valid_data.nunique()
        mode = valid_data.mode()
        stats['most_frequent'] = mode.iloc[0] if not mode.empty else None
        vc = valid_data.value_counts()
        stats['freq_of_most_frequent'] = vc.iloc[0] if not vc.empty else 0
        if valid_data.dtype == 'object':
            str_lengths = valid_data.astype(str).str.len()
            stats['avg_length'] = str_lengths.mean()
            stats['min_length'] = str_lengths.min()
            stats['max_length'] = str_lengths.max()
    except (AttributeError, IndexError, TypeError):
        pass

    return stats


def _print_series_report(series: pd.Series, stats: Dict[str, Any]):
    print("=" * 60)
    print("📊 SERIES 详细分析报告")
    print("=" * 60)
    print(f"数据类型: {stats.get('dtype', 'Unknown')}")
    print(f"总数据点: {len(series)}")
    print(f"有效数据: {stats.get('count', 0)}")
    print(f"缺失数据: {stats.get('missing_count', 0)} ({stats.get('missing_pct', 0):.1f}%)")

    if pd.api.types.is_numeric_dtype(series):
        print("\n数值统计:")
        for label, key in [("平均值", "mean"), ("标准差", "std"),
                            ("最小值", "min"), ("最大值", "max"),
                            ("中位数", "median")]:
            v = stats.get(key)
            print(f"  {label}: {f'{v:.4f}' if v is not None else 'N/A'}")

    if series.dtype == 'object':
        print("\n对象统计:")
        print(f"  唯一值数量: {stats.get('unique_count', 'N/A')}")
        print(f"  最频繁值: {stats.get('most_frequent', 'N/A')}")
    print("=" * 60)


def _print_dataframe_report(df: pd.DataFrame, stats_summary: Dict[str, Dict[str, Any]]):
    print("=" * 60)
    print("📊 DATAFRAME 详细分析报告")
    print("=" * 60)
    print(f"数据形状: {df.shape[0]} 行 × {df.shape[1]} 列")
    print(f"总数据点: {df.size}")
    print(f"内存使用: {stats_summary['dataframe_info']['memory_usage_mb']:.2f} MB")

    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    object_cols  = [c for c in df.columns if df[c].dtype == 'object']
    other_cols   = [c for c in df.columns if c not in numeric_cols + object_cols]

    print(f"\n列类型分布:")
    print(f"  数值型: {len(numeric_cols)} 列")
    print(f"  对象型: {len(object_cols)} 列")
    print(f"  其他类型: {len(other_cols)} 列")

    total_missing = stats_summary['dataframe_info']['total_missing']
    print(f"总缺失值: {total_missing} ({(total_missing / df.size) * 100:.1f}%)")

    print("\n各列摘要:")
    for col in df.columns:
        cs = stats_summary[col]
        print(f"  {col}: {cs['dtype']}, 缺失: {cs['missing_count']} ({cs['missing_pct']:.1f}%)")
    print("=" * 60)
