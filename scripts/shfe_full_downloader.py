#!/usr/bin/env python3
"""
SHFE Historical Daily Data Downloader
Downloads kx (daily trading) data from SHFE website for a date range.
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import urllib.request
import urllib.error


DATA_DIR = Path("/root/clabin_sync/LOTT/DL/shfe/daily")
LOG_FILE = "/tmp/shfe_full_download.log"


def download_kx(date_str):
    """Download kx data for a specific date (YYYYMMDD format)."""
    url = f"https://www.shfe.com.cn/data/tradedata/future/dailydata/kx{date_str}.dat"
    out_file = DATA_DIR / f"kx_{date_str}.dat"

    if out_file.exists():
        return "skipped", f"{date_str} already exists"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        instruments = data.get("o_curinstrument", [])
        if not instruments:
            return "failed", f"{date_str} empty response"

        # Filter out subtotal rows
        real = [i for i in instruments if i.get("DELIVERYMONTH") != "小计"]
        if not real:
            return "failed", f"{date_str} no real contracts"

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return "success", f"{date_str} -> {len(real)} contracts"

    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "holiday", f"{date_str} not a trading day (404)"
        return "failed", f"{date_str} HTTP {e.code}"
    except Exception as e:
        return "failed", f"{date_str} {e}"


def is_trading_day(date_obj):
    """Simple check: skip weekends."""
    return date_obj.weekday() < 5  # Monday=0 ... Friday=4


def main():
    parser = argparse.ArgumentParser(description="SHFE Historical Data Downloader")
    parser.add_argument("--start", default=None, help="Start date YYYYMMDD")
    parser.add_argument("--end", default=None, help="End date YYYYMMDD")
    parser.add_argument("--date", default=None, help="Single date YYYYMMDD")
    parser.add_argument("--export", action="store_true", help="Alias for single date (yesterday)")
    parser.add_argument("--data-dir", default=None, help="Override data dir")
    args = parser.parse_args()

    if args.data_dir:
        global DATA_DIR
        DATA_DIR = Path(args.data_dir)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now()

    # Determine date range
    if args.date:
        dates = [args.date]
    elif args.export:
        yesterday = (today - timedelta(days=1)).strftime("%Y%m%d")
        dates = [yesterday]
    elif args.start and args.end:
        start_dt = datetime.strptime(args.start, "%Y%m%d")
        end_dt = datetime.strptime(args.end, "%Y%m%d")
        dates = []
        d = start_dt
        while d <= end_dt:
            if is_trading_day(d):
                dates.append(d.strftime("%Y%m%d"))
            d += timedelta(days=1)
    else:
        print("Specify --start/--end or --date or --export")
        sys.exit(1)

    results = {"success": 0, "skipped": 0, "failed": 0, "holiday": 0}
    log_lines = []

    for i, date_str in enumerate(dates):
        status, msg = download_kx(date_str)
        results[status] = results.get(status, 0) + 1

        log_line = f"[{i+1}/{len(dates)}] {status.upper()} {msg}"
        print(log_line)
        log_lines.append(log_line)

        # Rate limit: be nice to SHFE servers
        if status == "success":
            time.sleep(1.5)

    summary = (f"\nDone: {results['success']} success, {results['skipped']} skipped, "
               f"{results['failed']} failed, {results['holiday']} holidays")
    print(summary)
    log_lines.append(summary)

    with open(LOG_FILE, "a") as f:
        f.write("\n".join(log_lines) + "\n")


if __name__ == "__main__":
    main()
