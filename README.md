# LOTT - Long-Oriented Trading Terminal

> 量化交易回测系统 | 期货数据采集 + 策略回测

<p align="center">
  <img src="https://img.shields.io/badge/Status-Active-brightgreen.svg" alt="Status">
  <img src="https://img.shields.io/badge/Language-Python-blue.svg" alt="Language">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## 📖 项目简介

LOTT 是一个专注于期货市场的量化交易回测系统，核心理念：

- **数据驱动**：多数据源整合（AkShare、SHFE 官网、JQData 等）
- **定时采集**：分钟级 + 日度数据自动采集
- **策略回测**：支持多种策略框架
- **持续运行**：Cron 驱动的定时任务

---

## 📁 项目结构

```
LOTT/
├── DL/                      # 数据目录
│   ├── akshare_daily/       # AkShare 日度数据
│   ├── minute_history/       # 分钟数据（1/5/15/30/60分钟）
│   ├── shfe/daily/         # SHFE 官网原始数据
│   ├── JQData/             # JQData 数据
│   └── merged/             # 合并后完整数据
│
├── scripts/                 # 采集脚本
│   ├── minute_collector.py   # 分钟数据采集器
│   ├── akshare_downloader.py # AkShare 日度下载
│   ├── shfe_full_downloader.py # SHFE 数据下载
│   └── dl_data_merger.py    # 数据合并工具
│
├── db_benchmark/           # 数据库对比框架
│   └── ...                  # SQLite/PostgreSQL/TimescaleDB 等
│
├── docs/                   # 文档
│   └── TimescaleDB部署教程.md
│
└── README.md               # 本文件
```

---

## 🔧 主要功能

### 数据采集

| 数据源 | 覆盖范围 | 更新频率 |
|--------|----------|----------|
| AkShare | SHFE/DCE/CZCE/CFFEX/INE | 日度 |
| SHFE 官网 | SHFE 全部合约 | 日度 |
| JQData | 全市场分钟数据 | 按需 |
| INE | 国际原油、低硫燃油等 | 日度 |

### 定时任务 (Cron)

| 任务 | 时间 | 说明 |
|------|------|------|
| 1分钟-日间 | 09:00, 13:00, 15:00 (工作日) | 交易时段采集 |
| 1分钟-夜盘 | 21:00, 23:00 (工作日) | 夜盘采集 |
| 5分钟-每日 | 16:30 (工作日) | 收盘后采集 |

---

## 🚀 快速开始

### 安装依赖

```bash
pip install akshare pandas sqlalchemy
```

### 下载日度数据

```bash
python3 scripts/akshare_downloader.py
```

### 采集分钟数据

```bash
# 1分钟数据
python3 scripts/minute_collector.py collect -p 1

# 5分钟数据
python3 scripts/minute_collector.py collect -p 5
```

---

## 📊 支持的期货品种

### 国内期货 (4 所)

| 交易所 | 品种数 | 主要品种 |
|--------|--------|----------|
| SHFE | 50+ | 铜、铝、锌、镍、黄金、白银、螺纹钢、橡胶 |
| DCE | 47+ | 铁矿石、豆粕、玉米、棕榈油 |
| CZCE | 44+ | 甲醇、PTA、动力煤 |
| CFFEX | 27+ | 国债期货、期指 |

### 国际期货

| 交易所 | 品种 |
|--------|------|
| INE | 原油、低硫燃油、20号胶、国际铜 |

---

## 📝 技术栈

- **语言**: Python 3.8+
- **数据库**: SQLite, PostgreSQL, TimescaleDB
- **数据源**: AkShare, SHFE API, JQData
- **调度**: Cron + Python
- **分析**: Pandas, NumPy

---

## 📌 注意事项

- 分钟数据受 AkShare API 限制，单次最多 1023 条
- 历史数据建议优先使用 SHFE 官网 JSON 文件
- DCE/CZCE 有反爬限制，需使用 AkShare 绕过

---

## 📄 License

MIT License

---

## 🔗 Links

- **GitHub**: https://github.com/Gabe-luv-Nancy/LOTT
- **数据目录**: `/root/clabin_sync/LOTT/DL/`
- **相关项目**: [Hippocampus](https://github.com/Gabe-luv-Nancy/hippocampus) - AI 记忆增强系统

---

<p align="center">
  <sub>Built for quantitative trading research</sub>
</p>
