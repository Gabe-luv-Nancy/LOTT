"""
多层折线图组件

支持多 Y 轴的折线图
"""

from typing import Dict, Optional
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg

from .types import VariableConfig


class MultiLineChartWidget(QWidget):
    """
    多层折线图组件
    
    功能：
    - 多条折线叠加显示
    - 多 Y 轴支持
    - 时间轴联动
    - 置信区间显示
    
    信号：
    - sigRangeChanged: 范围变化
    - sigCursorMoved: 光标移动
    """
    
    sigRangeChanged = pyqtSignal(tuple)
    sigCursorMoved = pyqtSignal(int, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lines: Dict[str, pg.PlotDataItem] = {}
        self._configs: Dict[str, VariableConfig] = {}
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建图形布局
        self._graphics_widget = pg.GraphicsLayoutWidget()
        self._graphics_widget.setBackground('#1a1a2e')
        layout.addWidget(self._graphics_widget)
        
        # 主绘图区域
        self._main_plot = self._graphics_widget.addPlot()
        self._main_plot.showGrid(x=True, y=True, alpha=0.3)
        self._main_plot.setMenuEnabled(False)
        
        # 设置Y轴
        self._main_plot.showAxis('left')
        self._main_plot.showAxis('right')
    
    def add_line(self, col_hash: str, config: VariableConfig):
        """
        添加折线
        
        Args:
            col_hash: 列哈希值
            config: 变量配置
        """
        if col_hash in self._lines:
            return
        
        # 创建画笔
        pen = QPen(config.color)
        pen.setWidthF(config.line_width)
        
        # 设置线型
        if config.line_style == 1:
            pen.setStyle(Qt.PenStyle.DashLine)
        elif config.line_style == 2:
            pen.setStyle(Qt.PenStyle.DotLine)
        elif config.line_style == 3:
            pen.setStyle(Qt.PenStyle.DashDotLine)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)
        
        # 创建折线
        line = self._main_plot.plot(pen=pen)
        self._lines[col_hash] = line
        self._configs[col_hash] = config
    
    def remove_line(self, col_hash: str):
        """移除折线"""
        if col_hash in self._lines:
            self._main_plot.removeItem(self._lines[col_hash])
            del self._lines[col_hash]
            del self._configs[col_hash]
    
    def update_line_config(self, col_hash: str, config: VariableConfig):
        """更新折线配置"""
        if col_hash not in self._lines:
            return
        
        self._configs[col_hash] = config
        
        # 更新画笔
        pen = QPen(config.color)
        pen.setWidthF(config.line_width)
        
        if config.line_style == 1:
            pen.setStyle(Qt.PenStyle.DashLine)
        elif config.line_style == 2:
            pen.setStyle(Qt.PenStyle.DotLine)
        elif config.line_style == 3:
            pen.setStyle(Qt.PenStyle.DashDotLine)
        else:
            pen.setStyle(Qt.PenStyle.SolidLine)
        
        self._lines[col_hash].setPen(pen)
    
    def set_line_visible(self, col_hash: str, visible: bool):
        """设置折线可见性"""
        if col_hash in self._lines:
            self._lines[col_hash].setVisible(visible)
    
    def set_data(self, col_hash: str, data: pd.Series):
        """设置折线数据"""
        if col_hash not in self._lines:
            return
        
        config = self._configs.get(col_hash)
        if config:
            # 应用滞后
            if config.lagging != 0:
                data = data.shift(config.lagging)
        
        x = list(range(len(data)))
        y = data.values.tolist()
        
        self._lines[col_hash].setData(x, y)
    
    def add_confidence_band(
        self,
        col_hash: str,
        lower: pd.Series,
        upper: pd.Series,
        color: QColor = None
    ):
        """添加置信区间"""
        if color is None:
            color = QColor(100, 100, 100, 50)
        
        # 创建填充区域
        x = list(range(len(lower)))
        
        fill = pg.FillBetweenItem(
            pg.PlotDataItem(x, lower.values),
            pg.PlotDataItem(x, upper.values),
            brush=color
        )
        self._main_plot.addItem(fill)
    
    def remove_confidence_band(self, col_hash: str):
        """移除置信区间"""
        # TODO: 实现移除置信区间
        pass
    
    def clear_all(self):
        """清除所有折线"""
        for line in list(self._lines.values()):
            self._main_plot.removeItem(line)
        self._lines.clear()
        self._configs.clear()
    
    def link_x_axis(self, other_chart):
        """关联 X 轴"""
        if hasattr(other_chart, '_main_plot'):
            self._main_plot.setXLink(other_chart._main_plot)