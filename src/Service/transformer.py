"""
DataFrame 转换器模块

将上游数据库 SELECT 查询结果转换为下游可操作的 DataFrame。
支持多种输入格式，自动处理 MultiIndex 列名和日期索引。

用法：
    from Service.transformer import DataFrameTransformer, transform_query_result
    
    # 使用类
    transformer = DataFrameTransformer()
    df = transformer.transform(query_result)
    
    # 使用快捷函数
    df = transform_query_result(query_result, date_column='trade_date')
"""

import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *

from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime


class DataFrameTransformer:
    """
    DataFrame 转换器
    
    将数据库查询结果（List[Dict] 或 Tuple 形式）转换为标准化 DataFrame。
    自动处理日期索引、MultiIndex 列名、数据类型转换等。
    
    Attributes:
        default_date_column: 默认日期列名
        auto_parse_dates: 是否自动解析日期
        optimize_memory: 是否优化内存使用
    """
    
    def __init__(self, 
                 default_date_column: str = 'date',
                 auto_parse_dates: bool = True,
                 optimize_memory: bool = True):
        """
        初始化转换器
        
        Args:
            default_date_column: 默认的日期列名
            auto_parse_dates: 是否自动解析日期列
            optimize_memory: 是否优化内存使用
        """
        self.default_date_column = default_date_column
        self.auto_parse_dates = auto_parse_dates
        self.optimize_memory = optimize_memory
        
    def transform(self, 
                  query_result: Union[List[Dict], List[Tuple], pd.DataFrame],
                  column_mapping: Optional[Dict[str, str]] = None,
                  date_column: Optional[str] = None,
                  set_index: bool = True,
                  multiindex_levels: Optional[List[str]] = None) -> pd.DataFrame:
        """
        转换数据库查询结果为 DataFrame
        
        Args:
            query_result: 数据库查询结果，支持 List[Dict]、List[Tuple] 或 DataFrame
            column_mapping: 列名映射字典，如 {'old_name': 'new_name'}
            date_column: 日期列名，默认使用 default_date_column
            set_index: 是否将日期列设为索引
            multiindex_levels: 用于构建 MultiIndex 的列名列表
            
        Returns:
            pd.DataFrame: 转换后的标准化 DataFrame
            
        Raises:
            ValueError: 查询结果为空或格式错误
            TypeError: 输入类型不支持
        """
        # 验证输入
        if query_result is None or (hasattr(query_result, '__len__') and len(query_result) == 0):
            raise ValueError("查询结果为空")
        
        # 根据输入类型转换
        if isinstance(query_result, pd.DataFrame):
            df = query_result.copy()
        elif isinstance(query_result, list):
            if len(query_result) == 0:
                raise ValueError("查询结果列表为空")
            
            # 判断是 Dict 列表还是 Tuple 列表
            if isinstance(query_result[0], dict):
                df = pd.DataFrame(query_result)
            elif isinstance(query_result[0], (tuple, list)):
                # Tuple 列表需要列名
                df = pd.DataFrame(query_result)
            else:
                raise TypeError(f"不支持的列表元素类型: {type(query_result[0])}")
        else:
            raise TypeError(f"不支持的输入类型: {type(query_result)}")
        
        # 应用列名映射
        if column_mapping:
            df = df.rename(columns=column_mapping)
        
        # 解析日期
        date_col = date_column or self.default_date_column
        if self.auto_parse_dates and date_col in df.columns:
            df = self._parse_date_column(df, date_col)
        
        # 设置索引
        if set_index and date_col in df.columns:
            df = df.set_index(date_col)
        
        # 构建 MultiIndex
        if multiindex_levels:
            df = self._build_multiindex(df, multiindex_levels)
        
        # 优化内存
        if self.optimize_memory:
            df = self._optimize_memory(df)
        
        return df
    
    def transform_to_multiindex(self,
                                query_result: Union[List[Dict], pd.DataFrame],
                                level_columns: List[str],
                                value_column: str = 'value',
                                date_column: str = 'date') -> pd.DataFrame:
        """
        将长表格式查询结果转换为 MultiIndex 宽表
        
        适用于数据库中存储的长表格式（symbol, time, value），
        转换为宽表格式（time 索引，MultiIndex 列名）。
        
        Args:
            query_result: 数据库查询结果
            level_columns: 用于构建 MultiIndex 列名的列列表，如 ['symbol', 'field']
            value_column: 值列名
            date_column: 日期列名
            
        Returns:
            pd.DataFrame: MultiIndex DataFrame
            
        Example:
            # 输入: [{'date': '2024-01-01', 'symbol': 'IF2406', 'field': 'close', 'value': 3650}, ...]
            # 输出: DataFrame with columns = MultiIndex([('IF2406', 'close'), ...])
        """
        df = self.transform(query_result, set_index=False)
        
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
        
        # 检查必要列
        missing_cols = [col for col in level_columns + [value_column, date_column] 
                       if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必要列: {missing_cols}")
        
        # 构建透视表
        if len(level_columns) == 1:
            # 单级列名
            pivot_df = df.pivot(index=date_column, columns=level_columns[0], values=value_column)
        else:
            # 多级列名
            pivot_df = df.pivot(index=date_column, columns=level_columns, values=value_column)
        
        return pivot_df
    
    def normalize_columns(self,
                          df: pd.DataFrame,
                          schema: Optional[Dict[str, str]] = None,
                          remove_unnamed: bool = True,
                          strip_whitespace: bool = True,
                          lowercase: bool = False) -> pd.DataFrame:
        """
        标准化 DataFrame 列名
        
        Args:
            df: 输入 DataFrame
            schema: 列名映射字典
            remove_unnamed: 是否移除 'Unnamed' 列
            strip_whitespace: 是否去除空白
            lowercase: 是否转为小写
            
        Returns:
            pd.DataFrame: 列名标准化后的 DataFrame
        """
        df = df.copy()
        
        # 处理 MultiIndex 列名
        if isinstance(df.columns, pd.MultiIndex):
            new_columns = []
            for col_tuple in df.columns:
                new_tuple = tuple(
                    self._normalize_column_name(str(c), remove_unnamed, strip_whitespace, lowercase)
                    for c in col_tuple
                )
                # 移除空字符串层级
                new_tuple = tuple(c for c in new_tuple if c)
                if not new_tuple:
                    new_tuple = ('unknown',)
                new_columns.append(new_tuple)
            
            # 统一层级数
            max_levels = max(len(c) for c in new_columns)
            new_columns = [c + ('',) * (max_levels - len(c)) for c in new_columns]
            df.columns = pd.MultiIndex.from_tuples(new_columns)
        else:
            new_columns = [
                self._normalize_column_name(str(c), remove_unnamed, strip_whitespace, lowercase)
                for c in df.columns
            ]
            df.columns = new_columns
        
        # 应用 schema 映射
        if schema:
            df = df.rename(columns=schema)
        
        return df
    
    def _normalize_column_name(self, 
                               name: str,
                               remove_unnamed: bool,
                               strip_whitespace: bool,
                               lowercase: bool) -> str:
        """标准化单个列名"""
        if remove_unnamed and 'Unnamed' in name:
            name = name.replace('Unnamed:', '').replace('Unnamed', '').strip()
            if not name:
                name = 'col'
        
        if strip_whitespace:
            name = name.strip()
        
        if lowercase:
            name = name.lower()
        
        return name
    
    def _parse_date_column(self, df: pd.DataFrame, date_column: str) -> pd.DataFrame:
        """解析日期列"""
        if date_column not in df.columns:
            return df
        
        try:
            df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
            
            # 检查转换成功率
            success_rate = df[date_column].notna().mean()
            if success_rate < 0.8:
                warnings.warn(f"日期列 '{date_column}' 转换成功率较低: {success_rate:.1%}")
        except Exception as e:
            warnings.warn(f"日期列解析失败: {e}")
        
        return df
    
    def _build_multiindex(self, df: pd.DataFrame, levels: List[str]) -> pd.DataFrame:
        """从指定列构建 MultiIndex"""
        available_levels = [l for l in levels if l in df.columns]
        
        if not available_levels:
            return df
        
        if len(available_levels) == 1:
            df.columns = df[available_levels[0]]
        else:
            tuples = list(zip(*[df[l] for l in available_levels]))
            df.columns = pd.MultiIndex.from_tuples(tuples, names=available_levels)
        
        return df
    
    def _optimize_memory(self, df: pd.DataFrame) -> pd.DataFrame:
        """优化 DataFrame 内存使用"""
        try:
            original_memory = df.memory_usage(deep=True).sum()
            
            # 优化数值列
            for col in df.select_dtypes(include=['int64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='integer')
            
            for col in df.select_dtypes(include=['float64']).columns:
                df[col] = pd.to_numeric(df[col], downcast='float')
            
            # 优化对象列
            for col in df.select_dtypes(include=['object']).columns:
                if len(df) > 0:
                    num_unique = df[col].nunique()
                    num_total = len(df[col])
                    if num_total > 0 and (num_unique / num_total) < 0.5:
                        df[col] = df[col].astype('category')
            
            optimized_memory = df.memory_usage(deep=True).sum()
            reduction = (original_memory - optimized_memory) / original_memory if original_memory > 0 else 0
            
            if reduction > 0.01:
                print(f"内存优化: {original_memory/1024/1024:.2f}MB -> {optimized_memory/1024/1024:.2f}MB (减少{reduction:.1%})")
            
        except Exception as e:
            warnings.warn(f"内存优化失败: {e}")
        
        return df
    
    def merge_dataframes(self,
                         df_list: List[pd.DataFrame],
                         merge_method: str = 'outer',
                         on_index: bool = True) -> pd.DataFrame:
        """
        合并多个 DataFrame
        
        Args:
            df_list: DataFrame 列表
            merge_method: 合并方式 ('inner', 'outer', 'left', 'right')
            on_index: 是否按索引合并
            
        Returns:
            pd.DataFrame: 合并后的 DataFrame
        """
        if not df_list:
            return pd.DataFrame()
        
        if len(df_list) == 1:
            return df_list[0]
        
        if on_index:
            # 按索引合并
            if merge_method in ['inner', 'outer']:
                result = pd.concat(df_list, axis=1, join=merge_method)
            else:
                # left/right 合并
                result = df_list[0]
                for df in df_list[1:]:
                    result = pd.merge(
                        result, df,
                        left_index=True,
                        right_index=True,
                        how=merge_method
                    )
        else:
            # 纵向合并
            result = pd.concat(df_list, axis=0, join=merge_method)
        
        return result


# 快捷函数
def transform_query_result(query_result: Union[List[Dict], List[Tuple], pd.DataFrame],
                           column_mapping: Optional[Dict[str, str]] = None,
                           date_column: str = 'date',
                           set_index: bool = True) -> pd.DataFrame:
    """
    快捷函数：转换数据库查询结果为 DataFrame
    
    Args:
        query_result: 数据库查询结果
        column_mapping: 列名映射
        date_column: 日期列名
        set_index: 是否设置日期为索引
        
    Returns:
        pd.DataFrame: 转换后的 DataFrame
    """
    transformer = DataFrameTransformer(default_date_column=date_column)
    return transformer.transform(query_result, column_mapping, date_column, set_index)


def transform_to_multiindex(query_result: Union[List[Dict], pd.DataFrame],
                            level_columns: List[str],
                            value_column: str = 'value',
                            date_column: str = 'date') -> pd.DataFrame:
    """
    快捷函数：将长表转换为 MultiIndex 宽表
    
    Args:
        query_result: 数据库查询结果
        level_columns: MultiIndex 层级列名
        value_column: 值列名
        date_column: 日期列名
        
    Returns:
        pd.DataFrame: MultiIndex DataFrame
    """
    transformer = DataFrameTransformer(default_date_column=date_column)
    return transformer.transform_to_multiindex(query_result, level_columns, value_column, date_column)


def normalize_columns(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """
    快捷函数：标准化 DataFrame 列名
    
    Args:
        df: 输入 DataFrame
        **kwargs: 传递给 normalize_columns 方法的参数
        
    Returns:
        pd.DataFrame: 列名标准化后的 DataFrame
    """
    transformer = DataFrameTransformer()
    return transformer.normalize_columns(df, **kwargs)