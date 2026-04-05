#!/bin/bash
# JQData 周末补跑脚本
# 用途：当周因配额耗尽导致jqdata_daily被跳过时，周末补跑缺失的日期
# 运行时间：每周六 09:00

cd /root/clabin_sync/LOTT/scripts || exit 1

mkdir -p /root/clabin_sync/LOTT/DL/JQData/logs

echo "[$(date)] JQData 周末补跑开始..."

python3 jqdata_downloader.py \
    --mode frequency \
    --freq 1m \
    --catchup

echo "[$(date)] JQData 周末补跑完成."
