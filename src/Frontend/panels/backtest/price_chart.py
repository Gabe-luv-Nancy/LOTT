"""
价格图表模块

显示回测期间的价格走势，支持叠加交易标记。
"""

from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import Qt, pyqtSignal, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPicture
import pyqtgraph as pg

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from Frontend.core import DataManager, BarData
from Frontend.chart.items import LineItem, CandleItem
from Frontend.chart.markers import TradeMarker, MarkerData, MarkerType


class PriceChart(pg.GraphicsLayoutWidget):
    """
    价格图表
    
    功能：
    - 显示价格折线或K线
    - 叠加交易标记
    - 支持置信区间显示
    - 十字光标追踪
    """
    
    sigCursorMoved = pyqtSignal(int, float)  # (index, price)
    sigRangeChanged = pyqtSignal(tuple)  # (x_min, x_max)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._data_manager: Optional[DataManager] = None
        self._markers: List[TradeMarker] = []
        self._show_markers = True
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        # 创建绘图区域
        self._plot = self.addPlot()
        self._plot.setMenuEnabled(False)
        self._plot.setClipToView(True)
        self._plot.hideAxis('left')
        self._plot.showAxis('right')
        self._plot.hideButtons()
        
        # 配置视图
        self._view = self._plot.getViewBox()
        self._view.setMouseEnabled(x=True, y=False)
        self._view.sigXRangeChanged.connect(self._on_range_changed)
        
        # 价格线元素
        self._price_item: Optional[LineItem] = None
        
        # 十字光标线
        self._vline = pg.InfiniteLine(angle=90, movable=False)
        self._hline = pg.InfiniteLine(angle=0, movable=False)
        self._plot.addItem(self._vline, ignoreBounds=True)
        self._plot.addItem(self._hline, ignoreBounds=True)
        
        # 代理用于鼠标移动事件
        self._proxy = pg.SignalProxy(
            self._plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved
        )
    
    def set_data_manager(self, data_manager: DataManager):
        """设置数据管理器"""
        self._data_manager = data_manager
        
        # 创建价格线
        self._price_item = LineItem(data_manager, field='close')
        self._plot.addItem(self._price_item)
    
    def load_price_data(self, bars: List[BarData]):
        """加载价格数据"""
        if self._data_manager is None:
            self._data_manager = DataManager()
        
        self._data_manager.update_history(bars)
        
        if self._price_item is None:
            self._price_item = LineItem(self._data_manager, field='close')
            self._plot.addItem(self._price_item)
        else:
            self._price_item.update_history(bars)
        
        # 自动调整视图
        self._auto_range()
    
    def add_trade_marker(self, marker: TradeMarker):
        """添加交易标记"""
        self._markers.append(marker)
        self._plot.addItem(marker)
    
    def clear_trade_markers(self):
        """清除所有交易标记"""
        for marker in self._markers:
            self._plot.removeItem(marker)
        self._markers.clear()
    
    def set_show_markers(self, show: bool):
        """设置是否显示标记"""
        self._show_markers = show
        for marker in self._markers:
            marker.setVisible(show)
    
    def _on_range_changed(self, view, range):
        """范围变化处理"""
        self.sigRangeChanged.emit((range[0], range[1]))
        
        # 更新Y轴范围
        if self._data_manager and self._price_item:
            min_ix = max(0, int(range[0]))
            max_ix = min(self._data_manager.get_count(), int(range[1]))
            y_range = self._price_item.get_y_range(min_ix, max_ix)
            self._plot.setRange(yRange=y_range, padding=0.02)
    
    def _on_mouse_moved(self, evt):
        """鼠标移动处理"""
        pos = evt[0]
        if self._plot.sceneBoundingRect().contains(pos):
            mouse_point = self._view.mapSceneToView(pos)
            x = mouse_point.x()
            y = mouse_point.y()
            
            # 更新十字光标
            self._vline.setPos(x)
            self._hline.setPos(y)
            
            # 发送信号
            self.sigCursorMoved.emit(int(x), y)
    
    def _auto_range(self):
        """自动调整范围"""
        if self._data_manager:
            count = self._data_manager.get_count()
            if count > 0:
                self._plot.setRange(xRange=(0, min(200, count)))
    
    def move_to_index(self, index: int):
        """移动到指定索引"""
        if self._data_manager:
            count = self._data_manager.get_count()
            bar_width = 100  # 可见Bar数量
            min_ix = max(0, index - bar_width // 2)
            max_ix = min(count, index + bar_width // 2)
            self._plot.setRange(xRange=(min_ix, max_ix))
    
    def get_price_range(self, start_ix: int = None, end_ix: int = None) -> Tuple[float, float]:
        """获取价格范围"""
        if self._data_manager:
            return self._data_manager.get_price_range(start_ix, end_ix)
        return (0.0, 1.0)