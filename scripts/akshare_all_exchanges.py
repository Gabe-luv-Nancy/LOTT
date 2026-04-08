#!/usr/bin/env python3
"""
六大交易所期货日度数据下载

接口状态（2026-04-08 实测）：
- SHFE 日度 kx:   ✅ 官方kx接口，全量历史
- SHFE 仓单:      ❌ URL已404（网站改版），旧akshare接口失效
- DCE 日度:       ✅ 单合约sina接口（交易所级get_dce_daily已损坏）
- DCE 仓单:       ❌ HTTP 412 WAF封锁（交易所对服务器IP封锁）
- CZCE 日度:      ✅ 官方接口
- CZCE 仓单:      ✅ 官方接口（最早2025-11-03）
- CFFEX 日度:     ✅ 官方接口
- INE 日度:       ✅ 官方接口
- GFEX 日度:      ✅ 官方接口
- GFEX 仓单:      ✅ 官方接口（最早2024-01-22）
"""
import sys
sys.path.insert(0, '/root/clabin_sync/LOTT/scripts')

import akshare as ak
from pathlib import Path
import time
from datetime import date as _date, timedelta
import traceback

DATA = Path("/root/clabin_sync/LOTT/DL/daily")
DATA.mkdir(parents=True, exist_ok=True)

TODAY = _date.today()
TODAY_STR = (TODAY - timedelta(days=1)).strftime("%Y%m%d")


# ===== 合约动态获取 =====

def get_active_contracts_shfe():
    """从SHFE kx接口获取当前挂牌合约"""
    try:
        df = ak.get_shfe_daily()
        df = df[df["date"] == df["date"].max()]
        return df["symbol"].str.lower().tolist()
    except:
        return []


def get_active_contracts_dce():
    """从DCE尝试获取当前合约列表（备用）"""
    # get_dce_daily 从2025年底起损坏，改用 sina 单合约
    # 返回空列表，强制走 fallback
    return []


def get_active_contracts_czce():
    try:
        df = ak.get_czce_daily(date=TODAY_STR)
        return df["symbol"].tolist()
    except:
        return []


def get_active_contracts_cffex():
    try:
        df = ak.get_cffex_daily()
        return df["symbol"].tolist()
    except:
        return []


def get_active_contracts_ine():
    try:
        df = ak.get_ine_daily()
        return df["symbol"].tolist()
    except:
        return []


def get_active_contracts_gfex():
    try:
        df = ak.get_gfex_daily()
        return df["symbol"].tolist()
    except:
        return []


# ===== 各交易所日度数据下载 =====

def download_shfe():
    """SHFE kx.dat 全量历史（日度 OHLCV + 持仓）"""
    print("\n[SHFE] 官网kx全量...")
    try:
        df = ak.get_shfe_daily()
        df["date"] = df["date"].astype(str).str[:4] + "-" + df["date"].astype(str).str[4:6] + "-" + df["date"].astype(str).str[6:8]
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


def _dce_fallback_symbols():
    """DCE fallback 活跃合约列表（211个，覆盖全品种+多月份）"""
    return [
        # 黑色金属（顶级交易量）
        'i2605','i2607','i2608','i2609','i2610','i2611','i2612','i2701',
        'j2605','j2607','j2608','j2609','j2610','j2611','j2701',
        'jm2605','jm2607','jm2608','jm2609','jm2610','jm2611','jm2701',
        # 油脂油料
        'm2605','m2607','m2608','m2609','m2611','m2612','m2701',
        'y2605','y2607','y2608','y2609','y2611','y2612','y2701',
        'p2605','p2607','p2608','p2609','p2610','p2611','p2612',
        'rm2605','rm2607','rm2608','rm2609','rm2611','rm2612',
        'oi2605','oi2607','oi2608','oi2609','oi2611','oi2612',
        'rs2607','rs2609','rs2611',
        # 农产品
        'a2605','a2607','a2609','a2611','a2612',
        'b2604','b2605','b2606','b2607','b2608',
        'c2605','c2607','c2609','c2611','c2612',
        'cs2605','cs2607','cs2609','cs2611',
        'wh2605','wh2607','wh2609','wh2611',
        'pm2605','pm2607','pm2609',
        'jr2605','jr2607','jr2609',
        'lr2605','lr2607','lr2609',
        'ri2605','ri2607','ri2609',
        'cf2605','cf2607','cf2609','cf2611',
        'sr2605','sr2607','sr2609','sr2611',
        # 化工
        'l2605','l2607','l2608','l2609','l2611','l2701',
        'v2605','v2607','v2608','v2609','v2611','v2701',
        'pp2605','pp2607','pp2608','pp2609','pp2611','pp2701',
        'eg2605','eg2607','eg2608','eg2609','eg2611',
        'eb2605','eb2607','eb2608','eb2609','eb2611',
        'pg2605','pg2606','pg2607','pg2608','pg2609','pg2611',
        # 软商品/工业品
        'ta2605','ta2607','ta2608','ta2609','ta2611',
        'ma2605','ma2607','ma2608','ma2609','ma2611',
        'fg2605','fg2607','fg2608','fg2609','fg2611',
        'sf2605','sf2607','sf2608','sf2609','sf2611',
        'sm2605','sm2607','sm2608','sm2609','sm2611',
        'ur2605','ur2607','ur2608','ur2609',
        'sa2605','sa2607','sa2608','sa2609',
        'ap2605','ap2607','ap2608','ap2609','ap2611',
        'cj2605','cj2607','cj2609',
        'pk2605','pk2607','pk2608','pk2609',
        'pf2605','pf2606','pf2607','pf2608','pf2609',
        'px2605','px2607','px2608','px2609',
        'sh2605','sh2607','sh2608','sh2609',
        # 生猪
        'lh2605','lh2607','lh2608','lh2609','lh2611',
        # 其他
        'rr2605','rr2606','rr2607','rr2608',
        'fb2605','fb2607','fb2609',
        'bb2605','bb2607','bb2609',
    ]


def download_dce():
    """DCE 单合约 sina 接口（交易所级 get_dce_daily 已损坏）"""
    print("\n[DCE] 逐合约下载...")
    symbols = _dce_fallback_symbols()
    print(f"  合约列表: {len(symbols)} 个")

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
        time.sleep(0.25)

    print(f"  ✅ {success} 成功, {len(failed)} 失败")
    if failed[:3]:
        print(f"  失败样例: {failed[:3]}{'...' if len(failed)>3 else ''}")
    return success


def download_czce():
    print(f"\n[CZCE] 当日全量 ({TODAY_STR})...")
    try:
        df = ak.get_czce_daily(date=TODAY_STR)
        if df.empty:
            print("  ⚠️ 今日无数据（交易所尚未发布）")
            return 0
        df["date"] = df["date"].astype(str).str[:4] + "-" + df["date"].astype(str).str[4:6] + "-" + df["date"].astype(str).str[6:8]
        exchange_dir = DATA / "CZCE"
        exchange_dir.mkdir(exist_ok=True)
        saved = sum(1 for sym, grp in df.groupby("symbol") if grp.to_csv(exchange_dir / f"{sym}.csv", index=False) is None)
        print(f"  ✅ {saved} 合约")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


def download_cffex():
    print(f"\n[CFFEX] 当日全量 ({TODAY_STR})...")
    try:
        df = ak.get_cffex_daily(date=TODAY_STR)
        if df.empty:
            print("  ⚠️ 今日无数据（交易所尚未发布）")
            return 0
        df["date"] = df["date"].astype(str).str[:4] + "-" + df["date"].astype(str).str[4:6] + "-" + df["date"].astype(str).str[6:8]
        exchange_dir = DATA / "CFFEX"
        exchange_dir.mkdir(exist_ok=True)
        saved = sum(1 for sym, grp in df.groupby("symbol") if grp.to_csv(exchange_dir / f"{sym}.csv", index=False) is None)
        print(f"  ✅ {saved} 合约")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


def download_ine():
    print(f"\n[INE] 当日全量 ({TODAY_STR})...")
    try:
        df = ak.get_ine_daily(date=TODAY_STR)
        if df.empty:
            print("  ⚠️ 无数据")
            return 0
        exchange_dir = DATA / "INE"
        exchange_dir.mkdir(exist_ok=True)
        saved = sum(1 for sym, grp in df.groupby("symbol") if grp.to_csv(exchange_dir / f"{sym}.csv", index=False) is None)
        print(f"  ✅ {saved} 合约, {len(df)} 条")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


def download_gfex():
    print(f"\n[GFEX] 当日全量 ({TODAY_STR})...")
    try:
        df = ak.get_gfex_daily(date=TODAY_STR)
        if df.empty:
            print("  ⚠️ 无数据")
            return 0
        exchange_dir = DATA / "GFEX"
        exchange_dir.mkdir(exist_ok=True)
        saved = sum(1 for sym, grp in df.groupby("symbol") if grp.to_csv(exchange_dir / f"{sym}.csv", index=False) is None)
        print(f"  ✅ {saved} 合约, {len(df)} 条")
        return saved
    except Exception as e:
        print(f"  ❌ {type(e).__name__}: {e}")
        return 0


# ===== 仓单数据 =====

WR_DIR = DATA / "warehouse_receipts"
WR_DIR.mkdir(parents=True, exist_ok=True)


def download_warehouse_receipts():
    """
    下载仓单数据

    接口现状（2026-04-08 实测）：
    - CZCE:  ✅ 可用，最早 2025-11-03
    - GFEX:  ✅ 可用，最早 2024-01-22
    - SHFE:  ❌ URL已404（网站改版，{date}dailystock.dat 不存在）
    - DCE:   ❌ HTTP 412 WAF封锁（交易所对服务器IP拒绝）
    - CFFEX: N/A（金融期货无实物仓单）
    """
    print(f"\n[仓单] CZCE + GFEX ({TODAY_STR})...")

    total = 0

    # CZCE 仓单
    try:
        data = ak.futures_warehouse_receipt_czce(date=TODAY_STR)
        if isinstance(data, dict):
            czce_dir = WR_DIR / "CZCE"
            czce_dir.mkdir(parents=True, exist_ok=True)
            for variety, df in data.items():
                if hasattr(df, 'columns') and not df.empty:
                    df = df.copy()
                    df.insert(0, "date", TODAY.strftime("%Y-%m-%d"))
                    df.to_csv(czce_dir / f"{variety}.csv", index=False)
                    total += 1
            print(f"  CZCE: {len(data)} 品种 ✅")
    except Exception as e:
        print(f"  CZCE ❌ {type(e).__name__}: {e}")

    # GFEX 仓单
    try:
        data = ak.futures_gfex_warehouse_receipt(date=TODAY_STR)
        if isinstance(data, dict):
            gfex_dir = WR_DIR / "GFEX"
            gfex_dir.mkdir(parents=True, exist_ok=True)
            for variety, df in data.items():
                if hasattr(df, 'columns') and not df.empty:
                    df = df.copy()
                    df.insert(0, "date", TODAY.strftime("%Y-%m-%d"))
                    df.to_csv(gfex_dir / f"{variety}.csv", index=False)
                    total += 1
            print(f"  GFEX: {len(data)} 品种 ✅")
    except Exception as e:
        print(f"  GFEX ❌ {type(e).__name__}: {e}")

    # SHFE 仓单：URL已404，标记为不可用
    print(f"  SHFE: ❌ URL已404（网站改版，SHFE改版后旧接口失效）")

    # DCE 仓单：WAF封锁
    print(f"  DCE:  ❌ HTTP 412（交易所WAF封锁服务器IP）")

    print(f"  ✅ 共保存 {total} 个品种仓单")
    return total


# ===== 主程序 =====

def main():
    print("=" * 60)
    print(f"🚀 日度数据下载 — {TODAY}（使用昨日日期: {TODAY_STR}）")
    print("=" * 60)

    r = {}
    r["SHFE"]  = download_shfe()
    r["DCE"]   = download_dce()
    r["CZCE"]  = download_czce()
    r["CFFEX"] = download_cffex()
    r["INE"]   = download_ine()
    r["GFEX"]  = download_gfex()
    r["WR"]    = download_warehouse_receipts()

    total_files = 0
    total_rows = 0
    print("\n" + "=" * 60)
    print("📊 结果:")
    for exch in ["SHFE","DCE","CZCE","CFFEX","INE","GFEX"]:
        ed = DATA / exch
        if ed.exists():
            files = list(ed.rglob("*.csv"))
            if files:
                lines = sum(1 for f in files for line in open(f) if line.strip()) - len(files)
                total_files += len(files)
                total_rows += lines
                print(f"   {exch}: {len(files)} 文件, {lines} 行")
    # 仓单单独统计
    wr_total = 0
    for sub in ["CZCE","GFEX"]:
        wd = WR_DIR / sub
        if wd.exists():
            files = list(wd.rglob("*.csv"))
            if files:
                wr_total += len(files)
    print(f"   WR:   {wr_total} 文件（仓单）")
    print(f"\n   总计: {total_files + wr_total} 文件, {total_rows} 行")
    print(f"   保存: {DATA}")


if __name__ == "__main__":
    main()
