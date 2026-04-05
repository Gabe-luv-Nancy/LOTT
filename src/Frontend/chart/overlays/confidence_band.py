"""
置信区间带模块

显示策略信号的置信区间和不确定性范围。
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from PyQt5.QtCore import QRectF, QPointF, Qt
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QPainterPath
import pyqtgraph as pg


@dataclass
class BandConfig:
    """置信区间带配置"""
    # 填充颜色
    fill_color: QColor = None  # type: ignore
    fill_opacity: float = 0.3
    
    # 边界线样式
    upper_line_color: QColor = None  # type: ignore
    lower_line_color: QColor = None  # type: ignore
    line_width: float = 1.0
    line_style: int = 1  # Qt.DashLine
    
    # 中线样式
    show_mid_line: bool = True
    mid_line_color: QColor = None  # type: ignore
    mid_line_width: float = 1.0
    
    def __post_init__(self):
        if self.fill_color is None:
            self.fill_color = QColor(100, 150, 255)
        if self.upper_line_color is None:
            self.upper_line_color = QColor(100, 150, 255)
        if self.lower_line_color is None:
            self.lower_line_color = QColor(100, 150, 255)
        if self.mid_line_color is None:
            self.mid_line_color = QColor(255, 255, 255, 150)


@dataclass
class BandData:
    """单点数据"""
    x: int
    upper: float
    lower: float
    mid: Optional[float] = None


class ConfidenceBand(pg.GraphicsObject):
    """
    置信区间带
    
    功能：
    - 显示预测区间
    - 显示策略置信范围
    - 支持多条带叠加
    """
    
    def __init__(self, config: Optional[BandConfig] = None):
        super().__init__()
        
        self._config = config or BandConfig()
        self._data: List[BandData] = []
        self._path: Optional[QPainterPath] = None
    
    def set_data(self, data: List[BandData]):
        """
        设置数据
        
        Args:
            data: BandData 列表
        """
        self._data = data
        self._build_path()
        self.update()
    
    def _build_path(self):
        """构建绘制路径"""
        if not self._data:
            self._path = None
            return
        
        self._path = QPainterPath()
        
        # 上边界点
        upper_points = []
        lower_points = []
        
        for d in self._data:
            upper_points.append(QPointF(d.x + 0.5, d.upper))
            lower_points.append(QPointF(d.x + 0.5, d.lower))
        
        if len(upper_points) < 2:
            self._path = None
            return
        
        # 构建填充区域
        self._path.moveTo(upper_points[0])
        for p in upper_points[1:]:
            self._path.lineTo(p)
        
        # 反向添加下边界
        for p in reversed(lower_points):
            self._path.lineTo(p)
        
        self._path.closeSubpath()
    
    def paint(self, painter: QPainter, option, widget=None):
        """绘制置信区间带"""
        if not self._path or not self._data:
            return
        
        painter.save()
        
        # 绘制填充区域
        fill_color = QColor(self._config.fill_color)
        fill_color.setAlphaF(self._config.fill_opacity)
        painter.fillPath(self._path, QBrush(fill_color))
        
        # 绘制上边界线
        pen = QPen(self._config.upper_line_color, self._config.line_width)
        pen.setStyle(Qt.PenStyle(self._config.line_style))
        painter.setPen(pen)
        
        upper_points = [QPointF(d.x + 0.5, d.upper) for d in self._data]
        for i in range(1, len(upper_points)):
            painter.drawLine(upper_points[i-1], upper_points[i])
        
        # 绘制下边界线
        pen.setColor(self._config.lower_line_color)
        painter.setPen(pen)
        
        lower_points = [QPointF(d.x + 0.5, d.lower) for d in self._data]
        for i in range(1, len(lower_points)):
            painter.drawLine(lower_points[i-1], lower_points[i])
        
        # 绘制中线
        if self._config.show_mid_line:
            mid_points = []
            for d in self._data:
                if d.mid is not None:
                    mid_points.append(QPointF(d.x + 0.5, d.mid))
            
            if len(mid_points) >= 2:
                pen = QPen(self._config.mid_line_color, self._config.mid_line_width)
                pen.setStyle(Qt.PenStyle.SolidLine)
                painter.setPen(pen)
                
                for i in range(1, len(mid_points)):
                    painter.drawLine(mid_points[i-1], mid_points[i])
        
        painter.restore()
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        if not self._data:
            return QRectF()
        
        x_min = min(d.x for d in self._data)
        x_max = max(d.x for d in self._data)
        y_min = min(d.lower for d in self._data)
        y_max = max(d.upper for d in self._data)
        
        return QRectF(x_min, y_min, x_max - x_min, y_max - y_min)
    
    def get_y_range(self) -> Tuple[float, float]:
        """获取Y轴范围"""
        if not self._data:
            return (0.0, 1.0)
        
        y_min = min(d.lower for d in self._data)
        y_max = max(d.upper for d in self._data)
        
        return (y_min, y_max)
    
    def clear(self):
        """清除数据"""
        self._data = []
        self._path = None
        self.update()