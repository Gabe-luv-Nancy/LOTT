"""
Dock 管理器模块

管理 Dock 窗口的布局和状态
"""

from typing import Dict, List, Optional, Any
from PyQt5.QtCore import QObject, pyqtSignal, QSettings
from PyQt5.QtWidgets import QDockWidget, QMainWindow


class DockManager(QObject):
    """
    Dock 管理器
    
    功能：
    - Dock 窗口注册/注销
    - 预设布局管理
    - 布局保存/恢复
    """
    
    sigLayoutChanged = pyqtSignal(str)
    
    # 预设布局
    PRESET_LAYOUTS = {
        "default": {
            "database": {"area": "left", "width": 300},
            "variables": {"area": "right", "width": 400},
            "backtest": {"area": "bottom", "height": 300},
        },
        "analysis": {
            "database": {"area": "left", "width": 250},
            "variables": {"area": "right", "width": 500},
            "backtest": {"area": "right", "height": 400},
        },
        "wide": {
            "database": {"area": "left", "width": 350},
            "variables": {"area": "right", "width": 600},
            "backtest": {"area": "bottom", "height": 350},
        },
    }
    
    def __init__(self, main_window: QMainWindow):
        super().__init__(main_window)
        self._main_window = main_window
        self._docks: Dict[str, QDockWidget] = {}
    
    def register_dock(self, name: str, dock: QDockWidget):
        """
        注册 Dock 窗口
        
        Args:
            name: Dock 名称
            dock: Dock 窗口
        """
        self._docks[name] = dock
    
    def unregister_dock(self, name: str):
        """注销 Dock 窗口"""
        if name in self._docks:
            del self._docks[name]
    
    def get_dock(self, name: str) -> Optional[QDockWidget]:
        """获取 Dock 窗口"""
        return self._docks.get(name)
    
    def get_all_docks(self) -> Dict[str, QDockWidget]:
        """获取所有 Dock 窗口"""
        return self._docks.copy()
    
    def apply_layout(self, layout_name: str):
        """
        应用预设布局
        
        Args:
            layout_name: 布局名称
        """
        if layout_name not in self.PRESET_LAYOUTS:
            return
        
        layout = self.PRESET_LAYOUTS[layout_name]
        
        for name, config in layout.items():
            dock = self._docks.get(name)
            if dock:
                # 设置区域
                area = config.get("area", "left")
                if area == "left":
                    self._main_window.addDockWidget(
                        0x1, dock  # Qt.LeftDockWidgetArea
                    )
                elif area == "right":
                    self._main_window.addDockWidget(
                        0x2, dock  # Qt.RightDockWidgetArea
                    )
                elif area == "bottom":
                    self._main_window.addDockWidget(
                        0x8, dock  # Qt.BottomDockWidgetArea
                    )
                
                # 设置大小
                if "width" in config:
                    dock.setMinimumWidth(config["width"])
                if "height" in config:
                    dock.setMinimumHeight(config["height"])
        
        self.sigLayoutChanged.emit(layout_name)
    
    def save_layout(self, name: str):
        """保存当前布局"""
        settings = QSettings("LOTT", "DockLayouts")
        layout_data = {}
        
        for dock_name, dock in self._docks.items():
            layout_data[dock_name] = {
                "visible": dock.isVisible(),
                "floating": dock.isFloating(),
            }
        
        settings.setValue(name, layout_data)
    
    def restore_layout(self, name: str):
        """恢复保存的布局"""
        settings = QSettings("LOTT", "DockLayouts")
        layout_data = settings.value(name)
        
        if not layout_data:
            return
        
        for dock_name, config in layout_data.items():
            dock = self._docks.get(dock_name)
            if dock:
                dock.setVisible(config.get("visible", True))
                dock.setFloating(config.get("floating", False))
    
    def get_available_layouts(self) -> List[str]:
        """获取可用布局列表"""
        return list(self.PRESET_LAYOUTS.keys())
    
    def show_dock(self, name: str):
        """显示 Dock 窗口"""
        dock = self._docks.get(name)
        if dock:
            dock.show()
            dock.raise_()
    
    def hide_dock(self, name: str):
        """隐藏 Dock 窗口"""
        dock = self._docks.get(name)
        if dock:
            dock.hide()
    
    def toggle_dock(self, name: str):
        """切换 Dock 窗口可见性"""
        dock = self._docks.get(name)
        if dock:
            dock.setVisible(not dock.isVisible())