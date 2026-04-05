"""
面板基类模块

所有面板的抽象基类，定义统一的接口和行为。
"""

from abc import ABCMeta, abstractmethod
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QDockWidget


# 解决 Qt 元类与 ABC 元类冲突
class CombinedMeta(type(QDockWidget), ABCMeta):
    """联合元类，解决 Qt 和 ABC 的元类冲突"""
    pass


class BasePanel(QDockWidget, metaclass=CombinedMeta):
    """
    面板基类
    
    功能：
    - 定义统一的面板接口
    - 管理 Dock 窗口属性
    - 提供通用的布局方法
    
    信号：
    - sigPanelShown: 面板显示时发出
    - sigPanelHidden: 面板隐藏时发出
    - sigPanelFocused: 面板获得焦点时发出
    """
    
    sigPanelShown = pyqtSignal()
    sigPanelHidden = pyqtSignal()
    sigPanelFocused = pyqtSignal()
    
    def __init__(self, title: str, parent=None):
        """
        初始化面板
        
        Args:
            title: 面板标题
            parent: 父窗口
        """
        super().__init__(title, parent)
        self._setup_dock_properties()
        self._init_ui()
    
    def _setup_dock_properties(self):
        """设置 Dock 窗口属性"""
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | 
            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
    
    @abstractmethod
    def _init_ui(self):
        """
        初始化 UI（子类必须实现）
        """
        pass
    
    @abstractmethod
    def refresh(self):
        """
        刷新面板内容（子类必须实现）
        """
        pass
    
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        self.sigPanelShown.emit()
    
    def hideEvent(self, event):
        """隐藏事件"""
        super().hideEvent(event)
        self.sigPanelHidden.emit()
    
    def focusInEvent(self, event):
        """焦点进入事件"""
        super().focusInEvent(event)
        self.sigPanelFocused.emit()