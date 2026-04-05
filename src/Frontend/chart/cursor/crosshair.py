"""
十字光标模块

提供十字线显示、位置信息显示和多图表联动功能。
"""

from typing import Dict, Optional, Tuple
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor
import pyqtgraph as pg

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from Frontend.core import DataManager


class ChartCursor(pg.GraphicsObject):
    """
    十字光标
    
    参考: vnpy.chart.cursor.ChartCursor
    
    功能：
    - 十字线显示
    - 位置信息显示
    - 多图表联动
    """
    
    sigCursorMoved = pyqtSignal(int, float)  # (x_index, y_value)
    
    def __init__(
        self,
        plot_item: pg.PlotItem,
        data_manager: DataManager,
        plots: Dict[str, pg.PlotItem] = None,
    ):
        """
        初始化十字光标
        
        Args:
            plot_item: 主绘图区域
            data_manager: 数据管理器
            plots: 所有绘图区域字典
        """
        super().__init__()
        
        self._plot_item = plot_item
        self._data_manager = data_manager
        self._plots = plots or {}
        
        # 光标状态
        self._x = 0
        self._y = 0.0
        self._visible = True
        
        # 垂直线
        self._v_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(color=QColor(255, 255, 255, 100), width=1, style=Qt.DashLine)
        )
        plot_item.addItem(self._v_line)
        
        # 水平线（每个绘图区域一个）
        self._h_lines: Dict[str, pg.InfiniteLine] = {}
        for name, plot in self._plots.items():
            h_line = pg.InfiniteLine(
                angle=0,
                movable=False,
                pen=pg.mkPen(color=QColor(255, 255, 255, 100), width=1, style=Qt.DashLine)
            )
            plot.addItem(h_line)
            self._h_lines[name] = h_line
        
        # 主绘图区域的水平线
        self._main_h_line = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=pg.mkPen(color=QColor(255, 255, 255, 100), width=1, style=Qt.DashLine)
        )
        plot_item.addItem(self._main_h_line)
        
        # 连接信号
        self._plot_item.scene().sigMouseMoved.connect(self._on_mouse_moved)
    
    def paint(self, painter: QPainter, option, widget):
        """绘制（由InfiniteLine处理）"""
        pass
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        return QRectF()
    
    def _on_mouse_moved(self, pos):
        """
        鼠标移动事件处理
        
        Args:
            pos: 鼠标位置（场景坐标）
        """
        if not self._visible:
            return
        
        # 转换为绘图坐标
        mouse_point = self._plot_item.vb.mapSceneToView(pos)
        x = int(mouse_point.x())
        y = mouse_point.y()
        
        # 限制在数据范围内
        bar_count = self._data_manager.get_count()
        if 0 <= x < bar_count:
            self.update_position(x, y)
    
    def update_position(self, x: int, y: float):
        """
        更新光标位置
        
        Args:
            x: X轴索引
            y: Y轴值
        """
        self._x = x
        self._y = y
        
        # 更新垂直线
        self._v_line.setPos(x + 0.5)
        
        # 更新水平线
        self._main_h_line.setPos(y)
        for h_line in self._h_lines.values():
            h_line.setPos(y)
        
        # 发送信号
        self.sigCursorMoved.emit(x, y)
    
    def set_visible(self, visible: bool):
        """
        设置可见性
        
        Args:
            visible: 是否可见
        """
        self._visible = visible
        self._v_line.setVisible(visible)
        self._main_h_line.setVisible(visible)
        for h_line in self._h_lines.values():
            h_line.setVisible(visible)
    
    def get_current_index(self) -> int:
        """获取当前索引"""
        return self._x
    
    def get_current_value(self) -> float:
        """获取当前值"""
        return self._y
    
    def add_plot(self, name: str, plot_item: pg.PlotItem):
        """
        添加绘图区域
        
        Args:
            name: 绘图区域名称
            plot_item: 绘图区域
        """
        if name in self._plots:
            return
        
        self._plots[name] = plot_item
        
        # 添加水平线
        h_line = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=pg.mkPen(color=QColor(255, 255, 255, 100), width=1, style=Qt.DashLine)
        )
        plot_item.addItem(h_line)
        self._h_lines[name] = h_line
    
    def remove_plot(self, name: str):
        """
        移除绘图区域
        
        Args:
            name: 绘图区域名称
        """
        if name not in self._plots:
            return
        
        # 移除水平线
        if name in self._h_lines:
            h_line = self._h_lines.pop(name)
            self._plots[name].removeItem(h_line)
        
        del self._plots[name]