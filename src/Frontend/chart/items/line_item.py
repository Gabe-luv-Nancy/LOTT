"""
折线图元素模块

用于显示价格、指标等连续数据。
"""

from typing import Optional, Tuple, List
from PyQt5.QtCore import QRectF, Qt, QPointF
from PyQt5.QtGui import QPicture, QPainter, QPen, QColor, QPolygonF

from .base_item import ChartItem
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from Frontend.core import BarData, DataManager


class LineItem(ChartItem):
    """
    折线图元素
    
    功能：
    - 显示连续折线
    - 支持多种线型（实线、虚线等）
    - 支持自定义颜色和宽度
    """
    
    def __init__(
        self,
        data_manager: DataManager,
        field: str = 'close',              # 数据字段
        color: Tuple[int, int, int] = (255, 255, 255),
        width: float = 1.0,
        style: Qt.PenStyle = Qt.SolidLine,
    ):
        """
        初始化折线元素
        
        Args:
            data_manager: 数据管理器
            field: 数据字段（'close', 'open', 'high', 'low'）
            color: 线条颜色 (R, G, B)
            width: 线条宽度
            style: 线条样式
        """
        super().__init__(data_manager)
        self._field = field
        self._color = color
        self._width = width
        self._style = style
        
        # 数据缓存
        self._values: List[float] = []
        self._y_min: float = 0
        self._y_max: float = 1
    
    def _draw_bar_picture(self, ix: int, bar_data: BarData) -> QPicture:
        """
        绘制单点（折线需要连续绘制，这里返回空图片）
        """
        picture = QPicture()
        # 折线图不使用单点绘制
        return picture
    
    def _draw_item_picture(self, min_ix: int, max_ix: int):
        """
        绘制折线（重写父类方法）
        """
        self._item_picture = QPicture()
        painter = QPainter(self._item_picture)
        
        bar_count = self._data_manager.get_count()
        if bar_count == 0:
            painter.end()
            return
        
        # 收集数据点
        points = []
        self._values = []
        self._y_min = float('inf')
        self._y_max = float('-inf')
        
        for ix in range(bar_count):
            bar_data = self._data_manager.get_bar(ix)
            if bar_data:
                value = getattr(bar_data, self._field, None)
                if value is not None:
                    points.append(QPointF(ix + 0.5, value))
                    self._values.append(value)
                    self._y_min = min(self._y_min, value)
                    self._y_max = max(self._y_max, value)
        
        if len(points) < 2:
            painter.end()
            return
        
        # 设置画笔
        pen = QPen(QColor(*self._color), self._width, self._style)
        painter.setPen(pen)
        
        # 绘制折线
        for i in range(1, len(points)):
            painter.drawLine(points[i-1], points[i])
        
        painter.end()
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        bar_count = self._data_manager.get_count()
        if bar_count == 0:
            return QRectF()
        
        if self._y_min == float('inf') or self._y_max == float('-inf'):
            return QRectF()
        
        padding = (self._y_max - self._y_min) * 0.1 if self._y_max > self._y_min else 1
        
        return QRectF(
            -0.5,
            self._y_min - padding,
            bar_count + 0.5,
            self._y_max - self._y_min + padding * 2
        )
    
    def get_y_range(
        self, 
        min_ix: Optional[int] = None, 
        max_ix: Optional[int] = None
    ) -> Tuple[float, float]:
        """获取Y轴范围"""
        bar_count = self._data_manager.get_count()
        if bar_count == 0:
            return (0.0, 1.0)
        
        start_ix = max(0, min_ix) if min_ix is not None else 0
        end_ix = min(bar_count, max_ix) if max_ix is not None else bar_count
        
        y_min = float('inf')
        y_max = float('-inf')
        
        for ix in range(start_ix, end_ix):
            bar_data = self._data_manager.get_bar(ix)
            if bar_data:
                value = getattr(bar_data, self._field, None)
                if value is not None:
                    y_min = min(y_min, value)
                    y_max = max(y_max, value)
        
        if y_min == float('inf') or y_max == float('-inf'):
            return (0.0, 1.0)
        
        return (y_min, y_max)
    
    def get_info_text(self, ix: int) -> str:
        """获取信息文本"""
        bar_data = self._data_manager.get_bar(ix)
        if bar_data is None:
            return ""
        
        value = getattr(bar_data, self._field, None)
        if value is None:
            return ""
        
        return f"{self._field}: {value:.2f}"
    
    # ==================== 样式设置 ====================
    
    def set_color(self, color: Tuple[int, int, int]):
        """设置颜色"""
        self._color = color
        self._to_update = True
        self.update()
    
    def set_width(self, width: float):
        """设置线宽"""
        self._width = width
        self._to_update = True
        self.update()
    
    def set_style(self, style: Qt.PenStyle):
        """设置线型"""
        self._style = style
        self._to_update = True
        self.update()
    
    def set_field(self, field: str):
        """设置数据字段"""
        self._field = field
        self._bar_pictures.clear()
        self._to_update = True
        self.update()