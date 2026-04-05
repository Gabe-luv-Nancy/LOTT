#!/usr/bin/env python3
"""
六大交易所期货日度数据下载 - 动态合约版

核心改进：从交易所API动态获取当前合约列表，不再依赖硬编码
修复了CFFEX/INE/GFEX/CZCE的"list index out of range"问题

接口策略：
- SHFE:  get_shfe_daily()     → 全量历史 ✅
- DCE:   动态获取合约列表   → 逐合约
- CZCE:  get_czce_daily()    → 当日全量 ✅
- CFFEX: get_cffex_daily()   → 当日全量 ✅
- INE:   get_ine_daily()     → 全量历史 ✅
- GFEX:  get_gfex_daily()   → 全量历史 ✅
"""
import sys
sys.path.insert(0, '/root/clabin_sync/LOTT/scripts')

import akshare as ak
from pathlib import Path
import time
from datetime import date
import traceback

DATA = Path("/root/clabin_sync/LOTT/DL/daily")
DATA.mkdir(parents=True, exist_ok=True)

TODAY = date.today()
TODAY_STR = TODAY.strftime("%Y%m%d")


# ===== 合约动态获取 =====

def get_active_contracts_shfe():
    """从SHFE JSON获取当前挂牌合约"""
    df = ak.get_shfe_daily()
    # 获取最近有交易的合约
    df = df[df["date"] == df["date"].max()]
    syms = df["symbol"].str.lower().tolist()
    return syms


def get_active_contracts_dce():
    """从DCE官网获取当前合约（带日期参数）"""
    try:
        # 试最近几个交易日
        for days_back in range(0, 10):
            d = date.today()
            from datetime import timedelta
            d = d - timedelta(days=days_back)
            d_str = d.strftime("%Y%m%d")
            try:
                df = ak.get_dce_daily(date=d_str)
                if not df.empty:
                    return df["symbol"].tolist()
            except:
                pass
    except:
        pass
    return []


def get_active_contracts_czce():
    """从CZCE获取当前合约"""
    try:
        df = ak.get_czce_daily(date=TODAY_STR)
        return df["symbol"].tolist()
    except:
        return []


def get_active_contracts_cffex():
    """从CFFEX获取当前合约"""
    try:
        df = ak.get_cffex_daily()
        return df["symbol"].tolist()
    except:
        return []


def get_active_contracts_ine():
    """从INE获取当前合约"""
    try:
        df = ak.get_ine_daily()
        return df["symbol"].tolist()
    except:
        return []


def get_active_contracts_gfex():
    """从GFEX获取当前合约"""
    try:
        df = ak.get_gfex_daily()
        return df["symbol"].tolist()
    except:
        return []


# ===== 各交易所下载 =====

def download_shfe():
    print("\n[SHFE] 官网JSON全量...")
    try:
        df = ak.get_shfe_daily()
        # date: YYYYMMDD → YYYY-MM-DD
        df["date"] = df["date"].astype(str)
        df["date"] = df["date"].str[:4] + "-" + df["date"].str[4:6] + "-" + df["date"].str[6:8]
        df["symbol"] = df["symbol"].str.lower()

        exchange_dir = DATA / "SHFE"
        exchange_dir.mkdir(exist_ok=True)

        saved = 0
        for sym, grp in df.groupby("symbol"):
            grp = grp.drop(columns=["index"], errors="ignore")
            grp.to_csv(exchange_dir / f"{sym}.csv", index=False)
            saved += 1
        print(f"  ✅ {saved} 合约, {len(df)} 条")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


def download_dce():
    print("\n[DCE] 逐合约下载...")
    symbols = get_active_contracts_dce()
    if not symbols:
        # 兜底：用已知活跃合约
        symbols = ['m2607', 'm2609', 'm2611', 'y2607', 'y2609', 'y2611',
                   'a2607', 'a2609', 'b2606', 'c2607', 'c2609',
                   'cs2607', 'cs2609', 'p2607', 'l2607', 'l2609',
                   'v2607', 'v2609', 'pp2607', 'pp2609',
                   'eg2609', 'eb2609', 'pg2607', 'jd2606']
        print(f"  兜底合约列表: {len(symbols)} 个")

    exchange_dir = DATA / "DCE"
    exchange_dir.mkdir(exist_ok=True)

    success, failed = 0, []
    for sym in symbols:
        try:
            df = ak.futures_zh_daily_sina(symbol=sym)
            if len(df) > 0:
                df.to_csv(exchange_dir / f"{sym}.csv", index=False)
                success += 1
            else:
                failed.append(f"{sym}(empty)")
        except Exception as e:
            failed.append(f"{sym}({type(e).__name__})")
        time.sleep(0.3)

    print(f"  ✅ {success} 成功, {len(failed)} 失败")
    if failed:
        print(f"  失败: {failed[:3]}{'...' if len(failed)>3 else ''}")
    return success


def download_czce():
    print("\n[CZCE] 当日全量...")
    try:
        df = ak.get_czce_daily(date=TODAY_STR)
        if df.empty:
            print("  ⚠️ 今日无数据")
            return 0

        # date: YYYYMMDD → YYYY-MM-DD
        df["date"] = df["date"].astype(str).str[:4] + "-" + df["date"].astype(str).str[4:6] + "-" + df["date"].astype(str).str[6:8]

        exchange_dir = DATA / "CZCE"
        exchange_dir.mkdir(exist_ok=True)

        saved = 0
        for sym, grp in df.groupby("symbol"):
            grp.to_csv(exchange_dir / f"{sym}.csv", index=False)
            saved += 1
        print(f"  ✅ {saved} 合约")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


def download_cffex():
    print("\n[CFFEX] 当日全量...")
    try:
        df = ak.get_cffex_daily()
        if df.empty:
            print("  ⚠️ 今日无数据")
            return 0

        # date: YYYYMMDD → YYYY-MM-DD
        df["date"] = df["date"].astype(str).str[:4] + "-" + df["date"].astype(str).str[4:6] + "-" + df["date"].astype(str).str[6:8]

        exchange_dir = DATA / "CFFEX"
        exchange_dir.mkdir(exist_ok=True)

        saved = 0
        for sym, grp in df.groupby("symbol"):
            grp.to_csv(exchange_dir / f"{sym}.csv", index=False)
            saved += 1
        print(f"  ✅ {saved} 合约")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


def download_ine():
    print("\n[INE] 全量历史...")
    try:
        df = ak.get_ine_daily()
        if df.empty:
            print("  ⚠️ 无数据")
            return 0

        exchange_dir = DATA / "INE"
        exchange_dir.mkdir(exist_ok=True)

        saved = 0
        for sym, grp in df.groupby("symbol"):
            grp.to_csv(exchange_dir / f"{sym}.csv", index=False)
            saved += 1
        print(f"  ✅ {saved} 合约, {len(df)} 条")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


def download_gfex():
    print("\n[GFEX] 全量历史...")
    try:
        df = ak.get_gfex_daily()
        if df.empty:
            print("  ⚠️ 无数据")
            return 0

        exchange_dir = DATA / "GFEX"
        exchange_dir.mkdir(exist_ok=True)

        saved = 0
        for sym, grp in df.groupby("symbol"):
            grp.to_csv(exchange_dir / f"{sym}.csv", index=False)
            saved += 1
        print(f"  ✅ {saved} 合约, {len(df)} 条")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


# ===== 主程序 =====

def main():
    print("=" * 60)
    print(f"🚀 日度数据下载 — {TODAY}")
    print("=" * 60)

    r = {}
    r["SHFE"] = download_shfe()
    r["DCE"]  = download_dce()
    r["CZCE"] = download_czce()
    r["CFFEX"] = download_cffex()
    r["INE"]  = download_ine()
    r["GFEX"] = download_gfex()

    total_contracts = 0
    total_rows = 0
    print("\n" + "=" * 60)
    print("📊 结果:")
    for exch, count in r.items():
        ed = DATA / exch
        if ed.exists():
            files = list(ed.glob("*.csv"))
            if files:
                lines = sum(1 for f in files for line in open(f) if line.strip()) - len(files)
                total_contracts += len(files)
                total_rows += lines
                print(f"   {exch}: {len(files)} 合约, {lines} 行")

    print(f"\n   总计: {total_contracts} 合约, {total_rows} 行")
    print(f"   保存: {DATA}")


if __name__ == "__main__":
    main()
