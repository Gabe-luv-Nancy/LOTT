#!/usr/bin/env python3
"""
期货仓单日度提取脚本

使用 akshare.get_receipt() 统一接口提取注册仓单数据

接口可用性（2026-04-08 实测）：
  SHFE ✅  get_receipt (get_shfe_receipt_3)
  CZCE ✅  get_receipt (get_czce_receipt_3)  
  GFEX ✅  get_receipt (get_gfex_receipt)
  DCE  ❌  HTTP 412 WAF封锁（需 Tushare Pro 或换源）

数据最早可用：
  SHFE: 约2-4周窗口（交易所仅保留近期数据）
  CZCE: 2008年起（部分日期Excel损坏会空）
  GFEX: 2022-12-22起
  DCE:  无法获取

使用方式：
  python3 receipt_collector.py                  # 提取昨日
  python3 receipt_collector.py --date 20260407  # 指定日期
  python3 receipt_collector.py --start 20260301 --end 20260407  # 范围
"""
import sys
sys.path.insert(0, '/root/clabin_sync/LOTT/scripts')

import warnings
warnings.filterwarnings('ignore')

import akshare as ak
import pandas as pd
from pathlib import Path
from datetime import date, timedelta, datetime
import argparse
import time

OUTPUT_DIR = Path("/root/clabin_sync/LOTT/DL/daily/warehouse_receipts_agg")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 各交易所品种列表
SHFE_VARS  = ['CU','AL','ZN','PB','NI','SN','AU','AG','RB','WR','HC','FU','BU','RU','SP','SS','LU','BC']
DCE_VARS   = ['A','B','C','CS','M','Y','P','L','V','PP','EG','EB','PG','LH','J','JM','I','LD','FB','BB','RR']
CZCE_VARS  = ['CF','SR','TA','MA','FG','SF','SM','OI','RI','LR','JR','WH','PM','RS','RM','ZC','AP','CJ','UR','SA','PK','PF','PX','SH']
GFEX_VARS  = ['SI','LC','PS','PT']


def collect_receipt(date_str, exchange_filter=None):
    """提取指定日期仓单，返回 {exchange: DataFrame}"""
    results = {}
    exchanges = ['SHFE','DCE','CZCE','GFEX'] if exchange_filter is None else [exchange_filter]
    
    for exch in exchanges:
        vars_list = {'SHFE': SHFE_VARS, 'DCE': DCE_VARS, 'CZCE': CZCE_VARS, 'GFEX': GFEX_VARS}.get(exch, [])
        if not vars_list:
            continue
        
        try:
            print(f"  [{exch}] {date_str} ...", end=' ', flush=True)
            df = ak.get_receipt(start_date=date_str, end_date=date_str, vars_list=vars_list)
            
            if df is None or (hasattr(df, 'empty') and df.empty):
                print("⚠️ 无数据")
                results[exch] = None
            else:
                print(f"✅ {len(df)} 条")
                results[exch] = df
                
        except Exception as e:
            err = type(e).__name__
            if 'JSONDecodeError' in err or '412' in str(e):
                print(f"❌ WAF封锁")
            else:
                print(f"❌ {err}: {str(e)[:60]}")
            results[exch] = None
        
        time.sleep(0.3)
    
    return results


def save_receipts(results, date_str):
    """保存仓单，每品种一个 CSV（追加模式）"""
    total_saved = 0
    for exch, df in results.items():
        if df is None or (hasattr(df, 'empty') and df.empty):
            continue
        
        exch_dir = OUTPUT_DIR / exch
        exch_dir.mkdir(exist_ok=True)
        
        for _, row in df.iterrows():
            variety = str(row.get('var', '')).strip()
            if not variety:
                continue
            
            filepath = exch_dir / f"{variety}.csv"
            new_row = pd.DataFrame([{
                'date': date_str,
                'var': variety,
                'receipt': row.get('receipt', 0),
                'receipt_chg': row.get('receipt_chg', 0),
            }])
            
            if filepath.exists():
                existing = pd.read_csv(filepath)
                if date_str in existing['date'].astype(str).values:
                    continue  # 已存在则跳过
                combined = pd.concat([existing, new_row], ignore_index=True)
            else:
                combined = new_row
            
            combined.to_csv(filepath, index=False)
            total_saved += 1
    
    return total_saved


def main():
    parser = argparse.ArgumentParser(description='期货仓单日度提取')
    parser.add_argument('--date',  type=str, default=None, help='指定日期 YYYYMMDD（默认昨日）')
    parser.add_argument('--start', type=str, default=None, help='开始日期 YYYYMMDD')
    parser.add_argument('--end',   type=str, default=None, help='结束日期 YYYYMMDD')
    args = parser.parse_args()

    if args.date:
        dates = [args.date]
    elif args.start and args.end:
        s = datetime.strptime(args.start, '%Y%m%d')
        e = datetime.strptime(args.end,   '%Y%m%d')
        dates = [(s + timedelta(days=i)).strftime('%Y%m%d') for i in range((e-s).days + 1)]
    else:
        dates = [(date.today() - timedelta(days=1)).strftime('%Y%m%d')]

    print("=" * 60)
    print(f"🚀 仓单提取 — {', '.join(dates)}")
    print("=" * 60)
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    print("接口状态:")
    print("  SHFE ✅  get_receipt  广期所 ✅  get_receipt")
    print("  郑商所 ✅  get_receipt  大商所 ❌  WAF封锁")
    print()

    total_saved = 0
    for d in dates:
        print(f"\n[{d}]")
        results = collect_receipt(d)
        saved = save_receipts(results, d)
        total_saved += saved
        print(f"  → 保存 {saved} 条记录")

    print(f"\n{'=' * 60}")
    print(f"✅ 完成，共保存 {total_saved} 条记录")


if __name__ == "__main__":
    main()
