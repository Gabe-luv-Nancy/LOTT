"""
仓位图表模块

显示回测期间的账户仓位变化。
"""

from typing import List, Optional, Tuple
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
import pyqtgraph as pg
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from Frontend.core import DataManager, BarData


class PositionChart(pg.GraphicsLayoutWidget):
    """
    仓位图表
    
    功能：
    - 显示仓位变化（柱状图）
    - 多头仓位显示为正（绿色/红色）
    - 空头仓位显示为负（红色/绿色）
    - 零线高亮
    """
    
    sigCursorMoved = pyqtSignal(int, float)  # (index, position)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._positions: List[float] = []
        self._bar_item: Optional[pg.BarGraphItem] = None
        
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
        self._plot.setMaximumHeight(120)
        
        # 配置视图
        self._view = self._plot.getViewBox()
        self._view.setMouseEnabled(x=True, y=False)
        
        # 零线
        self._zero_line = pg.InfiniteLine(pos=0, angle=0, pen=pg.mkPen('w', width=1, style=Qt.DashLine))
        self._plot.addItem(self._zero_line)
        
        # 样式
        self._long_color = QColor(255, 75, 75)   # 多头颜色
        self._short_color = QColor(0, 255, 255)  # 空头颜色
    
    def load_positions(self, positions: List[float]):
        """
        加载仓位数据
        
        Args:
            positions: 仓位列表，正数为多头，负数为空头
        """
        self._positions = positions
        self._update_chart()
    
    def _update_chart(self):
        """更新图表"""
        if not self._positions:
            return
        
        # 移除旧元素
        if self._bar_item:
            self._plot.removeItem(self._bar_item)
        
        # 准备数据
        x = np.arange(len(self._positions))
        heights = np.array(self._positions)
        
        # 分离多头和空头
        long_mask = heights >= 0
        short_mask = heights < 0
        
        # 创建柱状图
        # 多头柱
        if np.any(long_mask):
            long_bars = pg.BarGraphItem(
                x=x[long_mask],
                height=heights[long_mask],
                width=0.8,
                brush=self._long_color
            )
            self._plot.addItem(long_bars)
        
        # 空头柱
        if np.any(short_mask):
            short_bars = pg.BarGraphItem(
                x=x[short_mask],
                height=heights[short_mask],
                width=0.8,
                brush=self._short_color
            )
            self._plot.addItem(short_bars)
        
        # 自动调整Y轴范围
        if self._positions:
            max_pos = max(abs(min(self._positions)), abs(max(self._positions)))
            if max_pos > 0:
                self._plot.setRange(yRange=(-max_pos * 1.1, max_pos * 1.1))
    
    def set_colors(self, long_color: QColor, short_color: QColor):
        """设置颜色"""
        self._long_color = long_color
        self._short_color = short_color
        self._update_chart()
    
    def get_position_at(self, index: int) -> Optional[float]:
        """获取指定索引的仓位"""
        if 0 <= index < len(self._positions):
            return self._positions[index]
        return None
    
    def clear_data(self):
        """清除数据"""
        self._positions.clear()
        if self._bar_item:
            self._plot.removeItem(self._bar_item)
            self._bar_item = None