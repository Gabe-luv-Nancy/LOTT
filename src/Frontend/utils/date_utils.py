"""
日期工具函数

日期处理相关工具
"""

from datetime import datetime, timedelta
from typing import Tuple, Optional
import pandas as pd


class DateUtils:
    """日期工具类"""
    
    @staticmethod
    def parse_date(date_str: str, format: str = "%Y-%m-%d") -> Optional[datetime]:
        """
        解析日期字符串
        
        Args:
            date_str: 日期字符串
            format: 日期格式
            
        Returns:
            datetime 对象，解析失败返回 None
        """
        try:
            return datetime.strptime(date_str, format)
        except ValueError:
            return None
    
    @staticmethod
    def format_date(date: datetime, format: str = "%Y-%m-%d") -> str:
        """
        格式化日期
        
        Args:
            date: datetime 对象
            format: 输出格式
            
        Returns:
            格式化后的日期字符串
        """
        return date.strftime(format)
    
    @staticmethod
    def get_date_range(
        start: datetime,
        end: datetime,
        freq: str = "D"
    ) -> pd.DatetimeIndex:
        """
        生成日期范围
        
        Args:
            start: 开始日期
            end: 结束日期
            freq: 频率（D=日, W=周, M=月）
            
        Returns:
            日期索引
        """
        return pd.date_range(start=start, end=end, freq=freq)
    
    @staticmethod
    def get_trading_days(start: datetime, end: datetime) -> pd.DatetimeIndex:
        """
        获取交易日（排除周末）
        
        Args:
            start: 开始日期
            end: 结束日期
            
        Returns:
            交易日索引
        """
        days = pd.date_range(start=start, end=end, freq="B")  # B = business day
        return days
    
    @staticmethod
    def is_trading_day(date: datetime) -> bool:
        """
        判断是否为交易日
        
        Args:
            date: 日期
            
        Returns:
            是否为交易日
        """
        return date.weekday() < 5  # 0-4 = 周一到周五
    
    @staticmethod
    def get_previous_trading_day(date: datetime) -> datetime:
        """
        获取前一个交易日
        
        Args:
            date: 当前日期
            
        Returns:
            前一个交易日
        """
        prev = date - timedelta(days=1)
        while not DateUtils.is_trading_day(prev):
            prev -= timedelta(days=1)
        return prev
    
    @staticmethod
    def get_next_trading_day(date: datetime) -> datetime:
        """
        获取下一个交易日
        
        Args:
            date: 当前日期
            
        Returns:
            下一个交易日
        """
        next_day = date + timedelta(days=1)
        while not DateUtils.is_trading_day(next_day):
            next_day += timedelta(days=1)
        return next_day
    
    @staticmethod
    def get_quarter(date: datetime) -> int:
        """
        获取季度
        
        Args:
            date: 日期
            
        Returns:
            季度（1-4）
        """
        return (date.month - 1) // 3 + 1
    
    @staticmethod
    def get_year(date: datetime) -> int:
        """获取年份"""
        return date.year
    
    @staticmethod
    def get_month(date: datetime) -> int:
        """获取月份"""
        return date.month
    
    @staticmethod
    def date_diff(start: datetime, end: datetime) -> int:
        """
        计算日期差
        
        Args:
            start: 开始日期
            end: 结束日期
            
        Returns:
            天数差
        """
        return (end - start).days


# 模块级便捷函数（兼容直接导入）
format_datetime = DateUtils.format_date
parse_datetime = DateUtils.parse_date
get_date_range = DateUtils.get_date_range
