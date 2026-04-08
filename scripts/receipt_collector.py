#!/usr/bin/env python3
"""
期货仓单/库存日度提取脚本

整合两个接口，覆盖全交易所：
  1. get_receipt()  — 注册仓单（来源：akshare推荐方式）
     - SHFE ✅  约2-4周窗口
     - CZCE ✅  历史全量（部分日期Excel损坏）
     - GFEX ✅  成立起
     - DCE  ❌  WAF封锁

  2. futures_inventory_em()  — 东方财富库存数据（来源：你提供的akshare文档）
     - 52个品种可用，覆盖 DCE+CZCE+SHFE
     - 约60个交易日窗口（近3个月）
     - 数据字段：日期/库存/增减
     - DCE: 铁矿石/焦炭/焦煤/塑料/PP/PE/EG/EB/豆粕/豆油/玉米等 ✅
     - CZCE: 甲醇/PTA/白糖/棉花/玻璃等 ✅
     - SHFE: 铜/铝/锌/金/银/螺纹钢等 ✅

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

# ===== get_receipt() 品种列表 =====

SHFE_VARS  = ['CU','AL','ZN','PB','NI','SN','AU','AG','RB','WR','HC','FU','BU','RU','SP','SS','LU','BC']
DCE_VARS   = ['A','B','C','CS','M','Y','P','L','V','PP','EG','EB','PG','LH','J','JM','I','LD','FB','BB','RR']
CZCE_VARS  = ['CF','SR','TA','MA','FG','SF','SM','OI','RI','LR','JR','WH','PM','RS','RM','ZC','AP','CJ','UR','SA','PK','PF','PX','SH']
GFEX_VARS  = ['SI','LC','PS','PT']

# ===== futures_inventory_em() 品种列表（中文名）=====

EM_VARS = [
    # DCE
    '豆一','豆二','豆粕','豆油','棕榈','玉米','玉米淀粉',
    '铁矿石','焦炭','焦煤','螺纹钢','不锈钢',
    '塑料','PVC','聚丙烯','乙二醇','苯乙烯','液化石油气',
    # CZCE
    'PTA','短纤','白糖','郑棉','菜油','菜粕','花生','红枣','苹果',
    '玻璃','纯碱','尿素','锰硅','硅铁','甲醇','橡胶','纸浆',
    '粳米','棉纱','胶版印刷纸','丁二烯橡胶','纯苯','丙烯','瓶片',
    # SHFE / INE / CFFEX
    '沪铜','沪铝','沪锌','沪铅','沪金','沪银',
    '碳酸锂','工业硅','燃油','沥青','20号胶',
]


def collect_receipt(date_str):
    """提取仓单（get_receipt 统一接口）"""
    results = {}
    exchanges = [('SHFE', SHFE_VARS), ('DCE', DCE_VARS), ('CZCE', CZCE_VARS), ('GFEX', GFEX_VARS)]
    
    for exch, vars_list in exchanges:
        try:
            print(f"  [{exch}] 仓单 ...", end=' ', flush=True)
            df = ak.get_receipt(start_date=date_str, end_date=date_str, vars_list=vars_list)
            if df is None or (hasattr(df, 'empty') and df.empty):
                results[exch] = None
                print("⚠️ 无数据")
            else:
                print(f"✅ {len(df)} 条")
                results[exch] = df
        except Exception as e:
            if '412' in str(e) or 'JSONDecodeError' in type(e).__name__:
                print(f"❌ WAF封锁")
            else:
                print(f"❌ {type(e).__name__}: {str(e)[:50]}")
            results[exch] = None
        time.sleep(0.3)
    
    return results


def collect_inventory():
    """提取东方财富库存数据（futures_inventory_em）"""
    results = {}
    
    for sym in EM_VARS:
        try:
            df = ak.futures_inventory_em(symbol=sym)
            if df is not None and not df.empty:
                results[sym] = df
        except Exception:
            pass
        time.sleep(0.15)
    
    return results


def save_receipts(results, date_str):
    """保存仓单（每品种一个 CSV，追加模式）"""
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
                    continue
                combined = pd.concat([existing, new_row], ignore_index=True)
            else:
                combined = new_row
            combined.to_csv(filepath, index=False)
            total_saved += 1
    return total_saved


def save_inventory(inv_results, date_str):
    """保存东方财富库存数据（按品种取最新一行，追加模式）"""
    total_saved = 0
    inv_dir = OUTPUT_DIR / "EM_INVENTORY"
    inv_dir.mkdir(parents=True, exist_ok=True)
    
    for sym, df in inv_results.items():
        if df is None or df.empty:
            continue
        
        # 取最新一行（最近日期）
        latest = df.iloc[-1]
        if latest['日期'] != date_str and latest['日期'] != date_str.replace('-', ''):
            # 如果不是今天的，尝试找对应日期
            matching = df[df['日期'].astype(str).str.replace('-','').str.contains(date_str[:8])]
            if matching.empty:
                # 用最新日期
                latest = df.iloc[-1]
            else:
                latest = matching.iloc[-1]
        
        filepath = inv_dir / f"{sym}.csv"
        new_row = pd.DataFrame([{
            'date': str(latest['日期'])[:10],
            'var': sym,
            'inventory': latest.get('库存', 0),
            'change': latest.get('增减', 0),
        }])
        
        if filepath.exists():
            existing = pd.read_csv(filepath)
            last_date = str(latest['日期'])[:10]
            if last_date in existing['date'].astype(str).values:
                continue
            combined = pd.concat([existing, new_row], ignore_index=True)
        else:
            combined = new_row
        combined.to_csv(filepath, index=False)
        total_saved += 1
    
    return total_saved


def main():
    parser = argparse.ArgumentParser(description='期货仓单/库存日度提取')
    parser.add_argument('--date',  type=str, default=None, help='指定日期 YYYYMMDD（默认昨日）')
    parser.add_argument('--start', type=str, default=None, help='开始日期 YYYYMMDD')
    parser.add_argument('--end',   type=str, default=None, help='结束日期 YYYYMMDD')
    parser.add_argument('--inventory-only', action='store_true', help='仅提取东方财富库存数据')
    parser.add_argument('--receipt-only', action='store_true', help='仅提取仓单数据')
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
    print(f"🚀 仓单+库存提取 — {', '.join(dates)}")
    print("=" * 60)
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    print("接口状态:")
    print("  仓单 get_receipt:    SHFE✅ CZCE✅ GFEX✅ DCE❌WAF封锁")
    print("  库存 futures_em:     52品种✅  约60天窗口（近3个月）")
    print()

    total_receipt = 0
    total_inv = 0

    if not args.inventory_only:
        print("【仓单提取】")
        for d in dates:
            print(f"\n[{d}]")
            results = collect_receipt(d)
            saved = save_receipts(results, d)
            total_receipt += saved
            print(f"  → 保存 {saved} 条记录")

    if not args.receipt_only:
        print("\n【东方财富库存提取】（全量品种一次性拉取）")
        inv_results = collect_inventory()
        print(f"  获取到 {len(inv_results)} 个品种的库存数据")
        for d in dates:
            saved = save_inventory(inv_results, d)
            total_inv += saved
        print(f"  → 今日新增 {total_inv} 条记录")

    print(f"\n{'=' * 60}")
    print(f"✅ 完成: 仓单 {total_receipt} 条 + 库存 {total_inv} 条")


if __name__ == "__main__":
    main()
