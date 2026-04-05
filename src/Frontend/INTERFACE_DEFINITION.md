# LOTT Frontend 接口定义规范

## 一、核心接口

### 1.1 SignalBus 信号总线

全局单例，通过 Qt pyqtSignal 实现模块间解耦通信。

```python
from Frontend.core import SignalBus

bus = SignalBus()  # 单例

# ====== 数据信号 ======
bus.sigDataLoaded        # (str)           数据加载完成，参数=数据源标识
bus.sigDataUpdated       # (str)           数据更新，参数=数据源标识
bus.sigBarSelected       # (int)           K线选中，参数=bar索引

# ====== 面板信号 ======
bus.sigColumnSelected    # (list)          列选择变化，参数=列哈希列表
bus.sigDateRangeChanged  # (tuple)         日期范围变化，参数=(start, end)
bus.sigCodeSelected      # (str)           代码选择，参数=品种代码

# ====== 回测信号 ======
bus.sigBacktestLoaded    # (object)        回测结果加载，参数=BacktestResult
bus.sigTradeSelected     # (object)        交易记录选中，参数=Trade

# ====== UI信号 ======
bus.sigThemeChanged      # (str)           主题切换，参数=主题名
bus.sigStatusMessage     # (str)           状态栏消息
bus.sigError             # (str)           错误消息
```

### 1.2 FrontendConfig 配置

全局单例，支持点分路径访问。

```python
from Frontend.core import FrontendConfig

config = FrontendConfig()

# 读取配置
db_path = config.get('database.path')         # → "sqlite:///...data.db"
bar_count = config.get('chart.default_bar_count')  # → 200
theme = config.get('theme.name')               # → "dark"

# 修改配置
config.set('chart.animation_enabled', False)

# 加载/保存
config.load('frontend_config.json')
config.save('frontend_config.json')
config.reset()
```

### 1.3 DataManager 数据管理

管理 BarData 列表，提供时间索引查询。

```python
from Frontend.core import DataManager, BarData

dm = DataManager()

# 添加 K线数据
bar = BarData(
    datetime=datetime(2024, 1, 1),
    open_price=100.0, high_price=105.0,
    low_price=98.0, close_price=103.0,
    volume=10000.0,
)
dm.update_bar(bar)

# 批量添加
dm.update_bars([bar1, bar2, bar3])

# 查询
bar = dm.get_bar(index=0)
bars = dm.get_bars(start=10, end=50)
count = dm.get_bar_count()
df = dm.to_dataframe()

# 信号
dm.sigDataUpdated.connect(on_data_updated)
dm.sigDataLoaded.connect(on_data_loaded)
```

### 1.4 DataProxy 数据代理

缓存层 + 数据转换。

```python
from Frontend.core import DataProxy

proxy = DataProxy(data_manager)

# 缓存
proxy.set_cached_data('key', data, ttl=3600)
data = proxy.get_cached_data('key')
proxy.clear_cache()

# 格式转换
ohlc_arrays = proxy.get_ohlc_arrays()  # → dict of numpy arrays
df = proxy.get_dataframe()             # → pandas DataFrame

# 降采样
downsampled = proxy.get_downsampled(max_points=500)
```

---

## 二、面板接口

### 2.1 图层1：DatabasePanel

```python
from Frontend.panels.database import DatabasePanel

panel = DatabasePanel(data_operation=data_op)

# 信号
panel.sigColumnSelected.connect(on_columns)      # (list) 列哈希列表
panel.sigDateRangeSelected.connect(on_range)      # (tuple) (start, end)
panel.sigCodeSelected.connect(on_code)            # (str) 品种代码

# 方法
panel.refresh_data()                  # 刷新数据
panel.get_selected_columns() → list   # 获取选中列
panel.get_date_range() → tuple        # 获取日期范围
```

#### ColumnTreeWidget

```python
from Frontend.panels.database import ColumnTreeWidget

tree = ColumnTreeWidget()
tree.load_metadata(metadata_df)       # 加载元数据 DataFrame
tree.sigColumnsSelected.connect(...)  # (list) 选中的列哈希

# 三级结构：品种代码 → 名称 → 指标
# tree.expand_all() / tree.collapse_all()
```

### 2.2 图层2：VariablePanel

```python
from Frontend.panels.variables import VariablePanel, VariableConfig

panel = VariablePanel()

# 信号
panel.sigVariableAdded.connect(on_add)        # (str) column_hash
panel.sigVariableRemoved.connect(on_remove)    # (str) column_hash
panel.sigVariableConfigChanged.connect(on_cfg) # (str, object) (hash, config)
panel.sigRangeChanged.connect(on_range)        # (tuple) (start, end)
```

#### VariableListWidget

```python
from Frontend.panels.variables import VariableListWidget

vlist = VariableListWidget()
config = vlist.add_variable('hash123', display_name='收盘价', color='#FF6B6B')
vlist.remove_variable('hash123')
vlist.toggle_variable('hash123')
vlist.set_variable_color('hash123', '#00FF00')
configs = vlist.get_all_configs()       # → List[VariableConfig]
visible = vlist.get_visible_configs()   # → List[VariableConfig] (仅可见)
```

#### VariableConfig 数据结构

```python
@dataclass
class VariableConfig:
    column_hash: str = ""           # 列哈希标识
    display_name: str = ""          # 显示名称
    color: QColor = QColor(255, 99, 132)
    lagging: int = 0                # 滞后阶数
    y_axis: int = 0                 # 0=左, 1=右, 2=独立
    line_style: int = 0             # 0=实线, 1=虚线, 2=点线, 3=点划线
    line_width: float = 1.0
    visible: bool = True
    show_confidence_band: bool = False
    confidence_level: float = 0.95
```

### 2.3 图层3：BacktestPanel

```python
from Frontend.panels.backtest import BacktestPanel, BacktestResult, Trade

panel = BacktestPanel()

# 加载回测结果
result = BacktestResult(
    dates=date_list,
    prices=price_array,
    positions=position_array,
    returns=return_array,
    trades=trade_list,
    benchmark_returns=benchmark_array,  # 可选
)
panel.load_result(result)

# 清空
panel.clear()
```

---

## 三、图表接口

### 3.1 ChartWidget

```python
from Frontend.chart import ChartWidget, CandleItem, LineItem

chart = ChartWidget()

# 添加图表元素
chart.add_item(CandleItem(), plot_name='main')
chart.add_item(LineItem(), plot_name='indicator')

# 设置数据
chart.set_data(bar_data_list)
chart.update_data(new_bar)

# 缩放/滚动
chart.zoom_in() / chart.zoom_out()
chart.scroll_left() / chart.scroll_right()
chart.fit_all()
```

### 3.2 MarkerManager

```python
from Frontend.chart import MarkerManager, MarkerData, MarkerType

manager = MarkerManager()

# 添加标记
marker_id = manager.add_marker(TradeMarker(MarkerData(
    marker_type=MarkerType.BUY,
    x=100, y=3500.0,
)))

# 批量操作
manager.get_markers_by_type(MarkerType.BUY)     # 按类型筛选
manager.get_markers_in_range(start_x, end_x)    # 按区间筛选
manager.clear_markers()
```

---

## 四、与后端 Data 层的接口

Frontend 通过 `Data.DataManager.DataOperation` 访问后端数据：

```python
from Data.DataManager.data_operation import DataOperation
from Data.DatabaseManager.database_config import DatabaseConfig

# 初始化
config = DatabaseConfig(db_type='sqlite', db_url='sqlite:///path/to/data.db')
data_op = DataOperation(config)

# 查询数据
df = data_op.query(
    columns=['hash1', 'hash2'],
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31),
)

# 获取元数据
meta_df = data_op.get_data_quality_report()

# 获取列信息
col_df = data_op.get_column_info(level_0='CU')  # 按品种过滤

# 统计
stats = data_op.get_table_stats()
# → {'row_count': 1000, 'meta_count': 50, 'column_count': 48}

# 释放资源
data_op.close()
```
