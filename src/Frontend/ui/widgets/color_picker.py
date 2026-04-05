"""
颜色选择器控件

用于选择颜色
"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QColorDialog


class ColorPickerButton(QPushButton):
    """
    颜色选择按钮
    
    信号：
    - sigColorChanged: 颜色变化时发出
    """
    
    sigColorChanged = pyqtSignal(QColor)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor(255, 99, 132)
        self._update_style()
        self.clicked.connect(self._on_clicked)
    
    def _update_style(self):
        """更新按钮样式"""
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color.name()};
                border: 2px solid #555;
                border-radius: 4px;
                min-width: 60px;
                min-height: 25px;
            }}
            QPushButton:hover {{
                border: 2px solid #888;
            }}
        """)
    
    def _on_clicked(self):
        """点击处理"""
        color = QColorDialog.getColor(self._color, self, "选择颜色")
        if color.isValid():
            self.set_color(color)
    
    def get_color(self) -> QColor:
        """获取当前颜色"""
        return self._color
    
    def set_color(self, color: QColor):
        """设置颜色"""
        self._color = color
        self._update_style()
        self.sigColorChanged.emit(color)