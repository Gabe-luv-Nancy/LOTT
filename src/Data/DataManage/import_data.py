"""
数据导入脚本 - 完整的数据导入流程

提供从 JSON/Excel/CSV 文件导入数据到 TimescaleDB 的完整流程。

用法：
    # 命令行运行
    python import_data.py
    
    # 或作为模块使用
    from Data.DataManage.import_data import (
        load_file_data,
        import_ohlcv_to_timescale,
        TimescaleIO,
    )
"""

import logging
import os
import sys
from typing import Optional

import pandas as pd

# 路径设置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Data.DataManage.timeseries_io import TimescaleIO
from Data.DataManage.local_access import LocalData

logger = logging.getLogger(__name__)


def load_file_data(file_path: str, **kwargs) -> pd.DataFrame:
    """
    加载数据文件（JSON/Excel/CSV），自动识别格式
    
    Args:
        file_path: 文件路径
        **kwargs: 透传给具体 loader
    
    Returns:
        pd.DataFrame
    """
    loader = LocalData()
    ext = os.path.splitext(file_path)[-1].lower()
    
    if ext == '.json':
        return loader.load_json_data(file_path, **kwargs)
    elif ext in ('.xlsx', '.xls'):
        return loader.load_excel_data(file_path, **kwargs)
    elif ext == '.csv':
        return loader.load_csv_data(file_path, **kwargs)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def dataframe_to_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    将通用 DataFrame 转换为标准 OHLCV 格式
    
    尝试自动识别列映射：
    - 时间列 -> time
    - 合约列 -> symbol
    - OHLCV 列 -> open/high/low/close/volume
    
    Args:
        df: 原始 DataFrame
    
    Returns:
        pd.DataFrame: 标准 OHLCV 格式
    """
    result = df.copy()
    
    # 尝试识别时间列
    time_candidates = ['time', 'date', 'datetime', 'timestamp', 'bar_time', 't']
    for col in time_candidates:
        if col in result.columns:
            result['time'] = pd.to_datetime(result[col])
            break
    else:
        if 'time' not in result.columns:
            raise ValueError("无法识别时间列，请确保 DataFrame 包含 time/date/datetime 列")
    
    # 尝试识别合约列
    symbol_candidates = ['symbol', 'code', 'instrument', '合约', '代码']
    for col in symbol_candidates:
        if col in result.columns:
            result['symbol'] = result[col].astype(str)
            break
    else:
        result['symbol'] = 'UNKNOWN'
    
    # 尝试识别交易所
    exchange_candidates = ['exchange', 'market', '交易所']
    for col in exchange_candidates:
        if col in result.columns:
            result['exchange'] = result[col].astype(str)
            break
    else:
        result['exchange'] = 'UNKNOWN'
    
    # 尝试识别周期（默认 1min）
    timeframe_candidates = ['timeframe', 'period', 'freq', '周期']
    for col in timeframe_candidates:
        if col in result.columns:
            result['timeframe'] = result[col].astype(str)
            break
    else:
        result['timeframe'] = '1min'
    
    # 尝试识别 OHLCV
    ohlcv_map = {
        'open': ['open', 'o', '开盘价', 'open_price'],
        'high': ['high', 'h', '最高价', 'high_price'],
        'low': ['low', 'l', '最低价', 'low_price'],
        'close': ['close', 'c', '收盘价', 'close_price'],
        'volume': ['volume', 'v', '成交量', 'vol'],
    }
    
    for target, candidates in ohlcv_map.items():
        if target not in result.columns:
            for col in candidates:
                if col in result.columns:
                    result[target] = pd.to_numeric(result[col], errors='coerce')
                    break
    
    required = ['symbol', 'exchange', 'timeframe', 'time', 'open', 'high', 'low', 'close', 'volume']
    missing = [c for c in required if c not in result.columns]
    if missing:
        raise ValueError(f"DataFrame 缺少必要列（转换后）: {missing}")
    
    return result[required]


def import_ohlcv_to_timescale(
    df: pd.DataFrame,
    config=None,
    batch_size: int = 1000,
    create_table: bool = True,
) -> dict:
    """
    将 DataFrame 导入 TimescaleDB
    
    Args:
        df: OHLCV DataFrame 或原始 DataFrame（会自动转换）
        config: TimescaleDB 配置，默认从 DataFeed 读取
        batch_size: 每批写入行数
        create_table: 是否自动创建表
    
    Returns:
        dict: {'rows_imported': N, 'rows_skipped': M}
    """
    # 自动转换为 OHLCV 格式
    if 'open' not in df.columns or 'high' not in df.columns:
        logger.info("自动转换 DataFrame 为 OHLCV 格式...")
        df = dataframe_to_ohlcv(df)
    
    ts = TimescaleIO(config=config)
    
    try:
        if create_table:
            ts.create_ohlcv_table()
        
        result = ts.insert_ohlcv(df, batch_size=batch_size)
        stats = ts.get_table_stats()
        logger.info(f"导入后统计: {stats}")
        return result
    finally:
        ts.close()


def main():
    """主函数 - 完整导入流程"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # 默认数据目录
    default_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'DataSource'
    )
    
    # 列出可用文件
    json_dir = os.path.join(default_dir, '_json')
    xl_dir = os.path.join(default_dir, '_xl')
    
    for d in [json_dir, xl_dir]:
        if os.path.exists(d):
            files = [f for f in os.listdir(d) if f.endswith(('.json', '.xlsx', '.xls', '.csv'))]
            if files:
                logger.info(f"可用文件 [{d}]: {files[:5]}...")
    
    logger.info("请在代码中指定文件路径后运行 import_ohlcv_to_timescale()")
    logger.info("示例:")
    logger.info("    from Data.DataManage.import_data import load_file_data, import_ohlcv_to_timescale")
    logger.info("    df = load_file_data('X:\\\\LOTT\\\\src\\\\Data\\\\DataSource\\\\_json\\\\data.json')")
    logger.info("    import_ohlcv_to_timescale(df)")


if __name__ == '__main__':
    main()
