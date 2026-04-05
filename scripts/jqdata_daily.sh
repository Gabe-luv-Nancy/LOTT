#!/bin/bash
# JQData 全量下载 - 每日定时任务
# 模式: frequency (按频率), 下载 1分钟K线

cd /root/clabin_sync/LOTT/scripts || exit 1

# 确保日志目录存在
mkdir -p /root/clabin_sync/LOTT/DL/JQData/logs

echo "[$(date)] JQData 全量下载开始..."

python3 jqdata_downloader.py \
    --mode frequency \
    --freq 1m

echo "[$(date)] JQData 全量下载完成."
