#!/usr/bin/env python3
"""
Merge recent minute_history data from /root/.openclaw/DL/ into
/root/clabin_sync/LOTT/DL/minute_history/
For each contract/period: append new rows (skip duplicates by datetime)
"""
import pandas as pd
from pathlib import Path
import shutil

SRC = Path("/root/.openclaw/DL/minute_history/")
DST = Path("/root/clabin_sync/LOTT/DL/minute_history/")

# Only process these exchanges
EXCHANGES = ["SHFE", "DCE", "CZCE", "CFFEX", "INE", "GFEX"]

total_merged = 0
total_new = 0

for exchange in EXCHANGES:
    src_dir = SRC / exchange
    dst_dir = DST / exchange
    if not src_dir.exists():
        print(f"  [SKIP] {exchange} (no source)")
        continue
    if not dst_dir.exists():
        # Copy entire exchange dir if doesn't exist
        shutil.copytree(src_dir, dst_dir)
        print(f"  [COPY] {exchange} (new) -> {len(list(src_dir.glob('*.csv')))} files")
        continue

    # Merge each CSV
    for src_file in src_dir.glob("*.csv"):
        dst_file = dst_dir / src_file.name
        try:
            src_df = pd.read_csv(src_file)
            if dst_file.exists():
                dst_df = pd.read_csv(dst_file)
                # Merge: concat then dedupe by datetime, keep original order
                merged = pd.concat([dst_df, src_df], ignore_index=True)
                merged = merged.drop_duplicates(subset=["datetime"], keep="first")
                merged = merged.sort_values("datetime").reset_index(drop=True)
                before = len(dst_df)
                merged.to_csv(dst_file, index=False)
                new_rows = len(merged) - before
                total_merged += 1
                if new_rows > 0:
                    total_new += new_rows
                    print(f"  [MERGED] {exchange}/{src_file.name}: +{new_rows} rows")
            else:
                # New file - just copy
                shutil.copy2(src_file, dst_file)
                total_new += len(src_df)
                print(f"  [NEW] {exchange}/{src_file.name}: +{len(src_df)} rows")
        except Exception as e:
            print(f"  [ERROR] {exchange}/{src_file.name}: {e}")

print(f"\nDone. {total_merged} files merged, {total_new} new rows added.")
print(f"Syncthing will now sync these to your local machine.")
