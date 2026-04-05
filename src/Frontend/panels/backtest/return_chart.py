"""
收益率图表模块

显示回测期间的累计收益率曲线。
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


class ReturnChart(pg.GraphicsLayoutWidget):
    """
    收益率图表
    
    功能：
    - 显示累计收益率曲线
    - 显示基准收益（可选）
    - 零线高亮
    - 最大回撤区域标注
    """
    
    sigCursorMoved = pyqtSignal(int, float)  # (index, return)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._returns: List[float] = []
        self._benchmark: List[float] = []
        self._curve_item: Optional[pg.PlotDataItem] = None
        self._benchmark_item: Optional[pg.PlotDataItem] = None
        
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
        self._return_color = QColor(255, 215, 0)    # 收益曲线颜色（金色）
        self._benchmark_color = QColor(128, 128, 128)  # 基准颜色（灰色）
        self._line_width = 1.5
    
    def load_returns(self, returns: List[float], benchmark: List[float] = None):
        """
        加载收益率数据
        
        Args:
            returns: 累计收益率列表
            benchmark: 基准收益率列表（可选）
        """
        self._returns = returns
        self._benchmark = benchmark or []
        self._update_chart()
    
    def _update_chart(self):
        """更新图表"""
        if not self._returns:
            return
        
        # 清除旧元素
        if self._curve_item:
            self._plot.removeItem(self._curve_item)
        if self._benchmark_item:
            self._plot.removeItem(self._benchmark_item)
        
        # 准备数据
        x = np.arange(len(self._returns))
        y = np.array(self._returns)
        
        # 创建收益曲线
        self._curve_item = self._plot.plot(
            x, y,
            pen=pg.mkPen(self._return_color, width=self._line_width),
            name='returns'
        )
        
        # 创建基准曲线
        if self._benchmark and len(self._benchmark) == len(self._returns):
            self._benchmark_item = self._plot.plot(
                x, np.array(self._benchmark),
                pen=pg.mkPen(self._benchmark_color, width=self._line_width, style=Qt.DashLine),
                name='benchmark'
            )
        
        # 自动调整Y轴范围
        if self._returns:
            min_val = min(self._returns)
            max_val = max(self._returns)
            if self._benchmark:
                min_val = min(min_val, min(self._benchmark))
                max_val = max(max_val, max(self._benchmark))
            
            padding = (max_val - min_val) * 0.1 if max_val != min_val else 0.1
            self._plot.setRange(yRange=(min_val - padding, max_val + padding))
    
    def set_colors(self, return_color: QColor, benchmark_color: QColor = None):
        """设置颜色"""
        self._return_color = return_color
        if benchmark_color:
            self._benchmark_color = benchmark_color
        self._update_chart()
    
    def get_return_at(self, index: int) -> Optional[float]:
        """获取指定索引的收益率"""
        if 0 <= index < len(self._returns):
            return self._returns[index]
        return None
    
    def get_max_drawdown(self) -> Tuple[float, int, int]:
        """
        计算最大回撤
        
        Returns:
            (最大回撤值, 起始索引, 结束索引)
        """
        if not self._returns:
            return (0.0, 0, 0)
        
        peak = self._returns[0]
        max_dd = 0.0
        start_ix = 0
        end_ix = 0
        temp_start = 0
        
        for i, ret in enumerate(self._returns):
            if ret > peak:
                peak = ret
                temp_start = i
            else:
                dd = (peak - ret) / peak if peak != 0 else 0
                if dd > max_dd:
                    max_dd = dd
                    start_ix = temp_start
                    end_ix = i
        
        return (max_dd, start_ix, end_ix)
    
    def clear_data(self):
        """清除数据"""
        self._returns.clear()
        self._benchmark.clear()
        if self._curve_item:
            self._plot.removeItem(self._curve_item)
            self._curve_item = None
        if self._benchmark_item:
            self._plot.removeItem(self._benchmark_item)
            self._benchmark_item = None