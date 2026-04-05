"""
数据工具模块 - 数据检测和处理工具

提供无效值检测、数据验证等功能，配合 ChartWidget + Marker 使用。

使用示例:
    # 检测无效值
    invalid_mask = detect_invalid_values(df, 'price')
    invalid_indices = get_invalid_indices(df, 'price')
    
    # 配合 ChartWidget 使用
    chart.add_line(data, name="price")
    chart.add_markers(invalid_indices, style='x', color='red')
"""

from typing import Union, List, Any, Optional
import numpy as np
import pandas as pd


# ============ 无效值常量定义 ============

INVALID_VALUES = [
    # Python 内置无效值
    0, None, float('nan'), float('inf'), float('-inf'),
    
    # 空字符串
    '', 
    
    # 常见无效标记
    '---', '--', 'NONE', 'None', 'null', 'NULL', 'NaN', 'nan',
    'N/A', 'n/a', '#N/A', '#VALUE!', '#REF!', '#DIV/0!',
    
    # 中文无效标记
    '未知', '不详', '缺失', '错误', '无数据', '无效',
    
    # 金融数据常见无效
    '停牌', '退市', '未上市',
]


# ============ 无效值检测函数 ============

def is_invalid(value: Any, invalid_list: Optional[List[Any]] = None) -> bool:
    """
    检查单个值是否为无效值
    
    参数:
        value: 要检查的值
        invalid_list: 自定义无效值列表，默认使用 INVALID_VALUES
    
    返回:
        bool: True 表示是无效值
    """
    if invalid_list is None:
        invalid_list = INVALID_VALUES
    
    # None 和 NaN 检查
    if value is None:
        return True
    if isinstance(value, float):
        if np.isnan(value) or np.isinf(value):
            return True
    
    # 数值 0 检查（可选，某些场景 0 是有效值）
    if value == 0 and 0 in invalid_list:
        return True
    
    # 字符串检查
    if isinstance(value, str):
        value_stripped = value.strip()
        if value_stripped in invalid_list:
            return True
        # 检查是否在列表中（不区分大小写）
        value_upper = value_stripped.upper()
        for invalid in invalid_list:
            if isinstance(invalid, str) and value_upper == invalid.upper():
                return True
    
    return False


def detect_invalid_values(
    series: Union[pd.Series, np.ndarray, list],
    invalid_list: Optional[List[Any]] = None
) -> np.ndarray:
    """
    检测序列中的无效值
    
    参数:
        series: 数据序列
        invalid_list: 自定义无效值列表
    
    返回:
        np.ndarray: 布尔掩码，True 表示无效值
    """
    if isinstance(series, pd.Series):
        values = series.values
    elif isinstance(series, np.ndarray):
        values = series
    else:
        values = np.array(series)
    
    mask = np.array([is_invalid(v, invalid_list) for v in values])
    return mask


def get_invalid_indices(
    df: Union[pd.DataFrame, pd.Series],
    column: Optional[str] = None,
    invalid_list: Optional[List[Any]] = None
) -> Union[pd.Index, List[int]]:
    """
    获取无效值的索引位置
    
    参数:
        df: DataFrame 或 Series
        column: 如果是 DataFrame，指定列名
        invalid_list: 自定义无效值列表
    
    返回:
        索引对象或索引列表
    """
    if isinstance(df, pd.DataFrame):
        if column is None:
            raise ValueError("DataFrame 需要指定 column 参数")
        series = df[column]
    else:
        series = df
    
    mask = detect_invalid_values(series, invalid_list)
    return series.index[mask].tolist()


def get_invalid_positions(
    df: Union[pd.DataFrame, pd.Series],
    column: Optional[str] = None,
    invalid_list: Optional[List[Any]] = None
) -> List[int]:
    """
    获取无效值的位置索引（整数位置，用于绘图）
    
    参数:
        df: DataFrame 或 Series
        column: 如果是 DataFrame，指定列名
        invalid_list: 自定义无效值列表
    
    返回:
        List[int]: 整数位置列表
    """
    if isinstance(df, pd.DataFrame):
        if column is None:
            raise ValueError("DataFrame 需要指定 column 参数")
        series = df[column]
    else:
        series = df
    
    mask = detect_invalid_values(series, invalid_list)
    return np.where(mask)[0].tolist()


def count_invalid_values(
    series: Union[pd.Series, np.ndarray, list],
    invalid_list: Optional[List[Any]] = None
) -> dict:
    """
    统计无效值信息
    
    参数:
        series: 数据序列
        invalid_list: 自定义无效值列表
    
    返回:
        dict: 包含 count, percentage, positions 等信息
    """
    mask = detect_invalid_values(series, invalid_list)
    count = np.sum(mask)
    total = len(mask)
    
    return {
        'count': int(count),
        'total': total,
        'percentage': count / total * 100 if total > 0 else 0,
        'positions': np.where(mask)[0].tolist(),
    }


def clean_invalid_values(
    series: pd.Series,
    invalid_list: Optional[List[Any]] = None,
    method: str = 'drop'
) -> pd.Series:
    """
    清理无效值
    
    参数:
        series: 数据序列
        invalid_list: 自定义无效值列表
        method: 清理方法
            - 'drop': 删除无效值
            - 'fill': 用 NaN 填充
            - 'ffill': 向前填充
            - 'bfill': 向后填充
            - 'interpolate': 线性插值
    
    返回:
        pd.Series: 清理后的序列
    """
    mask = detect_invalid_values(series, invalid_list)
    result = series.copy()
    
    if method == 'drop':
        result = result[~mask]
    elif method == 'fill':
        result[mask] = np.nan
    elif method == 'ffill':
        result[mask] = np.nan
        result = result.ffill()
    elif method == 'bfill':
        result[mask] = np.nan
        result = result.bfill()
    elif method == 'interpolate':
        result[mask] = np.nan
        result = result.interpolate()
    
    return result


# ============ 便捷别名 ============

# 保持与旧代码兼容
IF_INVALID = is_invalid


# ============ 工具函数 ============

def add_invalid_value(value: Any) -> None:
    """添加自定义无效值到全局列表"""
    if value not in INVALID_VALUES:
        INVALID_VALUES.append(value)


def remove_invalid_value(value: Any) -> None:
    """从全局列表移除无效值"""
    if value in INVALID_VALUES:
        INVALID_VALUES.remove(value)


def set_invalid_values(values: List[Any]) -> None:
    """设置自定义无效值列表（替换默认）"""
    global INVALID_VALUES
    INVALID_VALUES = values.copy()


def get_invalid_values() -> List[Any]:
    """获取当前无效值列表"""
    return INVALID_VALUES.copy()