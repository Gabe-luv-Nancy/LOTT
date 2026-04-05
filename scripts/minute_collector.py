#!/usr/bin/env python3
"""
期货分钟数据定时采集器 v2
- 安全隔离执行
- 完备异常处理
- 详细日志记录
- 不影响主进程
"""

import akshare as ak
import pandas as pd
import os
import json
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
import time
import signal

# ==================== 配置区 ====================

DATA_DIR = "/root/clabin_sync/LOTT/DL/minute_history"
LOG_DIR = "/root/.openclaw/logs/futures"
HISTORY_DIR = "/root/clabin_sync/LOTT/DL/minute_history"
STATE_FILE = "/root/.openclaw/logs/futures/collector_state.json"

# 超时配置
REQUEST_TIMEOUT = 30  # 单个请求超时秒数
MAX_RETRIES = 3       # 最大重试次数
RETRY_DELAY = 2       # 重试间隔秒数
RATE_LIMIT_DELAY = 0.5  # 请求间隔，避免被限流

# 交易日判断 (简单方案，实际应该用交易日历)
WEEKEND_DAYS = [5, 6]  # 周六日

# 主力合约列表
MAIN_CONTRACTS = {
    "INE": [
        ("sc2604", "原油"),
        ("lu2604", "低硫燃料油"),
        ("nr2604", "20号胶"),
        ("bc2604", "国际铜"),
        ("ec2604", "欧线"),
    ],
    "SHFE": [
        ("cu2604", "铜"), ("al2604", "铝"), ("zn2604", "锌"), ("pb2604", "铅"),
        ("ni2604", "镍"), ("sn2604", "锡"), ("au2604", "黄金"), ("ag2604", "白银"),
        ("rb2605", "螺纹钢"), ("hc2605", "热卷"), ("ss2604", "不锈钢"),
        ("ru2605", "橡胶"), ("fu2604", "燃油"), ("bu2604", "沥青"),
        ("sp2604", "纸浆"), ("wr2605", "线材"),
    ],
    "DCE": [
        ("i2605", "铁矿"), ("j2605", "焦炭"), ("jm2605", "焦煤"),
        ("m2605", "豆粕"), ("y2605", "豆油"), ("p2605", "棕榈油"),
        ("a2605", "豆一"), ("b2605", "豆二"), ("c2605", "玉米"), ("cs2605", "淀粉"),
        ("l2605", "塑料"), ("v2605", "PVC"), ("pp2605", "PP"),
        ("eb2604", "苯乙烯"), ("eg2604", "乙二醇"), ("pg2604", "LPG"),
        ("rr2604", "粳米"), ("lh2505", "生猪"),
    ],
    "GFEX": [
        ("si2504", "工业硅"),
        ("lc2504", "碳酸锂"),
    ],
    "CFFEX": [
        ("IF2503", "沪深300"), ("IC2503", "中证500"),
        ("IH2503", "上证50"), ("IM2503", "中证1000"),
        ("T2503", "10年国债"), ("TF2503", "5年国债"), ("TS2503", "2年国债"),
    ],
}

# ==================== 日志配置 ====================

def setup_logging() -> logging.Logger:
    """配置日志"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    log_file = os.path.join(LOG_DIR, f"collector_{datetime.now().strftime('%Y%m%d')}.log")
    
    logger = logging.getLogger("futures_collector")
    logger.setLevel(logging.INFO)
    
    # 文件处理器 - 详细日志
    fh = logging.FileHandler(log_file, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    
    # 控制台处理器 - 简洁输出
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        '%(asctime)s %(message)s', datefmt='%H:%M:%S'
    ))
    
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

logger = setup_logging()

# ==================== 状态管理 ====================

class CollectorState:
    """采集器状态管理"""
    
    def __init__(self, state_file: str):
        self.state_file = state_file
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'last_run': None,
            'last_success': None,
            'consecutive_failures': 0,
            'total_runs': 0,
            'total_rows_collected': 0,
            'errors': [],
        }
    
    def save(self):
        """保存状态"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def record_start(self):
        """记录开始"""
        self.state['last_run'] = datetime.now().isoformat()
        self.state['total_runs'] += 1
        self.save()
    
    def record_success(self, new_rows: int):
        """记录成功"""
        self.state['last_success'] = datetime.now().isoformat()
        self.state['consecutive_failures'] = 0
        self.state['total_rows_collected'] += new_rows
        self.save()
    
    def record_failure(self, error: str):
        """记录失败"""
        self.state['consecutive_failures'] += 1
        self.state['errors'].append({
            'time': datetime.now().isoformat(),
            'error': str(error)[:500],
        })
        # 只保留最近20条错误
        self.state['errors'] = self.state['errors'][-20:]
        self.save()

state = CollectorState(STATE_FILE)

# ==================== 核心功能 ====================

def is_trading_day() -> Tuple[bool, str]:
    """
    判断是否为交易日
    返回: (是否交易日, 原因说明)
    """
    now = datetime.now()
    
    # 周末判断
    if now.weekday() in WEEKEND_DAYS:
        return False, f"周末非交易日 (周{now.weekday()+1})"
    
    # 法定节假日需要额外判断，这里简化处理
    # 实际应该用交易日历
    
    return True, "交易日"


def download_with_retry(symbol: str, period: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    带重试的数据下载
    返回: (DataFrame或None, 错误信息)
    """
    last_error = ""
    
    for attempt in range(MAX_RETRIES):
        try:
            df = ak.futures_zh_minute_sina(symbol=symbol, period=period)
            
            if df is not None and len(df) > 0:
                return df, ""
            
            # 空数据
            if df is None or len(df) == 0:
                return None, "数据为空"
                
        except Exception as e:
            last_error = str(e)[:200]
            
            if attempt < MAX_RETRIES - 1:
                logger.debug(f"  {symbol} 重试 {attempt+2}/{MAX_RETRIES}: {last_error}")
                time.sleep(RETRY_DELAY)
    
    return None, last_error


def merge_to_history(df: pd.DataFrame, symbol: str, period: str, exchange: str) -> Tuple[int, str]:
    """
    增量合并到历史文件
    返回: (新增行数, 错误信息)
    """
    try:
        exchange_dir = os.path.join(HISTORY_DIR, exchange)
        os.makedirs(exchange_dir, exist_ok=True)
        history_file = os.path.join(exchange_dir, f"{symbol}_{period}m_history.csv")
        
        if os.path.exists(history_file):
            old_df = pd.read_csv(history_file)
            
            # 合并去重
            combined = pd.concat([old_df, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=['datetime'], keep='last')
            combined = combined.sort_values('datetime').reset_index(drop=True)
            
            new_rows = len(combined) - len(old_df)
            
            if new_rows > 0:
                combined.to_csv(history_file, index=False)
            elif new_rows == 0:
                # 无新数据，但更新文件时间
                pass
            
            return new_rows, ""
        else:
            # 首次创建
            df.to_csv(history_file, index=False)
            return len(df), ""
            
    except Exception as e:
        return 0, str(e)[:200]


def collect_minute_data(period: str = "1", exchanges: List[str] = None) -> Dict:
    """
    采集分钟数据
    返回: 采集结果统计
    """
    start_time = time.time()
    state.record_start()
    
    # 检查交易日
    is_trading, reason = is_trading_day()
    logger.info(f"="*60)
    logger.info(f"采集开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"交易日检查: {reason}")
    logger.info(f"="*60)
    
    if not is_trading:
        logger.info("非交易日，跳过采集")
        return {
            'status': 'skipped',
            'reason': reason,
            'duration': time.time() - start_time,
        }
    
    results = {
        'status': 'success',
        'period': period,
        'total_symbols': 0,
        'success_count': 0,
        'fail_count': 0,
        'skip_count': 0,
        'new_rows': 0,
        'errors': [],
        'duration': 0,
    }
    
    for exchange, contracts in MAIN_CONTRACTS.items():
        if exchanges and exchange not in exchanges:
            continue
        
        logger.info(f"\n[{exchange}]")
        exchange_success = 0
        exchange_fail = 0
        exchange_new = 0
        
        for symbol, name in contracts:
            results['total_symbols'] += 1
            
            # 下载
            df, error = download_with_retry(symbol, period)
            
            if df is not None:
                # 合并
                new_rows, merge_error = merge_to_history(df, symbol, period, exchange)
                
                if merge_error:
                    results['errors'].append(f"{symbol}: 合并失败 - {merge_error}")
                    results['fail_count'] += 1
                    exchange_fail += 1
                    logger.warning(f"  ✗ {symbol}: 合并失败")
                else:
                    results['success_count'] += 1
                    results['new_rows'] += new_rows
                    exchange_success += 1
                    exchange_new += new_rows
                    
                    if new_rows > 0:
                        logger.info(f"  ✓ {symbol}: +{new_rows}条")
                    else:
                        results['skip_count'] += 1
            else:
                results['fail_count'] += 1
                results['errors'].append(f"{symbol}: {error}")
                exchange_fail += 1
                logger.warning(f"  ✗ {symbol}: {error}")
            
            # 限流
            time.sleep(RATE_LIMIT_DELAY)
        
        logger.info(f"  [{exchange}] 成功:{exchange_success} 失败:{exchange_fail} 新增:{exchange_new}条")
    
    # 完成
    duration = time.time() - start_time
    results['duration'] = round(duration, 2)
    
    logger.info(f"\n" + "="*60)
    logger.info(f"采集完成: 成功{results['success_count']} 失败{results['fail_count']} 新增{results['new_rows']}条")
    logger.info(f"耗时: {duration:.1f}秒")
    
    # 记录状态
    if results['fail_count'] == 0:
        state.record_success(results['new_rows'])
    else:
        state.record_failure(f"{results['fail_count']} symbols failed")
    
    return results


def get_stats() -> Dict:
    """获取统计信息"""
    stats = {
        'collector_state': state.state,
        'data_stats': {
            'total_files': 0,
            'total_rows': 0,
            'exchanges': {},
            'latest_update': None,
        }
    }
    
    if not os.path.exists(HISTORY_DIR):
        return stats
    
    for exchange in os.listdir(HISTORY_DIR):
        exchange_dir = os.path.join(HISTORY_DIR, exchange)
        if not os.path.isdir(exchange_dir):
            continue
            
        exchange_stats = {'files': 0, 'rows': 0, 'latest': None}
        
        for f in os.listdir(exchange_dir):
            if not f.endswith('_history.csv'):
                continue
                
            filepath = os.path.join(exchange_dir, f)
            try:
                df = pd.read_csv(filepath)
                exchange_stats['files'] += 1
                exchange_stats['rows'] += len(df)
                
                if len(df) > 0:
                    latest = df['datetime'].iloc[-1]
                    if exchange_stats['latest'] is None or latest > exchange_stats['latest']:
                        exchange_stats['latest'] = latest
            except:
                pass
        
        stats['data_stats']['exchanges'][exchange] = exchange_stats
        stats['data_stats']['total_files'] += exchange_stats['files']
        stats['data_stats']['total_rows'] += exchange_stats['rows']
        
        if exchange_stats['latest']:
            if stats['data_stats']['latest_update'] is None or exchange_stats['latest'] > stats['data_stats']['latest_update']:
                stats['data_stats']['latest_update'] = exchange_stats['latest']
    
    return stats


# ==================== 主入口 ====================

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='期货分钟数据采集器')
    parser.add_argument('command', choices=['collect', 'stats', 'test', 'check'],
                       help='命令: collect=采集, stats=统计, test=测试, check=检查')
    parser.add_argument('--period', '-p', default='1', help='周期: 1/5/15/30/60')
    parser.add_argument('--exchange', '-e', help='指定交易所')
    parser.add_argument('--symbol', '-s', help='测试指定合约')
    
    args = parser.parse_args()
    
    if args.command == 'collect':
        exchanges = [args.exchange] if args.exchange else None
        result = collect_minute_data(args.period, exchanges)
        
        # 输出JSON结果供调用方解析
        print("\n---RESULT---")
        print(json.dumps(result, ensure_ascii=False))
        
        # 返回码: 0=成功, 1=部分失败, 2=全部失败
        if result['status'] == 'skipped':
            sys.exit(0)
        elif result['fail_count'] == 0:
            sys.exit(0)
        elif result['success_count'] == 0:
            sys.exit(2)
        else:
            sys.exit(1)
    
    elif args.command == 'stats':
        stats = get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    elif args.command == 'test':
        symbol = args.symbol or 'sc2604'
        period = args.period
        logger.info(f"测试下载: {symbol} {period}分钟")
        
        df, error = download_with_retry(symbol, period)
        if df is not None:
            logger.info(f"成功: {len(df)}条")
            logger.info(f"时间范围: {df['datetime'].iloc[0]} ~ {df['datetime'].iloc[-1]}")
            print(df.head(10))
        else:
            logger.error(f"失败: {error}")
    
    elif args.command == 'check':
        # 健康检查
        is_trading, reason = is_trading_day()
        stats = get_stats()
        
        print(f"交易日: {is_trading} ({reason})")
        print(f"总数据: {stats['data_stats']['total_rows']} 条")
        print(f"最近采集: {stats['collector_state'].get('last_run', 'N/A')}")
        print(f"连续失败: {stats['collector_state'].get('consecutive_failures', 0)} 次")


if __name__ == "__main__":
    main()
