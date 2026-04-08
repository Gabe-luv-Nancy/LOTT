# DL 任务协作说明

> 本文档供本地 OpenClaw 部署参考。2026-04-08。

---

## 一、系统架构

```
┌─────────────────────────────────────────────────────┐
│  云端 OpenClaw（81.70.200.211）                     │
│  职责：数据采集、Cron 调度、网络可及的数据源         │
│  目录：/root/clabin_sync/LOTT/DL/                  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  本地 OpenClaw（用户 PC）                    │  │
│  │  职责：交易所/券商反爬封锁的数据源            │  │
│  │  目录：/root/clabin_sync/LOTT/DL/            │  │
│  │  （通过 Syncthing 双向同步）                 │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
              ↑ Syncthing 双向同步 ↓
```

**文件同步**：Syncthing
- 云端目录：`/root/clabin_sync/`
- 本地目录：`X:\CLABIN\`
- 同步密码：`Lottgoeswell0325`
- 两端 Device ID 已在 Syncthing 控制台配置

---

## 二、我（云端 OpenClaw）负责什么

### 2.1 日度 OHLCV 数据采集

| 交易所 | 脚本 | 数据窗口 | 说明 |
|--------|------|---------|------|
| SHFE | `akshare_all_exchanges.py` | 全量历史 | 官网 kx JSON，每日更新 |
| DCE | `akshare_all_exchanges.py` | 2025-05 起 | 逐合约 sina 接口，每日更新 |
| CZCE | `akshare_all_exchanges.py` | 当日（用昨日期） | 交易所 17:00 后发布 |
| CFFEX | `akshare_all_exchanges.py` | 当日（用昨日期） | 同上 |
| INE | `akshare_all_exchanges.py` | 当日（用昨日期） | 同上 |
| GFEX | `akshare_all_exchanges.py` | 当日（用昨日期） | 同上 |

**路径**：`/root/clabin_sync/LOTT/DL/daily/{SHFE,DCE,CZCE,CFFEX,INE,GFEX}/`
**命名**：`{symbol}.csv`
**字段**：`date,open,high,low,close,volume,hold,settle`

### 2.2 分钟 OHLCV 数据

**脚本**：`minute_collector.py`
**周期**：1m / 5m / 15m / 30m / 60m
**路径**：`/root/clabin_sync/LOTT/DL/minute_history/{SHFE,DCE,CFFEX,INE,GFEX}/`
**命名**：`{symbol}_{N}m_history.csv`
**字段**：`datetime,open,high,low,close,volume,hold`

### 2.3 仓单数据（我这边能拿到）

| 来源 | 脚本 | 字段 | 路径 |
|------|------|------|------|
| SHFE | `receipt_collector.py` | `date,var,receipt,receipt_chg` | `warehouse_receipts_agg/SHFE/` |
| CZCE 详细 | `akshare_all_exchanges.py` | `date,仓库,品牌,仓单数量,增减` | `warehouse_receipts/CZCE/` |
| GFEX 详细 | `akshare_all_exchanges.py` | `date,品种,仓库,昨日/今日仓单量,增减` | `warehouse_receipts/GFEX/` |
| 东方财富库存 | `receipt_collector.py` | `date,var,inventory,change` | `warehouse_receipts_agg/EM_INVENTORY/` |

**东方财富覆盖 53 品种**：铁矿石/焦炭/焦煤/螺纹钢/塑料/PP/乙二醇/PTA/甲醇/白糖/棉花/沪铜/沪铝/沪金等

### 2.4 定时任务

| 任务名 | cron | 说明 |
|--------|------|------|
| DL-daily | `0 17 * * *` | 日度 OHLCV（六交易所） |
| DL-仓单提取 | `0 17 * * *` | 仓单 + 东方财富库存 |
| DL-1min-day1/2/3 | `0 9,13,15 * * 1-5` | 分钟数据日间采集 |
| DL-1min-night1/2 | `0 21,23 * * 1-5` | 分钟数据夜盘采集 |
| DL-5min-daily | `30 16 * * 1-5` | 5 分钟数据 |
| DL-weekly | `0 18 * * 0` | SHFE kx 原始文件 |

---

## 三、本地 OpenClaw 负责什么

### 3.1 我这边无法获取的数据

| 数据源 | 问题 | 本地 akshare 方案 |
|--------|------|-----------------|
| **DCE 仓单** | HTTP 412 WAF 封锁 | 暂无，依赖东方财富库存替代 |
| **DCE 日度（交易所级）** | 接口全天 JSONDecodeError | `futures_zh_daily_sina()` 单合约替代，每日更新 |
| **99qh 库存** | HTTP 412 WAF 封锁 | 暂无，依赖东方财富库存替代 |

### 3.2 两端协同方式

本地部署同款 OpenClaw 后，参照上述定时任务配置。数据通过 Syncthing 双向同步至同一目录，云端优先写入仓单和东方财富库存数据。

---

## 四、目录分工约定

为避免冲突，两端按以下目录分工：

### 云端独占（本地不写）
```
/root/clabin_sync/LOTT/DL/
├── daily/{SHFE,DCE,CZCE,CFFEX,INE,GFEX}/   ← 日度 OHLCV
├── minute_history/                             ← 分钟 OHLCV
├── shfe/daily/                               ← SHFE kx 原始
└── (定时任务均在此侧)
```

### Syncthing 同步目录（两端共用）
```
/root/clabin_sync/LOTT/DL/daily/
├── warehouse_receipts/                        ← 仓单详细（CZCE/GFEX）
└── warehouse_receipts_agg/                    ← 仓单汇总 + 东方财富库存
```

> **注意**：Syncthing 同步时以最后修改时间为准，避免两端同时写入同一文件。

---

## 五、接口状态速查

| 接口 | 函数 | 状态 | 云端可用？ |
|------|------|------|---------|
| SHFE 仓单 | `get_receipt()` | ✅ | ✅ |
| CZCE 仓单 | `futures_warehouse_receipt_czce()` | ✅ | ✅ |
| GFEX 仓单 | `futures_gfex_warehouse_receipt()` | ✅ | ✅ |
| DCE 仓单 | `get_receipt()` | ❌ 412 | ❌ |
| 99qh 库存 | `futures_inventory_99()` | ❌ 412 | ❌ |
| 东方财富库存 | `futures_inventory_em()` | ✅ 53品种 | ✅ |
| DCE 日度（交易所级） | `get_dce_daily()` | ❌ JSONDecode | ✅（sina 单合约替代） |

---

## 六、关键脚本路径

```
/root/clabin_sync/LOTT/scripts/
├── akshare_all_exchanges.py     # 日度 OHLCV + CZCE/GFEX 详细仓单 + SHFE 汇总仓单
├── receipt_collector.py         # 仓单汇总 + 东方财富库存（支持 --date/--start/--end）
├── minute_collector.py          # 分钟 OHLCV 采集
├── jqdata_downloader.py        # JQData 日线
└── shfe_full_downloader.py     # SHFE kx.dat 原始文件
```
