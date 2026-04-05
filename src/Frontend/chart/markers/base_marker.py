"""
标记基类模块

所有标记的抽象基类，定义标记的基本属性和交互行为。
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Optional

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor, QFont
import pyqtgraph as pg

# 定义abstractmethod装饰器（简化版本，不使用ABC）
def abstractmethod(func):
    """标记为抽象方法的装饰器"""
    return func


class MarkerType(Enum):
    """标记类型枚举"""
    # 主动交易
    BUY = auto()              # 主动买入
    SELL = auto()             # 主动卖出
    
    # 被动交易
    STOP_LOSS = auto()        # 止损
    TAKE_PROFIT = auto()      # 止盈
    LIQUIDATION = auto()      # 强制平仓
    
    # 信号标记
    SIGNAL_BUY = auto()       # 买入信号
    SIGNAL_SELL = auto()      # 卖出信号
    
    # 分析标记
    PIVOT_HIGH = auto()       # 枢轴高点
    PIVOT_LOW = auto()        # 枢轴低点
    BREAKOUT = auto()         # 突破点
    
    # 自定义
    CUSTOM = auto()           # 自定义


class MarkerShape(Enum):
    """标记形状枚举"""
    TRIANGLE_UP = "triangle_up"
    TRIANGLE_DOWN = "triangle_down"
    CIRCLE = "circle"
    SQUARE = "square"
    DIAMOND = "diamond"
    STAR = "star"
    ARROW_UP = "arrow_up"
    ARROW_DOWN = "arrow_down"
    CROSS = "cross"
    FLAG = "flag"
    PIN = "pin"


class MarkerPosition(Enum):
    """标记位置"""
    ABOVE_BAR = "above"       # K线上方
    BELOW_BAR = "below"       # K线下方
    ON_BAR = "on"             # K线上
    INLINE = "inline"         # 与价格对齐


@dataclass
class MarkerStyle:
    """标记样式配置"""
    shape: MarkerShape = MarkerShape.TRIANGLE_UP
    size: float = 10.0
    color: QColor = None  # type: ignore
    border_color: QColor = None  # type: ignore
    border_width: float = 1.0
    opacity: float = 1.0
    
    # 文本配置
    show_text: bool = False
    text: str = ""
    text_color: QColor = None  # type: ignore
    text_font: QFont = None  # type: ignore
    text_offset: tuple = (0, -15)
    
    # 位置配置
    position: MarkerPosition = MarkerPosition.ABOVE_BAR
    offset: float = 5.0
    
    # 交互配置
    hoverable: bool = True
    selectable: bool = True
    draggable: bool = False
    
    def __post_init__(self):
        if self.color is None:
            self.color = QColor(255, 0, 0)
        if self.border_color is None:
            self.border_color = QColor(255, 255, 255)
        if self.text_color is None:
            self.text_color = QColor(255, 255, 255)
        if self.text_font is None:
            self.text_font = QFont("Arial", 8)


@dataclass
class MarkerData:
    """标记数据"""
    marker_type: MarkerType
    x: int                    # X轴索引
    y: float                  # Y轴值
    style: MarkerStyle = None  # type: ignore
    
    # 附加信息
    order_id: Optional[str] = None
    strategy_name: Optional[str] = None
    timestamp: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    display_text: Optional[str] = None
    
    def __post_init__(self):
        if self.style is None:
            self.style = MarkerStyle()


class BaseMarker(pg.GraphicsObject):
    """
    标记基类
    
    参考: FRONTEND_REQUIREMENTS.md 中的标记系统设计
    
    信号：
    - sigClicked: 点击信号
    - sigDoubleClicked: 双击信号
    - sigHoverEnter: 悬浮进入
    - sigHoverLeave: 悬浮离开
    """
    
    sigClicked = pyqtSignal(object)
    sigDoubleClicked = pyqtSignal(object)
    sigHoverEnter = pyqtSignal(object)
    sigHoverLeave = pyqtSignal(object)
    
    def __init__(self, data: MarkerData, parent=None):
        super().__init__(parent)
        self._data = data
        self._style = data.style
        self._picture = None
        self._is_hovered = False
        self._is_selected = False
        
        self.setAcceptHoverEvents(True)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, data.style.selectable)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, data.style.draggable)
    
    @abstractmethod
    def _draw_marker(self, painter: QPainter) -> None:
        """绘制标记的具体实现"""
        pass
    
    @abstractmethod
    def boundingRect(self) -> QRectF:
        """返回边界矩形"""
        pass
    
    def paint(self, painter: QPainter, option, widget=None):
        """绘制标记"""
        painter.save()
        painter.setOpacity(self._style.opacity)
        
        # 应用悬浮效果
        if self._is_hovered:
            painter.setOpacity(self._style.opacity * 0.8)
        
        self._draw_marker(painter)
        
        # 绘制选中边框
        if self._is_selected:
            rect = self.boundingRect()
            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)
        
        painter.restore()
    
    def get_tooltip_text(self) -> str:
        """获取悬浮提示文本"""
        text = f"类型: {self._data.marker_type.name}\n"
        text += f"位置: ({self._data.x}, {self._data.y:.2f})\n"
        
        if self._data.order_id:
            text += f"订单ID: {self._data.order_id}\n"
        if self._data.strategy_name:
            text += f"策略: {self._data.strategy_name}\n"
        if self._data.display_text:
            text += f"描述: {self._data.display_text}"
        
        return text
    
    def hoverEnterEvent(self, event):
        """悬浮进入事件"""
        self._is_hovered = True
        self.sigHoverEnter.emit(self)
        self.update()
    
    def hoverLeaveEvent(self, event):
        """悬浮离开事件"""
        self._is_hovered = False
        self.sigHoverLeave.emit(self)
        self.update()
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self._is_selected = True
            self.sigClicked.emit(self)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件"""
        if event.button() == Qt.LeftButton:
            self.sigDoubleClicked.emit(self)
        super().mouseDoubleClickEvent(event)
    
    def update_style(self, style: MarkerStyle):
        """更新标记样式"""
        self._style = style
        self._data.style = style
        self.update()
    
    def set_selected(self, selected: bool):
        """设置选中状态"""
        self._is_selected = selected
        self.update()
    
    @property
    def data(self) -> MarkerData:
        return self._data
    
    @property
    def marker_type(self) -> MarkerType:
        return self._data.marker_type
    
    @property
    def x(self) -> int:
        return self._data.x
    
    @property
    def y(self) -> float:
        return self._data.y