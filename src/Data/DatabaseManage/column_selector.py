"""
列选择器模块 - MultiIndex DataFrame 列选择工具

从 Cross_Layer/enhanceddataframe.py 迁移，提供多级列索引的高级切片功能。

使用示例:
    # 元组模式索引
    df_sel[('589990.SH', '科创综指ETF华泰柏瑞', '万份基金单位')]

    # 字典模式索引
    df_sel[{0: '56108.*', 2: '收盘价.*'}]

    # 通配符搜索
    df_sel['*收益率*']

    # 按层级筛选
    select_columns(df, code='^56108', metric='价|成交量')
"""

import re
from typing import Union, List, Dict, Any, Optional
from functools import lru_cache

import numpy as np
import pandas as pd


def select_columns(
    df: pd.DataFrame,
    code: Optional[str] = None,
    name: Optional[str] = None,
    metric: Optional[str] = None,
    **filters
) -> pd.DataFrame:
    """
    根据多级列索引条件选择列
    
    参数:
        df: 具有 MultiIndex 列的 DataFrame
        code: 第一级（代码）匹配模式
        name: 第二级（名称）匹配模式
        metric: 第三级（指标）匹配模式
        **filters: 其他层级匹配条件，格式为 level_name=pattern
    
    返回:
        匹配的列组成的 DataFrame
    """
    # 验证结构
    if not validate_multiindex_structure(df):
        raise ValueError("DataFrame 不符合多级列索引结构")
    
    # 构建过滤条件字典
    filter_dict = {}
    
    # 处理标准参数
    if code is not None:
        filter_dict[0] = code
    if name is not None:
        filter_dict[1] = name
    if metric is not None:
        filter_dict[2] = metric
    
    # 处理额外过滤器
    for level_name, pattern in filters.items():
        level_idx = _get_level_index(df, level_name)
        filter_dict[level_idx] = pattern
    
    return _apply_column_filters(df, filter_dict)


def select_by_tuple(df: pd.DataFrame, conditions: tuple) -> pd.DataFrame:
    """
    使用元组模式选择列
    
    参数:
        df: DataFrame
        conditions: 条件元组，如 ('56108.*', None, '收盘价.*')
                   不足3个元素会用 None 填充
    
    示例:
        select_by_tuple(df, ('589990.SH', '科创综指ETF华泰柏瑞', '万份基金单位'))
    """
    # 确保conditions是三元组，不足用None填充
    conditions = list(conditions) + [None] * (3 - len(conditions))
    level0_cond, level1_cond, level2_cond = conditions[:3]
    
    return _apply_column_filters(df, {
        0: level0_cond,
        1: level1_cond,
        2: level2_cond
    })


def select_by_dict(df: pd.DataFrame, pattern_dict: Dict[int, str]) -> pd.DataFrame:
    """
    使用字典模式选择列
    
    参数:
        df: DataFrame
        pattern_dict: 层级索引到匹配模式的映射
                     如 {0: '56108.*', 2: '收盘价.*'}
    
    示例:
        select_by_dict(df, {0: '56108.*', 2: '收盘价.*'})
    """
    return _apply_column_filters(df, pattern_dict)


def select_by_wildcard(df: pd.DataFrame, pattern: str) -> pd.DataFrame:
    """
    使用通配符搜索列
    
    参数:
        df: DataFrame
        pattern: 通配符模式，如 '*收益率*'
    
    示例:
        select_by_wildcard(df, '*收益率*')
    """
    # 将通配符转换为正则表达式
    if pattern.startswith('^') or pattern.endswith('$'):
        regex_pattern = pattern
    else:
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
    
    # 使用NumPy数组避免索引对齐问题
    mask = np.array([False] * len(df.columns))
    
    # 在所有层级中搜索匹配
    for level in range(df.columns.nlevels):
        level_values = df.columns.get_level_values(level).astype(str)
        level_mask = level_values.str.contains(regex_pattern, regex=True, na=False)
        mask |= level_mask.to_numpy()
    
    return df.iloc[:, mask]


def search_columns(df: pd.DataFrame, pattern: str, level: Optional[Union[int, str]] = None) -> pd.DataFrame:
    """
    搜索包含特定模式的列
    
    参数:
        df: DataFrame
        pattern: 搜索模式（正则表达式）
        level: 可选，指定搜索的层级
    
    返回:
        匹配的列组成的 DataFrame
    """
    if level is not None:
        level_idx = _get_level_index(df, level)
        mask = df.columns.get_level_values(level_idx).astype(str).str.contains(pattern, na=False)
    else:
        mask = np.zeros(len(df.columns), dtype=bool)
        for i in range(df.columns.nlevels):
            level_mask = df.columns.get_level_values(i).astype(str).str.contains(pattern, na=False)
            mask |= level_mask.to_numpy()
    
    result_columns = df.columns[mask]
    print(f"找到 {len(result_columns)} 列匹配 '{pattern}'")
    if len(result_columns) > 0:
        print("前10个匹配:", result_columns[:10].tolist())
    
    return df.iloc[:, mask]


def validate_multiindex_structure(df: pd.DataFrame, expected_levels: List[str] = None) -> bool:
    """
    验证 DataFrame 是否符合多级列索引结构
    
    参数:
        df: DataFrame
        expected_levels: 期望的层级名称列表，默认为 ['code', 'name', 'metric']
    """
    if expected_levels is None:
        expected_levels = ['code', 'name', 'metric']
    
    if df.columns.nlevels != len(expected_levels):
        return False
    
    actual_names = list(df.columns.names)
    
    # 如果列名是None，尝试设置
    if all(name is None for name in actual_names):
        print(f"警告: 列级别名称为 None，建议设置为 {expected_levels}")
        return True
    
    return True


def get_column_info(df: pd.DataFrame, level: Optional[Union[int, str]] = None) -> Union[pd.Series, Dict]:
    """
    获取列信息
    
    参数:
        df: DataFrame
        level: 可选，指定层级
    """
    if level is not None:
        level_idx = _get_level_index(df, level)
        values = df.columns.get_level_values(level_idx)
        print(f"Level {level} 值 (前20个):")
        print(values[:20])
        print(f"唯一值总数: {values.nunique()}")
        return pd.Series(values)
    else:
        print("列层级数:", df.columns.nlevels)
        print("层级名称:", df.columns.names)
        for i in range(df.columns.nlevels):
            unique_count = df.columns.get_level_values(i).nunique()
            print(f"Level {i}: {unique_count} 个唯一值")
        
        return {
            'levels': list(range(df.columns.nlevels)),
            'names': list(df.columns.names),
            'unique_counts': [df.columns.get_level_values(i).nunique() for i in range(df.columns.nlevels)]
        }


def get_unique_values(df: pd.DataFrame, level: Union[int, str]) -> List[str]:
    """
    获取指定层级的所有唯一值
    
    参数:
        df: DataFrame
        level: 层级索引或名称
    """
    level_idx = _get_level_index(df, level)
    return list(df.columns.get_level_values(level_idx).unique())


# ============ 内部辅助函数 ============

@lru_cache(maxsize=100)
def _compile_regex(pattern: str):
    """缓存正则表达式编译结果"""
    return re.compile(pattern)


def _get_level_index(df: pd.DataFrame, level: Union[int, str]) -> int:
    """将层级名称转换为索引"""
    if isinstance(level, int):
        return level
    elif isinstance(level, str):
        if level in df.columns.names:
            return df.columns.names.index(level)
        else:
            raise ValueError(f"层级 '{level}' 不存在。可用层级: {df.columns.names}")
    else:
        raise TypeError("level 必须是整数或字符串")


def _apply_column_filters(df: pd.DataFrame, filters_dict: Dict[int, str]) -> pd.DataFrame:
    """应用列过滤器"""
    if not filters_dict:
        return df.copy()
    
    # 使用NumPy数组进行布尔运算
    mask = np.ones(len(df.columns), dtype=bool)
    
    for level, pattern in filters_dict.items():
        if pattern is not None and str(pattern).strip():
            pattern_str = str(pattern)
            
            # 处理正则表达式
            if pattern_str.startswith('^') or pattern_str.endswith('$'):
                regex_pattern = pattern_str
            else:
                regex_pattern = pattern_str.replace('*', '.*').replace('?', '.')
            
            try:
                compiled_regex = _compile_regex(regex_pattern)
                level_values = df.columns.get_level_values(int(level)).astype(str)
                
                # 使用列表推导式进行匹配
                level_mask = [
                    bool(compiled_regex.search(str(x))) if pd.notna(x) else False 
                    for x in level_values
                ]
                mask &= np.array(level_mask, dtype=bool)
                
            except re.error:
                # 正则表达式编译失败，使用字符串包含匹配
                level_values = df.columns.get_level_values(int(level)).astype(str)
                level_mask = level_values.str.contains(pattern_str, na=False, regex=False)
                mask &= level_mask.to_numpy()
    
    return df.iloc[:, mask]


# ============ 便捷函数别名 ============

# ETF 数据专用快捷函数
def by_code(df: pd.DataFrame, code_pattern: str, exact_match: bool = False) -> pd.DataFrame:
    """根据代码选择列"""
    if exact_match:
        return df.xs(code_pattern, level=0, axis=1, drop_level=False)
    return select_columns(df, code=code_pattern)


def by_name(df: pd.DataFrame, name_pattern: str, exact_match: bool = False) -> pd.DataFrame:
    """根据名称选择列"""
    if exact_match:
        return df.xs(name_pattern, level=1, axis=1, drop_level=False)
    return select_columns(df, name=name_pattern)


def by_metric(df: pd.DataFrame, metric_pattern: str, exact_match: bool = False) -> pd.DataFrame:
    """根据指标选择列"""
    if exact_match:
        return df.xs(metric_pattern, level=2, axis=1, drop_level=False)
    return select_columns(df, metric=metric_pattern)


def get_all_codes(df: pd.DataFrame) -> List[str]:
    """获取所有代码"""
    return get_unique_values(df, 0)


def get_all_names(df: pd.DataFrame) -> List[str]:
    """获取所有名称"""
    return get_unique_values(df, 1)


def get_all_metrics(df: pd.DataFrame) -> List[str]:
    """获取所有指标"""
    return get_unique_values(df, 2)