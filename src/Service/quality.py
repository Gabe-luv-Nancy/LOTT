"""
数据质量分析模块

提供 DataFrame 数据质量分析功能，包括缺失值统计、异常值检测、
数据范围分析等。生成数据质量报告供策略参考。

用法：
    from Service.quality import DataQualityAnalyzer, analyze_quality
    
    # 使用类
    analyzer = DataQualityAnalyzer(df)
    report = analyzer.generate_report()
    
    # 使用快捷函数
    report = analyze_quality(df)
"""

import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *

from typing import Any, Dict, List, Optional, Union
from datetime import datetime


class DataQualityAnalyzer:
    """
    数据质量分析器
    
    分析 DataFrame 的数据质量，生成质量报告。
    支持缺失值统计、异常值检测、数据范围分析等。
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        初始化分析器
        
        Args:
            df: 待分析的 DataFrame
        """
        if df is None or df.empty:
            raise ValueError("DataFrame 不能为空")
        
        self.df = df
        self._analysis_result: Optional[Dict] = None
    
    def analyze(self) -> Dict[str, Any]:
        """
        执行完整的数据质量分析
        
        Returns:
            包含分析结果的字典
        """
        self._analysis_result = {
            'basic_info': self._analyze_basic_info(),
            'missing_values': self._analyze_missing_values(),
            'data_range': self._analyze_data_range(),
            'duplicates': self._analyze_duplicates(),
            'outliers': self._analyze_outliers(),
            'data_types': self._analyze_data_types(),
        }
        
        # 计算总体质量分数
        self._analysis_result['quality_score'] = self._calculate_quality_score()
        
        return self._analysis_result
    
    def _analyze_basic_info(self) -> Dict[str, Any]:
        """分析基本信息"""
        df = self.df
        
        # 时间范围
        time_range = {}
        if isinstance(df.index, pd.DatetimeIndex):
            time_range = {
                'start': str(df.index.min()),
                'end': str(df.index.max()),
                'duration_days': (df.index.max() - df.index.min()).days,
            }
        elif hasattr(df.index, 'get_level_values'):
            # MultiIndex
            try:
                level0 = df.index.get_level_values(0)
                if pd.api.types.is_datetime64_any_dtype(level0):
                    time_range = {
                        'start': str(level0.min()),
                        'end': str(level0.max()),
                        'duration_days': (level0.max() - level0.min()).days,
                    }
            except:
                pass
        
        return {
            'rows': len(df),
            'columns': len(df.columns),
            'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
            'time_range': time_range,
        }
    
    def _analyze_missing_values(self) -> Dict[str, Any]:
        """分析缺失值"""
        df = self.df
        
        # 总体统计
        total_cells = df.size
        total_missing = df.isna().sum().sum()
        overall_missing_rate = total_missing / total_cells if total_cells > 0 else 0
        
        # 逐列统计
        column_stats = []
        for col in df.columns:
            missing_count = df[col].isna().sum()
            missing_rate = missing_count / len(df) if len(df) > 0 else 0
            
            column_stats.append({
                'column': str(col),
                'missing_count': int(missing_count),
                'missing_rate': float(missing_rate),
                'valid_count': int(len(df) - missing_count),
            })
        
        # 高缺失率列
        high_missing_cols = [s for s in column_stats if s['missing_rate'] > 0.5]
        
        return {
            'total_missing': int(total_missing),
            'overall_missing_rate': float(overall_missing_rate),
            'column_stats': column_stats,
            'high_missing_columns': high_missing_cols,
            'complete_rows': int(len(df.dropna())),
            'complete_row_rate': float(len(df.dropna()) / len(df)) if len(df) > 0 else 0,
        }
    
    def _analyze_data_range(self) -> Dict[str, Any]:
        """分析数据范围"""
        df = self.df
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        range_stats = []
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            
            stats = {
                'column': str(col),
                'min': float(series.min()),
                'max': float(series.max()),
                'mean': float(series.mean()),
                'std': float(series.std()) if len(series) > 1 else 0,
                'median': float(series.median()),
            }
            
            # 检查是否有负值（对于价格类数据可能是异常）
            stats['has_negative'] = bool(series.min() < 0)
            
            # 检查是否有零值
            stats['zero_count'] = int((series == 0).sum())
            stats['zero_rate'] = float((series == 0).sum() / len(series))
            
            range_stats.append(stats)
        
        return {
            'numeric_columns': len(numeric_cols),
            'range_stats': range_stats,
        }
    
    def _analyze_duplicates(self) -> Dict[str, Any]:
        """分析重复数据"""
        df = self.df
        
        # 重复行
        duplicate_rows = df.duplicated().sum()
        
        # 重复索引
        duplicate_index = 0
        if not df.index.is_unique:
            duplicate_index = df.index.duplicated().sum()
        
        return {
            'duplicate_rows': int(duplicate_rows),
            'duplicate_row_rate': float(duplicate_rows / len(df)) if len(df) > 0 else 0,
            'duplicate_index_count': int(duplicate_index),
            'index_is_unique': bool(df.index.is_unique),
        }
    
    def _analyze_outliers(self) -> Dict[str, Any]:
        """分析异常值（使用 IQR 方法）"""
        df = self.df
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outlier_stats = []
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 4:
                continue
            
            # IQR 方法
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = series[(series < lower_bound) | (series > upper_bound)]
            
            outlier_stats.append({
                'column': str(col),
                'outlier_count': int(len(outliers)),
                'outlier_rate': float(len(outliers) / len(series)) if len(series) > 0 else 0,
                'lower_bound': float(lower_bound),
                'upper_bound': float(upper_bound),
            })
        
        return {
            'method': 'IQR',
            'outlier_stats': outlier_stats,
            'columns_with_outliers': [s for s in outlier_stats if s['outlier_count'] > 0],
        }
    
    def _analyze_data_types(self) -> Dict[str, Any]:
        """分析数据类型"""
        df = self.df
        
        type_counts = df.dtypes.value_counts().to_dict()
        type_counts = {str(k): int(v) for k, v in type_counts.items()}
        
        # 检查可能的类型问题
        issues = []
        
        for col in df.columns:
            dtype = df[col].dtype
            
            # 检查 object 类型中是否有混合类型
            if dtype == 'object':
                sample = df[col].dropna().head(100)
                if len(sample) > 0:
                    types = set(type(x).__name__ for x in sample)
                    if len(types) > 1:
                        issues.append({
                            'column': str(col),
                            'issue': 'mixed_types',
                            'types': list(types),
                        })
        
        return {
            'type_counts': type_counts,
            'potential_issues': issues,
        }
    
    def _calculate_quality_score(self) -> float:
        """计算总体质量分数（0-100）"""
        if self._analysis_result is None:
            return 0.0
        
        score = 100.0
        
        # 缺失值扣分
        missing_rate = self._analysis_result['missing_values']['overall_missing_rate']
        score -= missing_rate * 30  # 最多扣 30 分
        
        # 重复数据扣分
        duplicate_rate = self._analysis_result['duplicates']['duplicate_row_rate']
        score -= duplicate_rate * 20  # 最多扣 20 分
        
        # 异常值扣分
        outlier_stats = self._analysis_result['outliers']['outlier_stats']
        if outlier_stats:
            avg_outlier_rate = np.mean([s['outlier_rate'] for s in outlier_stats])
            score -= avg_outlier_rate * 20  # 最多扣 20 分
        
        # 类型问题扣分
        issues = self._analysis_result['data_types']['potential_issues']
        score -= len(issues) * 5  # 每个问题扣 5 分
        
        return max(0.0, min(100.0, score))
    
    def generate_report(self, output_format: str = 'dict') -> Union[Dict, str]:
        """
        生成数据质量报告
        
        Args:
            output_format: 输出格式 ('dict', 'text')
            
        Returns:
            报告内容
        """
        if self._analysis_result is None:
            self.analyze()
        
        if output_format == 'text':
            return self._format_text_report()
        else:
            return self._analysis_result
    
    def _format_text_report(self) -> str:
        """格式化文本报告"""
        r = self._analysis_result
        
        lines = [
            "=" * 60,
            "数据质量分析报告",
            "=" * 60,
            "",
            "【基本信息】",
            f"  行数: {r['basic_info']['rows']}",
            f"  列数: {r['basic_info']['columns']}",
            f"  内存使用: {r['basic_info']['memory_usage_mb']:.2f} MB",
        ]
        
        if r['basic_info']['time_range']:
            tr = r['basic_info']['time_range']
            lines.extend([
                f"  时间范围: {tr['start']} ~ {tr['end']}",
                f"  时间跨度: {tr['duration_days']} 天",
            ])
        
        lines.extend([
            "",
            "【缺失值分析】",
            f"  总缺失率: {r['missing_values']['overall_missing_rate']:.2%}",
            f"  完整行数: {r['missing_values']['complete_rows']}",
            f"  完整行比例: {r['missing_values']['complete_row_rate']:.2%}",
        ])
        
        if r['missing_values']['high_missing_columns']:
            lines.append("  高缺失率列 (>50%):")
            for col in r['missing_values']['high_missing_columns']:
                lines.append(f"    - {col['column']}: {col['missing_rate']:.2%}")
        
        lines.extend([
            "",
            "【重复数据】",
            f"  重复行数: {r['duplicates']['duplicate_rows']}",
            f"  重复行比例: {r['duplicates']['duplicate_row_rate']:.2%}",
            f"  索引是否唯一: {'是' if r['duplicates']['index_is_unique'] else '否'}",
        ])
        
        lines.extend([
            "",
            "【异常值分析】",
            f"  使用方法: {r['outliers']['method']}",
        ])
        
        if r['outliers']['columns_with_outliers']:
            lines.append("  存在异常值的列:")
            for col in r['outliers']['columns_with_outliers']:
                lines.append(f"    - {col['column']}: {col['outlier_count']} 个异常值 ({col['outlier_rate']:.2%})")
        else:
            lines.append("  未检测到明显异常值")
        
        lines.extend([
            "",
            "【总体质量分数】",
            f"  {r['quality_score']:.1f} / 100",
            "",
            "=" * 60,
        ])
        
        return "\n".join(lines)
    
    def get_column_report(self, column_name: str) -> Dict[str, Any]:
        """
        获取单个列的详细报告
        
        Args:
            column_name: 列名
            
        Returns:
            该列的详细分析结果
        """
        if column_name not in self.df.columns:
            raise ValueError(f"列 '{column_name}' 不存在")
        
        series = self.df[column_name]
        
        report = {
            'column_name': str(column_name),
            'dtype': str(series.dtype),
            'count': int(len(series)),
            'valid_count': int(series.notna().sum()),
            'missing_count': int(series.isna().sum()),
            'missing_rate': float(series.isna().sum() / len(series)) if len(series) > 0 else 0,
        }
        
        # 数值类型统计
        if pd.api.types.is_numeric_dtype(series):
            valid_series = series.dropna()
            if len(valid_series) > 0:
                report.update({
                    'min': float(valid_series.min()),
                    'max': float(valid_series.max()),
                    'mean': float(valid_series.mean()),
                    'std': float(valid_series.std()) if len(valid_series) > 1 else 0,
                    'median': float(valid_series.median()),
                    'unique_count': int(valid_series.nunique()),
                })
        
        return report
    
    def suggest_cleaning_actions(self) -> List[Dict[str, Any]]:
        """
        建议数据清洗操作
        
        Returns:
            建议的清洗操作列表
        """
        if self._analysis_result is None:
            self.analyze()
        
        suggestions = []
        
        # 缺失值处理建议
        missing = self._analysis_result['missing_values']
        if missing['overall_missing_rate'] > 0.1:
            suggestions.append({
                'type': 'missing_values',
                'priority': 'high',
                'description': f"缺失率较高 ({missing['overall_missing_rate']:.1%})，建议进行缺失值填充或删除",
                'affected_columns': [c['column'] for c in missing['column_stats'] if c['missing_rate'] > 0.1],
            })
        
        # 重复数据建议
        duplicates = self._analysis_result['duplicates']
        if duplicates['duplicate_rows'] > 0:
            suggestions.append({
                'type': 'duplicates',
                'priority': 'medium',
                'description': f"存在 {duplicates['duplicate_rows']} 个重复行，建议去重",
            })
        
        # 异常值建议
        outliers = self._analysis_result['outliers']
        if outliers['columns_with_outliers']:
            suggestions.append({
                'type': 'outliers',
                'priority': 'medium',
                'description': f"存在 {len(outliers['columns_with_outliers'])} 列有异常值，建议检查",
                'affected_columns': [c['column'] for c in outliers['columns_with_outliers']],
            })
        
        # 类型问题建议
        type_issues = self._analysis_result['data_types']['potential_issues']
        if type_issues:
            suggestions.append({
                'type': 'data_types',
                'priority': 'low',
                'description': f"存在 {len(type_issues)} 列有类型混合问题，建议统一类型",
                'affected_columns': [c['column'] for c in type_issues],
            })
        
        return suggestions


# 快捷函数
def analyze_quality(df: pd.DataFrame, output_format: str = 'dict') -> Union[Dict, str]:
    """
    快捷函数：分析数据质量
    
    Args:
        df: 待分析的 DataFrame
        output_format: 输出格式 ('dict', 'text')
        
    Returns:
        分析结果
    """
    analyzer = DataQualityAnalyzer(df)
    return analyzer.generate_report(output_format)


def get_quality_score(df: pd.DataFrame) -> float:
    """
    快捷函数：获取数据质量分数
    
    Args:
        df: 待分析的 DataFrame
        
    Returns:
        质量分数 (0-100)
    """
    analyzer = DataQualityAnalyzer(df)
    analyzer.analyze()
    return analyzer._analysis_result['quality_score']


def get_missing_report(df: pd.DataFrame) -> Dict[str, Any]:
    """
    快捷函数：获取缺失值报告
    
    Args:
        df: 待分析的 DataFrame
        
    Returns:
        缺失值分析结果
    """
    analyzer = DataQualityAnalyzer(df)
    return analyzer._analyze_missing_values()


def suggest_cleaning(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    快捷函数：获取数据清洗建议
    
    Args:
        df: 待分析的 DataFrame
        
    Returns:
        清洗建议列表
    """
    analyzer = DataQualityAnalyzer(df)
    return analyzer.suggest_cleaning_actions()