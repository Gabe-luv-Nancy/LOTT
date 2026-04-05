"""
图表主组件模块

整合所有图表组件，提供完整的图表功能。
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
import pyqtgraph as pg

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from Frontend.core import DataManager, BarData, SignalBus
from Frontend.chart.items import CandleItem, LineItem, BarItem
from Frontend.chart.markers import MarkerManager, TradeMarker, MarkerData, MarkerType
from Frontend.chart.cursor import ChartCursor
from Frontend.chart.overlays import ConfidenceBand


class ChartWidget(QWidget):
    """
    图表主组件
    
    参考: vnpy.chart.widget.ChartWidget
    
    功能：
    - K线图表显示
    - 成交量图表
    - 多图表联动
    - 标记管理
    - 十字光标
    """
    
    # 信号
    sigBarClicked = pyqtSignal(int)           # 点击K线
    sigMarkerClicked = pyqtSignal(object)     # 点击标记
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化组件
        self._data_manager = DataManager()
        self._signal_bus = SignalBus()
        self._marker_manager = MarkerManager()
        
        # 图表项
        self._candle_item: Optional[CandleItem] = None
        self._volume_item: Optional[BarItem] = None
        self._cursor: Optional[ChartCursor] = None
        
        # 绘图区域
        self._plots: Dict[str, pg.PlotItem] = {}
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        # 设置背景色
        self.setStyleSheet("background-color: #1a1a2e;")
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建图形布局
        self._graphics_layout = pg.GraphicsLayoutWidget()
        self._graphics_layout.setBackground('#1a1a2e')
        layout.addWidget(self._graphics_layout)
        
        # 创建价格图表
        self._price_plot = self._graphics_layout.addPlot(row=0, col=0)
        self._price_plot.showGrid(x=True, y=True, alpha=0.3)
        self._price_plot.setMenuEnabled(False)
        self._price_plot.setMouseEnabled(x=True, y=True)
        self._plots['price'] = self._price_plot
        
        # 创建成交量图表
        self._graphics_layout.nextRow()
        self._volume_plot = self._graphics_layout.addPlot(row=1, col=0)
        self._volume_plot.showGrid(x=True, y=True, alpha=0.3)
        self._volume_plot.setMenuEnabled(False)
        self._volume_plot.setMouseEnabled(x=True, y=False)
        self._volume_plot.setMaximumHeight(150)
        self._plots['volume'] = self._volume_plot
        
        # 链接X轴
        self._volume_plot.setXLink(self._price_plot)
        
        # 创建信息标签
        self._info_label = QLabel()
        self._info_label.setStyleSheet(
            "color: white; background-color: transparent; padding: 5px;"
        )
        self._info_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        # 连接信号
        self._price_plot.scene().sigMouseClicked.connect(self._on_clicked)
    
    def set_data(self, bars: List[BarData]):
        """
        设置历史数据
        
        Args:
            bars: BarData 列表
        """
        # 更新数据管理器
        self._data_manager.clear()
        for bar in bars:
            self._data_manager.add_bar(bar)
        
        # 清除旧图表项
        self._clear_chart_items()
        
        # 创建新图表项
        self._create_chart_items()
        
        # 更新视图
        self._update_view()
    
    def _create_chart_items(self):
        """创建图表项"""
        # 创建K线图
        self._candle_item = CandleItem(self._data_manager)
        self._price_plot.addItem(self._candle_item)
        
        # 创建成交量图
        self._volume_item = BarItem(self._data_manager, field='volume')
        self._volume_plot.addItem(self._volume_item)
        
        # 创建十字光标
        self._cursor = ChartCursor(
            self._price_plot,
            self._data_manager,
            self._plots
        )
        self._cursor.sigCursorMoved.connect(self._on_cursor_moved)
    
    def _clear_chart_items(self):
        """清除图表项"""
        if self._candle_item:
            self._price_plot.removeItem(self._candle_item)
            self._candle_item = None
        
        if self._volume_item:
            self._volume_plot.removeItem(self._volume_item)
            self._volume_item = None
        
        if self._cursor:
            self._cursor = None
    
    def _update_view(self):
        """更新视图范围"""
        bar_count = self._data_manager.get_count()
        if bar_count == 0:
            return
        
        # 设置X轴范围（显示最近的100根K线）
        view_count = min(100, bar_count)
        self._price_plot.setXRange(bar_count - view_count, bar_count)
        
        # 设置Y轴范围
        y_min, y_max = self._data_manager.get_price_range(
            bar_count - view_count, bar_count
        )
        if y_min is not None and y_max is not None:
            padding = (y_max - y_min) * 0.1
            self._price_plot.setYRange(y_min - padding, y_max + padding)
    
    def _on_cursor_moved(self, x: int, y: float):
        """
        光标移动事件
        
        Args:
            x: X轴索引
            y: Y轴值
        """
        bar_data = self._data_manager.get_bar(x)
        if bar_data is None:
            return
        
        # 更新信息标签
        info_text = (
            f"时间: {bar_data.datetime.strftime('%Y-%m-%d %H:%M')}\n"
            f"开: {bar_data.open:.2f}  高: {bar_data.high:.2f}\n"
            f"低: {bar_data.low:.2f}  收: {bar_data.close:.2f}\n"
            f"量: {bar_data.volume:.0f}"
        )
        self._info_label.setText(info_text)
    
    def _on_clicked(self, event):
        """
        点击事件
        
        Args:
            event: 鼠标事件
        """
        pos = event.scenePos()
        mouse_point = self._price_plot.vb.mapSceneToView(pos)
        ix = int(mouse_point.x())
        
        if 0 <= ix < self._data_manager.get_count():
            self.sigBarClicked.emit(ix)
    
    # ==================== 标记管理 ====================
    
    def add_marker(
        self,
        marker_type: MarkerType,
        x: int,
        y: float,
        text: str = "",
        strategy_name: str = "",
    ) -> str:
        """
        添加标记
        
        Args:
            marker_type: 标记类型
            x: X轴索引
            y: Y轴值
            text: 显示文本
            strategy_name: 策略名称
            
        Returns:
            标记ID
        """
        from .markers.base_marker import MarkerStyle, MarkerPosition
        
        style = MarkerStyle()
        if text:
            style.show_text = True
        
        data = MarkerData(
            marker_type=marker_type,
            x=x,
            y=y,
            style=style,
            strategy_name=strategy_name if strategy_name else None,
            display_text=text if text else None,
        )
        
        marker = TradeMarker(data)
        marker_id = self._marker_manager.add_marker(marker)
        
        # 添加到图表
        self._price_plot.addItem(marker)
        
        # 连接信号
        marker.sigClicked.connect(self._on_marker_clicked)
        
        return marker_id
    
    def remove_marker(self, marker_id: str):
        """
        移除标记
        
        Args:
            marker_id: 标记ID
        """
        marker = self._marker_manager.get_marker(marker_id)
        if marker:
            self._price_plot.removeItem(marker)
            self._marker_manager.remove_marker(marker_id)
    
    def clear_markers(self):
        """清除所有标记"""
        for marker in self._marker_manager.get_all_markers():
            self._price_plot.removeItem(marker)
        self._marker_manager.clear_all()
    
    def _on_marker_clicked(self, marker):
        """
        标记点击事件
        
        Args:
            marker: 被点击的标记
        """
        self.sigMarkerClicked.emit(marker)
    
    # ==================== 叠加层管理 ====================
    
    def add_confidence_band(self, band: ConfidenceBand):
        """
        添加置信区间带
        
        Args:
            band: ConfidenceBand 对象
        """
        self._price_plot.addItem(band)
    
    def remove_confidence_band(self, band: ConfidenceBand):
        """
        移除置信区间带
        
        Args:
            band: ConfidenceBand 对象
        """
        self._price_plot.removeItem(band)
    
    # ==================== 工具方法 ====================
    
    def get_bar(self, ix: int) -> Optional[BarData]:
        """获取指定索引的Bar数据"""
        return self._data_manager.get_bar(ix)
    
    def get_bar_count(self) -> int:
        """获取Bar数量"""
        return self._data_manager.get_count()
    
    def scroll_to_end(self):
        """滚动到最新数据"""
        bar_count = self._data_manager.get_count()
        if bar_count > 0:
            view_count = 100
            self._price_plot.setXRange(
                max(0, bar_count - view_count), bar_count
            )
    
    def update_last_bar(self, bar: BarData):
        """
        更新最后一根K线
        
        Args:
            bar: 新的Bar数据
        """
        self._data_manager.update_bar(bar)
        if self._candle_item:
            self._candle_item.update_bar(bar)
        if self._volume_item:
            self._volume_item.update_bar(bar)
    
    def add_new_bar(self, bar: BarData):
        """
        添加新K线
        
        Args:
            bar: 新的Bar数据
        """
        self._data_manager.add_bar(bar)
        if self._candle_item:
            self._candle_item.update_history([])
        if self._volume_item:
            self._volume_item.update_history([])