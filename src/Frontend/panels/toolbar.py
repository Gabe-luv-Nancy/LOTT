"""
图表工具栏模块

提供图表操作的工具按钮。
"""

from typing import Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QComboBox, QLabel, QFrame, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtGui import QFont, QIcon


class ChartToolbar(QWidget):
    """
    图表工具栏
    
    功能：
    - 周期切换
    - 图表类型切换
    - 指标添加
    - 主题切换
    - 缩放控制
    """
    
    # 信号
    sigPeriodChanged = pyqtSignal(str)
    sigChartTypeChanged = pyqtSignal(str)
    sigIndicatorToggled = pyqtSignal(str, bool)
    sigThemeChanged = pyqtSignal(str)
    sigZoomIn = pyqtSignal()
    sigZoomOut = pyqtSignal()
    sigResetView = pyqtSignal()
    sigAutoScroll = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._auto_scroll = True
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #252540;
                color: #ffffff;
            }
            QPushButton {
                background-color: #3a3a5a;
                border: 1px solid #4a4a6a;
                border-radius: 3px;
                padding: 5px 10px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: #4a4a6a;
            }
            QPushButton:pressed {
                background-color: #2a2a4a;
            }
            QPushButton:checked {
                background-color: #5a5a8a;
            }
            QComboBox {
                background-color: #3a3a5a;
                border: 1px solid #4a4a6a;
                border-radius: 3px;
                padding: 3px 10px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #3a3a5a;
                color: #ffffff;
                selection-background-color: #5a5a8a;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: #3a3a5a;
                border: 1px solid #4a4a6a;
                border-radius: 3px;
                padding: 3px;
                color: #ffffff;
            }
            QLabel {
                color: #aaaaaa;
            }
        """)
        
        # 主布局
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # 周期选择
        layout.addWidget(self._create_label("周期:"))
        self._period_combo = QComboBox()
        self._period_combo.addItems([
            "1min", "5min", "15min", "30min", "1h", "4h", "1d", "1w"
        ])
        self._period_combo.setCurrentText("1d")
        self._period_combo.currentTextChanged.connect(self.sigPeriodChanged)
        layout.addWidget(self._period_combo)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 图表类型
        layout.addWidget(self._create_label("类型:"))
        self._chart_type_combo = QComboBox()
        self._chart_type_combo.addItems(["K线", "折线", "美国线"])
        self._chart_type_combo.currentTextChanged.connect(self._on_chart_type_changed)
        layout.addWidget(self._chart_type_combo)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 指标按钮
        layout.addWidget(self._create_label("指标:"))
        
        self._ma_btn = self._create_toggle_button("MA")
        self._ma_btn.setChecked(True)
        self._ma_btn.clicked.connect(lambda: self.sigIndicatorToggled.emit("MA", self._ma_btn.isChecked()))
        layout.addWidget(self._ma_btn)
        
        self._vol_btn = self._create_toggle_button("VOL")
        self._vol_btn.setChecked(True)
        self._vol_btn.clicked.connect(lambda: self.sigIndicatorToggled.emit("VOL", self._vol_btn.isChecked()))
        layout.addWidget(self._vol_btn)
        
        self._macd_btn = self._create_toggle_button("MACD")
        self._macd_btn.clicked.connect(lambda: self.sigIndicatorToggled.emit("MACD", self._macd_btn.isChecked()))
        layout.addWidget(self._macd_btn)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 主题选择
        layout.addWidget(self._create_label("主题:"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["深色", "浅色", "经典"])
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        layout.addWidget(self._theme_combo)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 缩放控制
        self._zoom_in_btn = self._create_button("放大")
        self._zoom_in_btn.clicked.connect(self.sigZoomIn)
        layout.addWidget(self._zoom_in_btn)
        
        self._zoom_out_btn = self._create_button("缩小")
        self._zoom_out_btn.clicked.connect(self.sigZoomOut)
        layout.addWidget(self._zoom_out_btn)
        
        self._reset_btn = self._create_button("重置")
        self._reset_btn.clicked.connect(self.sigResetView)
        layout.addWidget(self._reset_btn)
        
        # 分隔线
        layout.addWidget(self._create_separator())
        
        # 自动滚动
        self._auto_scroll_btn = self._create_toggle_button("自动滚动")
        self._auto_scroll_btn.setChecked(True)
        self._auto_scroll_btn.clicked.connect(self._on_auto_scroll)
        layout.addWidget(self._auto_scroll_btn)
        
        # 弹性空间
        layout.addStretch()
    
    def _create_label(self, text: str) -> QLabel:
        """创建标签"""
        label = QLabel(text)
        label.setFont(QFont("Arial", 9))
        return label
    
    def _create_button(self, text: str) -> QPushButton:
        """创建按钮"""
        btn = QPushButton(text)
        btn.setFont(QFont("Arial", 9))
        btn.setFixedHeight(28)
        return btn
    
    def _create_toggle_button(self, text: str) -> QPushButton:
        """创建切换按钮"""
        btn = QPushButton(text)
        btn.setFont(QFont("Arial", 9))
        btn.setCheckable(True)
        btn.setFixedHeight(28)
        return btn
    
    def _create_separator(self) -> QFrame:
        """创建分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setStyleSheet("background-color: #4a4a6a;")
        return line
    
    def _on_chart_type_changed(self, text: str):
        """图表类型变更"""
        type_map = {
            "K线": "candle",
            "折线": "line",
            "美国线": "ohlc"
        }
        self.sigChartTypeChanged.emit(type_map.get(text, "candle"))
    
    def _on_theme_changed(self, text: str):
        """主题变更"""
        theme_map = {
            "深色": "dark",
            "浅色": "light",
            "经典": "classic"
        }
        self.sigThemeChanged.emit(theme_map.get(text, "dark"))
    
    def _on_auto_scroll(self):
        """自动滚动切换"""
        self._auto_scroll = self._auto_scroll_btn.isChecked()
        self.sigAutoScroll.emit(self._auto_scroll)
    
    def set_period(self, period: str):
        """设置周期"""
        self._period_combo.setCurrentText(period)
    
    def set_theme(self, theme: str):
        """设置主题"""
        theme_map = {
            "dark": "深色",
            "light": "浅色",
            "classic": "经典"
        }
        self._theme_combo.setCurrentText(theme_map.get(theme, "深色"))
    
    def set_auto_scroll(self, enabled: bool):
        """设置自动滚动"""
        self._auto_scroll = enabled
        self._auto_scroll_btn.setChecked(enabled)
    
    def is_auto_scroll(self) -> bool:
        """获取自动滚动状态"""
        return self._auto_scroll