# -*- coding: utf-8 -*-
"""
Cross_Layer.global_imports — LOTT 通用模块导入

将所有常用模块统一放在这里，notebook 只需两行：
    from Cross_Layer.global_imports import *

然后直接使用：
    pd   → pandas
    np   → numpy
    os   → os
    pd.DataFrame(...)   # 等同于 pandas.DataFrame(...)
"""

# TimescaleDB
import psycopg2
import subprocess
import importlib


import logging
from typing import Dict, List, Optional, Any


import os 
import sys
import logging
from pathlib import Path

# 数据处理
import numpy as np
import pandas as pd

# 时间
from datetime import datetime, timedelta, date, timezone

# 文件/序列化
import json
import pickle
import csv

# HTTP
try:
    import requests
except ImportError:
    requests = None

# 类型
from typing import (
    Any, Optional, Union, List, Dict, Tuple,
    Callable, TypeVar, Generic, Type,
)

# 常用工具（lazy）
try:
    from functools import cached_property
except ImportError:  # Python < 3.8
    cached_property = property

# 日志快捷函数
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

# 常用别名（避免每次写完整名字）
DataFrame = pd.DataFrame
Series    = pd.Series