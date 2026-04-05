"""
主题管理模块

提供颜色主题、样式配置的统一管理。
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional, Tuple, Any

from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal, QObject


class ColorScheme(Enum):
    """颜色方案枚举"""
    DARK = auto()        # 深色主题
    LIGHT = auto()       # 浅色主题
    CLASSIC = auto()     # 经典主题
    CUSTOM = auto()      # 自定义主题


@dataclass
class Theme:
    """
    主题配置
    
    定义图表和UI的颜色、字体等样式。
    """
    name: str
    scheme: ColorScheme = ColorScheme.DARK
    
    # 背景颜色
    background: QColor = None  # type: ignore
    background_alt: QColor = None  # type: ignore
    
    # 文字颜色
    text_primary: QColor = None  # type: ignore
    text_secondary: QColor = None  # type: ignore
    
    # K线颜色
    candle_up: QColor = None  # type: ignore
    candle_down: QColor = None  # type: ignore
    candle_wick: QColor = None  # type: ignore
    
    # 成交量颜色
    volume_up: QColor = None  # type: ignore
    volume_down: QColor = None  # type: ignore
    
    # 网格颜色
    grid_line: QColor = None  # type: ignore
    axis_line: QColor = None  # type: ignore
    
    # 十字光标颜色
    crosshair: QColor = None  # type: ignore
    
    # 标记颜色
    marker_buy: QColor = None  # type: ignore
    marker_sell: QColor = None  # type: ignore
    marker_signal: QColor = None  # type: ignore
    
    # 置信区间颜色
    band_fill: QColor = None  # type: ignore
    band_border: QColor = None  # type: ignore
    
    # 指标颜色
    indicator_ma1: QColor = None  # type: ignore
    indicator_ma2: QColor = None  # type: ignore
    indicator_ma3: QColor = None  # type: ignore
    
    def __post_init__(self):
        """初始化默认颜色"""
        if self.background is None:
            self.background = QColor(26, 26, 46)
        if self.background_alt is None:
            self.background_alt = QColor(35, 35, 55)
        
        if self.text_primary is None:
            self.text_primary = QColor(255, 255, 255)
        if self.text_secondary is None:
            self.text_secondary = QColor(150, 150, 150)
        
        if self.candle_up is None:
            self.candle_up = QColor(255, 0, 0)
        if self.candle_down is None:
            self.candle_down = QColor(0, 255, 0)
        if self.candle_wick is None:
            self.candle_wick = QColor(200, 200, 200)
        
        if self.volume_up is None:
            self.volume_up = QColor(255, 0, 0, 150)
        if self.volume_down is None:
            self.volume_down = QColor(0, 255, 0, 150)
        
        if self.grid_line is None:
            self.grid_line = QColor(60, 60, 80)
        if self.axis_line is None:
            self.axis_line = QColor(80, 80, 100)
        
        if self.crosshair is None:
            self.crosshair = QColor(255, 255, 255, 100)
        
        if self.marker_buy is None:
            self.marker_buy = QColor(255, 0, 0)
        if self.marker_sell is None:
            self.marker_sell = QColor(0, 255, 0)
        if self.marker_signal is None:
            self.marker_signal = QColor(255, 255, 0)
        
        if self.band_fill is None:
            self.band_fill = QColor(100, 150, 255, 80)
        if self.band_border is None:
            self.band_border = QColor(100, 150, 255)
        
        if self.indicator_ma1 is None:
            self.indicator_ma1 = QColor(255, 255, 255)
        if self.indicator_ma2 is None:
            self.indicator_ma2 = QColor(255, 255, 0)
        if self.indicator_ma3 is None:
            self.indicator_ma3 = QColor(255, 0, 255)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'scheme': self.scheme.name,
            'background': self.background.name(),
            'background_alt': self.background_alt.name(),
            'text_primary': self.text_primary.name(),
            'text_secondary': self.text_secondary.name(),
            'candle_up': self.candle_up.name(),
            'candle_down': self.candle_down.name(),
            'candle_wick': self.candle_wick.name(),
            'volume_up': self.volume_up.name(),
            'volume_down': self.volume_down.name(),
            'grid_line': self.grid_line.name(),
            'axis_line': self.axis_line.name(),
            'crosshair': self.crosshair.name(),
            'marker_buy': self.marker_buy.name(),
            'marker_sell': self.marker_sell.name(),
            'marker_signal': self.marker_signal.name(),
            'band_fill': self.band_fill.name(),
            'band_border': self.band_border.name(),
            'indicator_ma1': self.indicator_ma1.name(),
            'indicator_ma2': self.indicator_ma2.name(),
            'indicator_ma3': self.indicator_ma3.name(),
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取主题属性值（兼容字典式访问）
        
        Args:
            key: 属性名
            default: 默认值
            
        Returns:
            属性值
        """
        # 映射表
        key_map = {
            'name': 'name',
            'scheme': 'scheme',
            'background': 'background',
            'background_alt': 'background_alt',
            'text_primary': 'text_primary',
            'text_secondary': 'text_secondary',
            'candle_up': 'candle_up',
            'candle_down': 'candle_down',
            'candle_wick': 'candle_wick',
            'volume_up': 'volume_up',
            'volume_down': 'volume_down',
            'grid_line': 'grid_line',
            'axis_line': 'axis_line',
            'crosshair': 'crosshair',
            'marker_buy': 'marker_buy',
            'marker_sell': 'marker_sell',
            'marker_signal': 'marker_signal',
            'band_fill': 'band_fill',
            'band_border': 'band_border',
            'indicator_ma1': 'indicator_ma1',
            'indicator_ma2': 'indicator_ma2',
            'indicator_ma3': 'indicator_ma3',
        }
        
        if key in key_map:
            return getattr(self, key_map[key], default)
        return default


class ThemeManager(QObject):
    """
    主题管理器
    
    功能：
    - 管理多个主题
    - 切换主题
    - 发送主题变更信号
    """
    
    sigThemeChanged = pyqtSignal(Theme)
    
    # 预设主题
    DARK_THEME = Theme(
        name="Dark",
        scheme=ColorScheme.DARK,
    )
    
    LIGHT_THEME = Theme(
        name="Light",
        scheme=ColorScheme.LIGHT,
        background=QColor(255, 255, 255),
        background_alt=QColor(240, 240, 240),
        text_primary=QColor(0, 0, 0),
        text_secondary=QColor(100, 100, 100),
        candle_up=QColor(255, 0, 0),
        candle_down=QColor(0, 200, 0),
        grid_line=QColor(200, 200, 200),
        axis_line=QColor(150, 150, 150),
    )
    
    CLASSIC_THEME = Theme(
        name="Classic",
        scheme=ColorScheme.CLASSIC,
        background=QColor(20, 20, 20),
        background_alt=QColor(30, 30, 30),
        candle_up=QColor(255, 50, 50),
        candle_down=QColor(50, 255, 50),
        grid_line=QColor(50, 50, 50),
    )
    
    def __init__(self):
        super().__init__()
        
        self._themes: Dict[str, Theme] = {
            'dark': self.DARK_THEME,
            'light': self.LIGHT_THEME,
            'classic': self.CLASSIC_THEME,
        }
        self._current_theme: Theme = self.DARK_THEME
    
    def get_theme(self, name: str) -> Optional[Theme]:
        """获取主题"""
        return self._themes.get(name.lower())
    
    def get_current_theme(self) -> Theme:
        """获取当前主题"""
        return self._current_theme
    
    def set_theme(self, name: str) -> bool:
        """
        设置当前主题
        
        Args:
            name: 主题名称
            
        Returns:
            是否成功
        """
        theme = self._themes.get(name.lower())
        if theme:
            self._current_theme = theme
            self.sigThemeChanged.emit(theme)
            return True
        return False
    
    def add_theme(self, theme: Theme):
        """添加自定义主题"""
        self._themes[theme.name.lower()] = theme
    
    def remove_theme(self, name: str) -> bool:
        """移除主题"""
        name_lower = name.lower()
        if name_lower in self._themes and name_lower not in ['dark', 'light', 'classic']:
            del self._themes[name_lower]
            return True
        return False
    
    def get_theme_names(self) -> list:
        """获取所有主题名称"""
        return list(self._themes.keys())


# 模块级便捷常量（兼容直接导入）
# 创建默认管理器实例
_default_manager = ThemeManager()

# 导出模块级常量
DARK_THEME = _default_manager.DARK_THEME
LIGHT_THEME = _default_manager.LIGHT_THEME
CLASSIC_THEME = _default_manager.CLASSIC_THEME
