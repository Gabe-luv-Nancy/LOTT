"""
图表样式配置模块

定义图表元素的具体样式配置。
"""

from dataclasses import dataclass
from typing import Tuple

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont


@dataclass
class CandleStyle:
    """K线样式配置"""
    # 宽度
    bar_width: float = 0.3
    
    # 颜色
    up_color: Tuple[int, int, int] = (255, 0, 0)
    down_color: Tuple[int, int, int] = (0, 255, 0)
    wick_color: Tuple[int, int, int] = (200, 200, 200)
    
    # 边框
    border_width: int = 1
    show_border: bool = True
    
    # 填充
    solid_up: bool = True
    solid_down: bool = False


@dataclass
class VolumeStyle:
    """成交量样式配置"""
    # 宽度
    bar_width: float = 0.4
    
    # 颜色
    up_color: Tuple[int, int, int] = (255, 0, 0)
    down_color: Tuple[int, int, int] = (0, 255, 0)
    
    # 透明度
    opacity: float = 0.6
    
    # 显示选项
    show_ma: bool = True
    ma_period: int = 5
    ma_color: Tuple[int, int, int] = (255, 255, 255)
    ma_width: float = 1.0


@dataclass
class LineStyle:
    """折线样式配置"""
    # 颜色
    color: Tuple[int, int, int] = (255, 255, 255)
    
    # 线宽
    width: float = 1.0
    
    # 线型
    style: Qt.PenStyle = Qt.SolidLine
    
    # 数据点
    show_points: bool = False
    point_size: float = 4.0
    point_color: Tuple[int, int, int] = (255, 255, 255)


@dataclass
class ChartStyle:
    """
    图表整体样式配置
    
    整合所有图表元素的样式。
    """
    # 名称
    name: str = "default"
    
    # K线样式
    candle: CandleStyle = None  # type: ignore
    
    # 成交量样式
    volume: VolumeStyle = None  # type: ignore
    
    # 折线样式
    line: LineStyle = None  # type: ignore
    
    # 背景颜色
    background: QColor = None  # type: ignore
    
    # 网格样式
    grid_visible: bool = True
    grid_alpha: float = 0.3
    grid_color: QColor = None  # type: ignore
    
    # 坐标轴样式
    axis_visible: bool = True
    axis_color: QColor = None  # type: ignore
    axis_font: QFont = None  # type: ignore
    
    # 十字光标样式
    crosshair_visible: bool = True
    crosshair_color: QColor = None  # type: ignore
    crosshair_width: float = 1.0
    crosshair_style: Qt.PenStyle = Qt.DashLine
    
    # 信息面板样式
    info_font: QFont = None  # type: ignore
    info_color: QColor = None  # type: ignore
    info_background: QColor = None  # type: ignore
    
    def __post_init__(self):
        """初始化默认值"""
        if self.candle is None:
            self.candle = CandleStyle()
        if self.volume is None:
            self.volume = VolumeStyle()
        if self.line is None:
            self.line = LineStyle()
        if self.background is None:
            self.background = QColor(26, 26, 46)
        if self.grid_color is None:
            self.grid_color = QColor(60, 60, 80)
        if self.axis_color is None:
            self.axis_color = QColor(150, 150, 150)
        if self.axis_font is None:
            self.axis_font = QFont("Arial", 8)
        if self.crosshair_color is None:
            self.crosshair_color = QColor(255, 255, 255, 100)
        if self.info_font is None:
            self.info_font = QFont("Consolas", 9)
        if self.info_color is None:
            self.info_color = QColor(255, 255, 255)
        if self.info_background is None:
            self.info_background = QColor(0, 0, 0, 150)
    
    @classmethod
    def from_theme(cls, theme) -> 'ChartStyle':
        """
        从主题创建样式
        
        Args:
            theme: Theme 对象
            
        Returns:
            ChartStyle 对象
        """
        style = cls(name=theme.name)
        
        # 应用主题颜色
        style.background = theme.background
        style.grid_color = theme.grid_line
        style.axis_color = theme.axis_line
        style.crosshair_color = theme.crosshair
        style.info_color = theme.text_primary
        style.info_background = QColor(
            theme.background.red(),
            theme.background.green(),
            theme.background.blue(),
            200
        )
        
        # K线颜色
        style.candle.up_color = (
            theme.candle_up.red(),
            theme.candle_up.green(),
            theme.candle_up.blue()
        )
        style.candle.down_color = (
            theme.candle_down.red(),
            theme.candle_down.green(),
            theme.candle_down.blue()
        )
        
        # 成交量颜色
        style.volume.up_color = style.candle.up_color
        style.volume.down_color = style.candle.down_color
        
        return style


# 预设样式
DEFAULT_STYLE = ChartStyle(name="default")

COMPACT_STYLE = ChartStyle(
    name="compact",
    candle=CandleStyle(bar_width=0.2),
    volume=VolumeStyle(bar_width=0.3, show_ma=False),
)

DETAILED_STYLE = ChartStyle(
    name="detailed",
    candle=CandleStyle(bar_width=0.4, show_border=True),
    volume=VolumeStyle(bar_width=0.5, show_ma=True, ma_period=10),
)