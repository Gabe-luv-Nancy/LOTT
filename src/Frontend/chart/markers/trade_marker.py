"""
交易标记模块

交易专用标记，提供预设样式和便捷创建方法。
"""

import math
from PyQt5.QtCore import QRectF, Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF

from .base_marker import BaseMarker, MarkerData, MarkerType, MarkerShape, MarkerStyle, MarkerPosition


class TradeMarker(BaseMarker):
    """
    交易标记
    
    功能：
    - 预设买卖样式
    - 支持止损/止盈标记
    - 支持信号标记
    """
    
    # 预设样式配置
    PRESET_STYLES = {
        MarkerType.BUY: MarkerStyle(
            shape=MarkerShape.TRIANGLE_UP,
            color=QColor(255, 0, 0),      # 红色
            position=MarkerPosition.BELOW_BAR,
        ),
        MarkerType.SELL: MarkerStyle(
            shape=MarkerShape.TRIANGLE_DOWN,
            color=QColor(0, 255, 0),      # 绿色
            position=MarkerPosition.ABOVE_BAR,
        ),
        MarkerType.STOP_LOSS: MarkerStyle(
            shape=MarkerShape.CROSS,
            color=QColor(255, 165, 0),    # 橙色
            position=MarkerPosition.ABOVE_BAR,
            show_text=True,
        ),
        MarkerType.TAKE_PROFIT: MarkerStyle(
            shape=MarkerShape.STAR,
            color=QColor(255, 215, 0),    # 金色
            position=MarkerPosition.ABOVE_BAR,
            show_text=True,
        ),
        MarkerType.SIGNAL_BUY: MarkerStyle(
            shape=MarkerShape.ARROW_UP,
            color=QColor(255, 100, 100),  # 浅红色
            position=MarkerPosition.BELOW_BAR,
        ),
        MarkerType.SIGNAL_SELL: MarkerStyle(
            shape=MarkerShape.ARROW_DOWN,
            color=QColor(100, 255, 100),  # 浅绿色
            position=MarkerPosition.ABOVE_BAR,
        ),
        MarkerType.PIVOT_HIGH: MarkerStyle(
            shape=MarkerShape.DIAMOND,
            color=QColor(255, 0, 255),    # 紫色
            position=MarkerPosition.ABOVE_BAR,
        ),
        MarkerType.PIVOT_LOW: MarkerStyle(
            shape=MarkerShape.DIAMOND,
            color=QColor(0, 255, 255),    # 青色
            position=MarkerPosition.BELOW_BAR,
        ),
    }
    
    def __init__(self, data: MarkerData, parent=None):
        # 应用预设样式
        if data.marker_type in self.PRESET_STYLES and data.style is None:
            data.style = self.PRESET_STYLES[data.marker_type]
        super().__init__(data, parent)
    
    def _draw_marker(self, painter: QPainter) -> None:
        """
        绘制交易标记
        
        支持的形状：
        - 三角形（上/下）
        - 圆形
        - 方形
        - 菱形
        - 五角星
        - 箭头
        - 叉号
        - 旗帜
        - 图钉
        """
        x = float(self._data.x)
        y = self._data.y
        size = self._style.size
        
        # 根据位置调整Y坐标
        if self._style.position == MarkerPosition.ABOVE_BAR:
            y += self._style.offset
        elif self._style.position == MarkerPosition.BELOW_BAR:
            y -= self._style.offset
        
        # 设置画笔和画刷
        painter.setPen(QPen(self._style.border_color, self._style.border_width))
        painter.setBrush(QBrush(self._style.color))
        
        shape = self._style.shape
        
        if shape == MarkerShape.TRIANGLE_UP:
            self._draw_triangle_up(painter, x, y, size)
        elif shape == MarkerShape.TRIANGLE_DOWN:
            self._draw_triangle_down(painter, x, y, size)
        elif shape == MarkerShape.CIRCLE:
            self._draw_circle(painter, x, y, size)
        elif shape == MarkerShape.SQUARE:
            self._draw_square(painter, x, y, size)
        elif shape == MarkerShape.DIAMOND:
            self._draw_diamond(painter, x, y, size)
        elif shape == MarkerShape.STAR:
            self._draw_star(painter, x, y, size)
        elif shape == MarkerShape.ARROW_UP:
            self._draw_arrow_up(painter, x, y, size)
        elif shape == MarkerShape.ARROW_DOWN:
            self._draw_arrow_down(painter, x, y, size)
        elif shape == MarkerShape.CROSS:
            self._draw_cross(painter, x, y, size)
        elif shape == MarkerShape.FLAG:
            self._draw_flag(painter, x, y, size)
        elif shape == MarkerShape.PIN:
            self._draw_pin(painter, x, y, size)
        
        # 绘制文本
        if self._style.show_text and (self._style.text or self._data.display_text):
            self._draw_text(painter, x, y, size)
    
    def _draw_triangle_up(self, painter: QPainter, x: float, y: float, size: float):
        """绘制向上三角形"""
        triangle = QPolygonF([
            QPointF(x, y - size),
            QPointF(x - size * 0.7, y + size * 0.5),
            QPointF(x + size * 0.7, y + size * 0.5)
        ])
        painter.drawPolygon(triangle)
    
    def _draw_triangle_down(self, painter: QPainter, x: float, y: float, size: float):
        """绘制向下三角形"""
        triangle = QPolygonF([
            QPointF(x, y + size),
            QPointF(x - size * 0.7, y - size * 0.5),
            QPointF(x + size * 0.7, y - size * 0.5)
        ])
        painter.drawPolygon(triangle)
    
    def _draw_circle(self, painter: QPainter, x: float, y: float, size: float):
        """绘制圆形"""
        painter.drawEllipse(QPointF(x, y), size * 0.6, size * 0.6)
    
    def _draw_square(self, painter: QPainter, x: float, y: float, size: float):
        """绘制方形"""
        painter.drawRect(
            int(x - size * 0.5),
            int(y - size * 0.5),
            int(size),
            int(size)
        )
    
    def _draw_diamond(self, painter: QPainter, x: float, y: float, size: float):
        """绘制菱形"""
        diamond = QPolygonF([
            QPointF(x, y - size),
            QPointF(x + size * 0.7, y),
            QPointF(x, y + size),
            QPointF(x - size * 0.7, y)
        ])
        painter.drawPolygon(diamond)
    
    def _draw_star(self, painter: QPainter, x: float, y: float, size: float):
        """绘制五角星"""
        points = []
        for i in range(5):
            # 外顶点
            angle = math.pi / 2 + i * 2 * math.pi / 5
            px = x + size * math.cos(angle)
            py = y - size * math.sin(angle)
            points.append(QPointF(px, py))
            
            # 内顶点
            angle += math.pi / 5
            px = x + size * 0.4 * math.cos(angle)
            py = y - size * 0.4 * math.sin(angle)
            points.append(QPointF(px, py))
        
        painter.drawPolygon(QPolygonF(points))
    
    def _draw_arrow_up(self, painter: QPainter, x: float, y: float, size: float):
        """绘制向上箭头"""
        arrow = QPolygonF([
            QPointF(x, y - size),
            QPointF(x + size * 0.5, y),
            QPointF(x + size * 0.25, y),
            QPointF(x + size * 0.25, y + size),
            QPointF(x - size * 0.25, y + size),
            QPointF(x - size * 0.25, y),
            QPointF(x - size * 0.5, y)
        ])
        painter.drawPolygon(arrow)
    
    def _draw_arrow_down(self, painter: QPainter, x: float, y: float, size: float):
        """绘制向下箭头"""
        arrow = QPolygonF([
            QPointF(x, y + size),
            QPointF(x + size * 0.5, y),
            QPointF(x + size * 0.25, y),
            QPointF(x + size * 0.25, y - size),
            QPointF(x - size * 0.25, y - size),
            QPointF(x - size * 0.25, y),
            QPointF(x - size * 0.5, y)
        ])
        painter.drawPolygon(arrow)
    
    def _draw_cross(self, painter: QPainter, x: float, y: float, size: float):
        """绘制叉号"""
        painter.drawLine(
            int(x - size * 0.7), int(y - size * 0.7),
            int(x + size * 0.7), int(y + size * 0.7)
        )
        painter.drawLine(
            int(x + size * 0.7), int(y - size * 0.7),
            int(x - size * 0.7), int(y + size * 0.7)
        )
    
    def _draw_flag(self, painter: QPainter, x: float, y: float, size: float):
        """绘制旗帜"""
        # 旗杆
        painter.drawLine(int(x), int(y - size), int(x), int(y + size))
        # 旗帜
        flag = QPolygonF([
            QPointF(x, y - size),
            QPointF(x + size, y - size * 0.6),
            QPointF(x, y - size * 0.2)
        ])
        painter.drawPolygon(flag)
    
    def _draw_pin(self, painter: QPainter, x: float, y: float, size: float):
        """绘制图钉"""
        # 圆头
        painter.drawEllipse(QPointF(x, y - size * 0.5), size * 0.4, size * 0.4)
        # 尖端
        painter.drawLine(int(x), int(y), int(x), int(y + size))
    
    def _draw_text(self, painter: QPainter, x: float, y: float, size: float):
        """绘制文本"""
        text = self._style.text or self._data.display_text or ""
        if not text:
            return
        
        painter.setPen(QPen(self._style.text_color))
        painter.setFont(self._style.text_font)
        
        offset_x, offset_y = self._style.text_offset
        painter.drawText(
            int(x + offset_x),
            int(y + offset_y),
            text
        )
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        size = self._style.size
        x = float(self._data.x)
        y = self._data.y
        
        # 考虑位置偏移
        if self._style.position == MarkerPosition.ABOVE_BAR:
            y += self._style.offset
        elif self._style.position == MarkerPosition.BELOW_BAR:
            y -= self._style.offset
        
        return QRectF(
            x - size,
            y - size,
            size * 2,
            size * 2
        )