"""
柱状图元素模块

用于显示成交量等柱状数据。
"""

from typing import Optional, Tuple, List
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QPicture, QPainter, QPen, QBrush, QColor

from .base_item import ChartItem
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from Frontend.core import BarData, DataManager


class BarItem(ChartItem):
    """
    柱状图元素
    
    功能：
    - 显示柱状数据（如成交量）
    - 支持涨跌颜色区分
    - 支持自定义样式
    """
    
    def __init__(
        self,
        data_manager: DataManager,
        field: str = 'volume',              # 数据字段
        bar_width: float = 0.4,
        up_color: Tuple[int, int, int] = (255, 0, 0),      # 上涨颜色
        down_color: Tuple[int, int, int] = (0, 255, 0),    # 下跌颜色
    ):
        """
        初始化柱状图元素
        
        Args:
            data_manager: 数据管理器
            field: 数据字段（'volume', 'turnover', 'open_interest'）
            bar_width: 柱子宽度
            up_color: 上涨颜色 (R, G, B)
            down_color: 下跌颜色 (R, G, B)
        """
        super().__init__(data_manager)
        self._field = field
        self._bar_width = bar_width
        self._up_color = up_color
        self._down_color = down_color
        
        # 数据缓存
        self._y_max: float = 1
    
    def _draw_bar_picture(self, ix: int, bar_data: BarData) -> QPicture:
        """
        绘制单根柱子
        """
        picture = QPicture()
        painter = QPainter(picture)
        
        value = getattr(bar_data, self._field, None)
        if value is None or value <= 0:
            painter.end()
            return picture
        
        # 判断涨跌
        is_up = bar_data.close >= bar_data.open
        color = QColor(*self._up_color) if is_up else QColor(*self._down_color)
        
        # 设置画笔和画刷
        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(color))
        
        # 绘制柱子
        painter.drawRect(
            int(ix + 0.5 - self._bar_width),
            0,
            int(self._bar_width * 2),
            int(value)
        )
        
        painter.end()
        return picture
    
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        bar_count = self._data_manager.get_count()
        if bar_count == 0:
            return QRectF()
        
        _, y_max = self.get_y_range()
        
        return QRectF(
            -0.5,
            0,
            bar_count + 0.5,
            y_max * 1.1  # 留出10%的顶部空间
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
        
        y_max = 0
        
        for ix in range(start_ix, end_ix):
            bar_data = self._data_manager.get_bar(ix)
            if bar_data:
                value = getattr(bar_data, self._field, None)
                if value is not None:
                    y_max = max(y_max, value)
        
        if y_max == 0:
            return (0.0, 1.0)
        
        self._y_max = y_max
        return (0.0, y_max)
    
    def get_info_text(self, ix: int) -> str:
        """获取信息文本"""
        bar_data = self._data_manager.get_bar(ix)
        if bar_data is None:
            return ""
        
        value = getattr(bar_data, self._field, None)
        if value is None:
            return ""
        
        # 格式化显示
        if value >= 1e8:
            return f"{self._field}: {value/1e8:.2f}亿"
        elif value >= 1e4:
            return f"{self._field}: {value/1e4:.2f}万"
        else:
            return f"{self._field}: {value:.0f}"
    
    # ==================== 样式设置 ====================
    
    def set_bar_width(self, width: float):
        """设置柱子宽度"""
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
    
    def set_field(self, field: str):
        """设置数据字段"""
        self._field = field
        self._bar_pictures.clear()
        self._to_update = True
        self.update()