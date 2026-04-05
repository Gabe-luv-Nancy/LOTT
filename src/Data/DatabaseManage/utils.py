'''
utils.py - 通用工具模块（轻量化版本）

依赖链：
  utils.py
    ↓
  database_config.py
    ↓  
  database_tables.py
    ↓
  database_operation.py
    ↓
  database_connect.py
'''

# === 核心依赖（必须） ===
import warnings
warnings.filterwarnings('ignore')
import os
import re
import sys
import json
import datetime
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Type
from pathlib import Path
import logging
import sqlite3
import hashlib
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# === 数据处理（必须） ===
import numpy as np
import pandas as pd

# === SQLAlchemy（必须） ===
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Text, 
    Boolean, JSON, UniqueConstraint, Index, ForeignKey, DDL, event, MetaData
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import func, text
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# === 可选依赖（按需加载） ===
try:
    from scipy.stats import kurtosis, skew
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    def tqdm(iterable, **kwargs):
        return iterable


# ==================== 常量定义 ====================

INVALID_VALUES = ['--', '-', '空', 'na', 'null', 'NULL', 'NaN', 
                  'nan', 'N/A', 'None', 'none', '', ' ', '  ',
                  None, np.nan, np.inf, -np.inf]


# ==================== 工具函数 ====================

def IF_INVALID(value):
    """检查值是否为无效值
    
    Args:
        value: pandas Series 或标量值
        
    Returns:
        bool 或 Series: 标识是否为无效值
    """
    if isinstance(value, pd.Series):
        return value.isna() | value.isin(INVALID_VALUES)
    else:
        if value is None:
            return True
        if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
            return True
        return value in INVALID_VALUES


def _now():
    """获取当前时间字符串"""
    return str(datetime.now().replace(microsecond=0)).replace(":", "-")


def hashit(colname_tuple: Union[tuple, List[tuple]],
           print_details: bool = False,
           backquoted: bool = False) -> Union[str, List[str]]:
    '''
    SHA256 hash on colname_tuple
    
    Args:
        colname_tuple: 单个元组或元组列表
        print_details: 是否打印哈希过程的详细信息
        backquoted: 返回的哈希字符串是否用反引号包裹
        
    Returns:
        str 或 List[str]: 哈希值
    '''
    def _compute_single_hash(tuple_item: tuple) -> str:
        """计算单个元组的哈希值"""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(str(tuple_item).encode('utf-8'))
        hex_dig = sha256_hash.hexdigest()
        return hex_dig

    # 处理单个元组输入
    if isinstance(colname_tuple, tuple):
        hex_dig = _compute_single_hash(colname_tuple)
        if print_details:
            print(f"SHA256 Hash for {colname_tuple}: -> {hex_dig}")
        if backquoted:
            return f"`{hex_dig}`"
        else:
            return hex_dig

    # 处理元组列表输入
    elif isinstance(colname_tuple, list):
        result_list = []
        for item in colname_tuple:
            if not isinstance(item, tuple):
                raise TypeError(f"列表中的元素必须是元组，但收到 {type(item)}: {item}")
            hex_dig = _compute_single_hash(item)
            if print_details:
                print(f"SHA256 Hash for {item}: -> {hex_dig}")
            if backquoted:
                result_list.append(f"`{hex_dig}`")
            else:
                result_list.append(hex_dig)
        return result_list

    else:
        raise TypeError("输入必须是元组或元组列表")


def setup_logging(config=None, level="INFO"):
    """统一的日志设置
    
    Args:
        config: 配置对象（可选），需要有 log_level 和 log_format 属性
        level: 日志级别（当 config 为 None 时使用）
    """
    if config:
        log_level = getattr(config, 'log_level', level)
        log_format = getattr(config, 'log_format', '%(asctime)s - %(levelname)s - %(name)s - %(message)s')
    else:
        log_level = level
        log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format
    )
