"""
滞后阶数控制组件

控制变量的滞后阶数
"""

from typing import Optional
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QSlider, QSpinBox, QPushButton
)


class LaggingControlWidget(QWidget):
    """
    滞后阶数控制组件
    
    信号：
    - sigLaggingChanged: 滞后阶数变化
    """
    
    sigLaggingChanged = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("滞后阶数控制:")
        layout.addWidget(title)
        
        # 滑块和数值
        slider_layout = QHBoxLayout()
        
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(-100, 100)
        self._slider.setValue(0)
        self._slider.valueChanged.connect(self._on_slider_changed)
        slider_layout.addWidget(self._slider)
        
        self._spinbox = QSpinBox()
        self._spinbox.setRange(-100, 100)
        self._spinbox.setValue(0)
        self._spinbox.valueChanged.connect(self._on_spinbox_changed)
        slider_layout.addWidget(self._spinbox)
        
        layout.addLayout(slider_layout)
        
        # 快捷按钮
        btn_layout = QHBoxLayout()
        
        btn_minus5 = QPushButton("-5")
        btn_minus5.clicked.connect(lambda: self._adjust_lagging(-5))
        btn_layout.addWidget(btn_minus5)
        
        btn_minus1 = QPushButton("-1")
        btn_minus1.clicked.connect(lambda: self._adjust_lagging(-1))
        btn_layout.addWidget(btn_minus1)
        
        btn_reset = QPushButton("重置")
        btn_reset.clicked.connect(lambda: self.set_lagging(0))
        btn_layout.addWidget(btn_reset)
        
        btn_plus1 = QPushButton("+1")
        btn_plus1.clicked.connect(lambda: self._adjust_lagging(1))
        btn_layout.addWidget(btn_plus1)
        
        btn_plus5 = QPushButton("+5")
        btn_plus5.clicked.connect(lambda: self._adjust_lagging(5))
        btn_layout.addWidget(btn_plus5)
        
        layout.addLayout(btn_layout)
    
    def _on_slider_changed(self, value: int):
        """滑块变化处理"""
        self._spinbox.blockSignals(True)
        self._spinbox.setValue(value)
        self._spinbox.blockSignals(False)
        self.sigLaggingChanged.emit(value)
    
    def _on_spinbox_changed(self, value: int):
        """数值框变化处理"""
        self._slider.blockSignals(True)
        self._slider.setValue(value)
        self._slider.blockSignals(False)
        self.sigLaggingChanged.emit(value)
    
    def _adjust_lagging(self, delta: int):
        """调整滞后阶数"""
        new_value = self._slider.value() + delta
        new_value = max(-100, min(100, new_value))
        self.set_lagging(new_value)
    
    def get_lagging(self) -> int:
        """获取滞后阶数"""
        return self._slider.value()
    
    def set_lagging(self, value: int):
        """设置滞后阶数"""
        value = max(-100, min(100, value))
        self._slider.setValue(value)


# 兼容性别名
LaggingControl = LaggingControlWidget
