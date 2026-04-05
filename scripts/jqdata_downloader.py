#!/usr/bin/env python3
"""
聚宽(JQData)期货和ETF数据下载器
支持分批下载模式
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import jqdatasdk
import argparse

# 配置
CONFIG = {
    'username': '13021081780',
    'password': '19981211Yxh$',
    'data_dir': '/root/clabin_sync/LOTT/DL/JQData',
    'daily_limit': 1_000_000,
    'request_delay': 0.1,
    # 默认下载最近30天数据，可根据权限调整
    'date_range': None,  # 动态计算，由 get_date_range() 返回
}

def get_date_range():
    """动态计算日期范围 - 使用JQData权限范围内的日期"""
    # JQData免费账号权限：2024-12-11 至 2025-12-18
    return ('2024-12-11', '2025-12-18')


def get_date_range_catchup():
    """Catchup模式：从AkShare数据目录找到有数据但JQData没有的日期"""
    from pathlib import Path
    import os

    akshare_daily = Path('/root/clabin_sync/LOTT/DL/daily')
    jqdata_dir = Path('/root/clabin_sync/LOTT/DL/JQData/futures')

    if not akshare_daily.exists():
        return None

    # 找到AkShare有数据的最近日期范围
    akshare_dates = set()
    for root, dirs, files in os.walk(akshare_daily):
        for f in files:
            if f.endswith('.csv') and len(f) >= 10:
                date_str = f[:8]  # YYYYMMDD
                if date_str.isdigit():
                    year = int(date_str[:4])
                    if 2024 <= year <= 2026:
                        akshare_dates.add(date_str)

    # 找到JQData已有数据的日期
    jqdata_dates = set()
    for root, dirs, files in os.walk(jqdata_dir):
        for f in files:
            if f.endswith('.csv') and len(f) >= 10:
                # 尝试从文件内容读取最新日期
                fpath = Path(root) / f
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as fh:
                        lines = fh.readlines()
                        if len(lines) > 1:
                            last_line = lines[-1].strip()
                            if ',' in last_line:
                                date_col = last_line.split(',')[0][:8]
                                if date_col.isdigit():
                                    jqdata_dates.add(date_col)
                except:
                    pass

    # 取差集：AkShare有但JQData没有的日期
    missing_dates = sorted(akshare_dates - jqdata_dates)

    if not missing_dates:
        return None

    # 取最近的90天（避免一次请求太多）
    recent_missing = missing_dates[-90:] if len(missing_dates) > 90 else missing_dates
    return (recent_missing[0], recent_missing[-1])

EXCHANGE_MAP = {
    'XINE': 'INE',
    'XSGE': 'SHFE',
    'XDCE': 'DCE',
    'XZCE': 'CZCE',
    'CCFX': 'CFFEX',
    'GFEX': 'GFEX',
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/root/clabin_sync/LOTT/DL/JQData/logs/jqdata_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JQDataDownloader:
    def __init__(self, mode='frequency', target=None, frequency='1m', catchup=False):
        self.data_dir = Path(CONFIG['data_dir'])
        self.mode = mode  # 'exchange', 'frequency'
        self.target = target  # 具体目标(交易所)
        self.frequency = frequency
        self.catchup = catchup
        self.stats = {'success': 0, 'failed': 0, 'skipped': 0}
        self.catchup_range = None
        if catchup:
            rng = get_date_range_catchup()
            if rng is None:
                logger.info('Catchup: 没有发现缺失日期，所有数据已就绪')
            else:
                logger.info(f'Catchup模式: 将只下载缺失日期范围 {rng[0]} ~ {rng[1]}')
                self.catchup_range = rng
        
    def login(self):
        jqdatasdk.auth(CONFIG['username'], CONFIG['password'])
        count = jqdatasdk.get_query_count()
        logger.info(f'登录成功! 剩余配额: {count["spare"]:,}')
        
    def get_contracts(self):
        futures = jqdatasdk.get_all_securities(types=['futures'])
        etfs = jqdatasdk.get_all_securities(types=['etf'])
        
        _date_range = get_date_range()
        start = datetime.strptime(_date_range[0], '%Y-%m-%d')
        end = datetime.strptime(_date_range[1], '%Y-%m-%d')
        
        valid_futures = []
        for code, row in futures.iterrows():
            s_date = pd.to_datetime(row['start_date'])
            e_date = pd.to_datetime(row['end_date'])
            if s_date <= end and e_date >= start:
                valid_futures.append({
                    'code': code,
                    'name': row['display_name'],
                    'exchange': EXCHANGE_MAP.get(code.split('.')[-1], 'OTHER'),
                    'type': 'futures'
                })
        
        valid_etfs = []
        for code, row in etfs.iterrows():
            s_date = pd.to_datetime(row['start_date'])
            e_date = pd.to_datetime(row['end_date'])
            if s_date <= end and e_date >= start:
                valid_etfs.append({
                    'code': code,
                    'name': row['display_name'],
                    'exchange': 'XSHG' if code.endswith('.XSHG') else 'XSHE',
                    'type': 'etf'
                })
        
        logger.info(f'有效期货: {len(valid_futures)}, 有效ETF: {len(valid_etfs)}')
        return valid_futures, valid_etfs
    
    def get_save_path(self, contract, freq):
        exchange = contract['exchange']
        code = contract['code'].replace('.', '_')
        
        if contract['type'] == 'futures':
            path = self.data_dir / 'futures' / exchange / freq / f'{code}.csv'
        else:
            path = self.data_dir / 'etf' / freq / f'{code}.csv'
        
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    
    def download_single(self, contract, freq):
        code = contract['code']
        save_path = self.get_save_path(contract, freq)
        
        # Catchup模式：检查是否需要下载（只看文件是否已存在，已有则跳过）
        if save_path.exists():
            self.stats['skipped'] += 1
            return 0
        
        try:
            _date_range = self.catchup_range if self.catchup_range else get_date_range()
            df = jqdatasdk.get_price(
                code,
                start_date=_date_range[0],
                end_date=_date_range[1],
                frequency=freq
            )
            
            if df is None or len(df) == 0:
                self.stats['skipped'] += 1
                return 0
            
            df.to_csv(save_path)
            return len(df)
            
        except Exception as e:
            logger.warning(f'下载失败 {code} {freq}: {e}')
            self.stats['failed'] += 1
            return 0
    
    def download_by_exchange(self, exchange, freq):
        """按交易所下载"""
        futures, etfs = self.get_contracts()
        
        if exchange == 'ETF':
            contracts = etfs
        else:
            contracts = [c for c in futures if c['exchange'] == exchange]
        
        logger.info(f'开始下载 {exchange} {freq}, 共{len(contracts)}个合约')
        
        for i, contract in enumerate(contracts):
            count = jqdatasdk.get_query_count()
            if count['spare'] < 500:
                logger.warning('配额不足，暂停')
                break
            
            rows = self.download_single(contract, freq)
            self.stats['success'] += rows
            time.sleep(CONFIG['request_delay'])
            
            if (i + 1) % 50 == 0:
                logger.info(f'进度: {i+1}/{len(contracts)}')
        
        return self.stats
    
    def download_by_frequency(self, freq):
        """按频率下载"""
        futures, etfs = self.get_contracts()
        all_contracts = futures + etfs
        
        logger.info(f'开始下载全部 {freq}, 共{len(all_contracts)}个合约')
        
        for i, contract in enumerate(all_contracts):
            count = jqdatasdk.get_query_count()
            if count['spare'] < 500:
                logger.warning('配额不足，暂停')
                break
            
            rows = self.download_single(contract, freq)
            self.stats['success'] += rows
            time.sleep(CONFIG['request_delay'])
            
            if (i + 1) % 100 == 0:
                logger.info(f'进度: {i+1}/{len(all_contracts)}')
        
        return self.stats
    
    def run(self):
        self.login()
        
        if self.mode == 'exchange':
            self.download_by_exchange(self.target, self.frequency)
        elif self.mode == 'frequency':
            self.download_by_frequency(self.frequency)
        else:
            logger.error(f'未知模式: {self.mode}')
            
        logger.info(f'完成! 成功: {self.stats["success"]}, 失败: {self.stats["failed"]}, 跳过: {self.stats["skipped"]}')


def main():
    parser = argparse.ArgumentParser(description='JQData下载器')
    parser.add_argument('--mode', choices=['exchange', 'frequency'], default='frequency',
                        help='下载模式: exchange按交易所, frequency按频率')
    parser.add_argument('--target', help='目标交易所(如INE, SHFE, DCE等)')
    parser.add_argument('--freq', '--frequency', dest='frequency', default='1m',
                        help='数据频率: 1m, 5m, 15m, 30m, 60m, daily')
    parser.add_argument('--catchup', action='store_true',
                        help='补跑模式: 只下载AkShare有但JQData缺失的日期')
    
    args = parser.parse_args()
    
    downloader = JQDataDownloader(
        mode=args.mode, 
        target=args.target, 
        frequency=args.frequency,
        catchup=args.catchup
    )
    downloader.run()


if __name__ == '__main__':
    main()
