# Core 核心模块

Frontend 的核心基础设施层，提供全局性的配置、信号通信、数据管理能力。

## 文件清单

| 文件 | 类 | 模式 | 说明 |
|------|-----|------|------|
| `config.py` | `FrontendConfig` | 单例 | 全局配置管理，JSON 加载/保存，点分路径访问 |
| `signal_bus.py` | `SignalBus` | 单例 | Qt pyqtSignal 信号总线，跨模块解耦通信 |
| `data_manager.py` | `DataManager`, `BarData` | QObject | K线数据管理，时间索引，增删改查 |
| `data_proxy.py` | `DataProxy` | 普通类 | 数据缓存（LRU+TTL）、格式转换、LTTB降采样 |

## 设计原则

1. **单例模式**：`FrontendConfig` 和 `SignalBus` 全局唯一，任何模块可直接访问
2. **Qt 信号驱动**：所有数据变化通过 pyqtSignal 通知，不使用回调函数
3. **数据与显示分离**：`DataManager` 只管数据，不关心如何渲染

## 使用示例

```python
from Frontend.core import FrontendConfig, SignalBus, DataManager, DataProxy, BarData

# 配置
config = FrontendConfig()
db_path = config.get('database.path')

# 信号总线
bus = SignalBus()
bus.sigDataLoaded.connect(lambda src: print(f"数据加载: {src}"))

# 数据管理
dm = DataManager()
dm.update_bar(BarData(datetime=..., open_price=100, high_price=105, ...))

# 数据代理
proxy = DataProxy(dm)
ohlc = proxy.get_ohlc_arrays()
```
