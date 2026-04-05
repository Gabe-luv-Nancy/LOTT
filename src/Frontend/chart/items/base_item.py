"""
图表元素基类模块

所有图表元素的抽象基类，定义统一接口和绘制优化机制。
"""

from typing import Dict, List, Optional, Tuple
from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QPainter, QPicture
import pyqtgraph as pg

# 定义abstractmethod装饰器（简化版本，不使用ABC）
def abstractmethod(func):
    """标记为抽象方法的装饰器"""
    return func

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from Frontend.core import BarData, DataManager


class ChartItem(pg.GraphicsObject):
    """
    图表元素基类
    
    参考: vnpy.chart.base.ChartItem
    
    使用 QPicture 缓存绘制结果，只重绘可见区域，优化性能。
    """
    
    def __init__(self, data_manager: DataManager):
        """
        初始化图表元素
        
        Args:
            data_manager: 数据管理器实例
        """
        super().__init__()
        
        self._data_manager = data_manager
        
        # 绘制缓存：每个Bar的图片缓存
        self._bar_pictures: Dict[int, Optional[QPicture]] = {}
        
        # 整体图片缓存
        self._item_picture: Optional[QPicture] = None
        
        # 边界区域
        self._rect_area: Optional[Tuple[float, float]] = None
        
        # 启用优化：只重绘可见部分
        self.setFlag(self.GraphicsItemFlag.ItemUsesExtendedStyleOption)
        self._to_update = False
    
    # ==================== 抽象方法（子类必须实现） ====================
    
    @abstractmethod
    def _draw_bar_picture(self, ix: int, bar_data: BarData) -> QPicture:
        """
        绘制单个数据点的图片
        
        Args:
            ix: 数据索引
            bar_data: Bar 数据
            
        Returns:
            QPicture 对象
        """
        pass
    
    @abstractmethod
    def boundingRect(self) -> QRectF:
        """
        返回边界矩形
        
        Returns:
            边界矩形
        """
        pass
    
    @abstractmethod
    def get_y_range(
        self, 
        min_ix: Optional[int] = None, 
        max_ix: Optional[int] = None
    ) -> Tuple[float, float]:
        """
        获取Y轴范围
        
        Args:
            min_ix: 起始索引
            max_ix: 结束索引
            
        Returns:
            (y_min, y_max)
        """
        pass
    
    @abstractmethod
    def get_info_text(self, ix: int) -> str:
        """
        获取光标位置的信息文本
        
        Args:
            ix: 数据索引
            
        Returns:
            信息文本
        """
        pass
    
    # ==================== 绘制方法 ====================
    
    def paint(self, painter: QPainter, option, widget=None):
        """
        绘制方法
        
        使用 QPicture 缓存，只绘制可见区域。
        
        参考: vnpy.chart.base.ChartItem.paint()
        """
        # 获取可见区域
        rect = option.exposedRect
        min_ix = int(rect.left())
        max_ix = int(rect.right()) + 1
        
        # 限制范围
        bar_count = self._data_manager.get_count()
        min_ix = max(0, min_ix)
        max_ix = min(bar_count, max_ix)
        
        # 创建或更新整体图片
        if self._to_update or self._item_picture is None:
            self._draw_item_picture(min_ix, max_ix)
            self._to_update = False
        
        # 绘制缓存的图片
        if self._item_picture:
            painter.drawPicture(0, 0, self._item_picture)
    
    def _draw_item_picture(self, min_ix: int, max_ix: int):
        """
        绘制指定范围的图片
        
        Args:
            min_ix: 起始索引
            max_ix: 结束索引
        """
        self._item_picture = QPicture()
        painter = QPainter(self._item_picture)
        
        for ix in range(min_ix, max_ix):
            # 检查缓存
            if ix not in self._bar_pictures:
                bar_data = self._data_manager.get_bar(ix)
                if bar_data:
                    picture = self._draw_bar_picture(ix, bar_data)
                    self._bar_pictures[ix] = picture
            
            # 绘制缓存的图片
            picture = self._bar_pictures.get(ix)
            if picture:
                painter.drawPicture(0, 0, picture)
        
        painter.end()
    
    # ==================== 数据更新 ====================
    
    def update_history(self, history: List[BarData]):
        """
        更新历史数据
        
        Args:
            history: BarData 列表
        """
        self._bar_pictures.clear()
        self._item_picture = None
        self._to_update = True
        self.update()
    
    def update_bar(self, bar_data: BarData):
        """
        更新单个数据点
        
        Args:
            bar_data: Bar 数据
        """
        ix = self._data_manager.get_index(bar_data.datetime)
        if ix is not None:
            # 清除该点的缓存
            self._bar_pictures.pop(ix, None)
            self._to_update = True
            self.update()
    
    def clear_all(self):
        """清除所有数据"""
        self._bar_pictures.clear()
        self._item_picture = None
        self._rect_area = None
        self._to_update = True
        self.update()