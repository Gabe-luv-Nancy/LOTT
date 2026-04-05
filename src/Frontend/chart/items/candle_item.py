"""
蜡烛图元素模块

K线/蜡烛图元素，用于显示 OHLC 数据。
"""

from typing import Optional, Tuple
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QPicture, QPainter, QPen, QBrush, QColor

from .base_item import ChartItem
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from Frontend.core import BarData, DataManager


class CandleItem(ChartItem):
    """
    蜡烛图元素
    
    参考: vnpy.chart.item.CandleItem
    
    功能：
    - 显示 OHLC K线
    - 涨跌颜色区分
    - 自定义样式
    """
    
    def __init__(
        self, 
        data_manager: DataManager,
        bar_width: float = 0.3,
        up_color: Tuple[int, int, int] = (255, 0, 0),      # 上涨颜色（红）
        down_color: Tuple[int, int, int] = (0, 255, 0),    # 下跌颜色（绿）
    ):
        """
        初始化蜡烛图元素
        
        Args:
            data_manager: 数据管理器
            bar_width: K线宽度
            up_color: 上涨颜色 (R, G, B)
            down_color: 下跌颜色 (R, G, B)
        """
        super().__init__(data_manager)
        self._bar_width = bar_width
        self._up_color = up_color
        self._down_color = down_color
        
        # 边界缓存
        self._bounding_rect: Optional[QRectF] = None
    
    def _draw_bar_picture(self, ix: int, bar_data: BarData) -> QPicture:
        """
        绘制单根K线
        
        参考: vnpy.chart.item.CandleItem._draw_bar_picture()
        """
        picture = QPicture()
        painter = QPainter(picture)
        
        # 判断涨跌
        is_up = bar_data.close >= bar_data.open
        color = QColor(*self._up_color) if is_up else QColor(*self._down_color)
        
        # 设置画笔和画刷
        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(color) if is_up else Qt.NoBrush)
        
        # 绘制上下影线
        if bar_data.high > bar_data.low:
            # 上影线
            painter.drawLine(
                ix + 0.5, bar_data.high,
                ix + 0.5, max(bar_data.open, bar_data.close)
            )
            # 下影线
            painter.drawLine(
                ix + 0.5, min(bar_data.open, bar_data.close),
                ix + 0.5, bar_data.low
            )
        
        # 绘制实体
        body_top = max(bar_data.open, bar_data.close)
        body_bottom = min(bar_data.open, bar_data.close)
        body_height = body_top - body_bottom if body_top > body_bottom else 0.001
        
        painter.drawRect(
            ix + 0.5 - self._bar_width,
            body_bottom,
            self._bar_width * 2,
            body_height
        )
        
        painter.end()
        return picture
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        bar_count = self._data_manager.get_count()
        if bar_count == 0:
            return QRectF()
        
        y_min, y_max = self.get_y_range()
        if y_min is None or y_max is None:
            return QRectF()
        
        return QRectF(
            -0.5,
            y_min,
            bar_count + 0.5,
            y_max - y_min
        )
    
    def get_y_range(
        self, 
        min_ix: Optional[int] = None, 
        max_ix: Optional[int] = None
    ) -> Tuple[float, float]:
        """获取Y轴范围（基于 high/low）"""
        return self._data_manager.get_price_range(min_ix, max_ix)
    
    def get_info_text(self, ix: int) -> str:
        """
        获取信息文本
        
        格式:
        开: xxx  高: xxx
        低: xxx  收: xxx
        """
        bar_data = self._data_manager.get_bar(ix)
        if bar_data is None:
            return ""
        
        return (
            f"开: {bar_data.open:.2f}  高: {bar_data.high:.2f}\n"
            f"低: {bar_data.low:.2f}  收: {bar_data.close:.2f}"
        )
    
    # ==================== 样式设置 ====================
    
    def set_bar_width(self, width: float):
        """设置K线宽度"""
        self._bar_width = width
        self._bar_pictures.clear()
        self._to_update = True
        self.update()
    
    def set_up_color(self, color: Tuple[int, int, int]):
        """设置上涨颜色"""
        self._up_color = color
        self._bar_pictures.clear()
        self._to_update = True
        self.update()
    
    def set_down_color(self, color: Tuple[int, int, int]):
        """设置下跌颜色"""
        self._down_color = color
        self._bar_pictures.clear()
        self._to_update = True
        self.update()
    
    # ==================== 兼容性方法 ====================
    
    def get_bar_count(self) -> int:
        """获取Bar数量（兼容性方法）"""
        return self._data_manager.get_count()
