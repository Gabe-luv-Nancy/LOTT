"""
主窗口模块

应用程序主窗口
"""

from typing import Optional
from PyQt5.QtCore import Qt, pyqtSignal, QSettings
from PyQt5.QtWidgets import (
    QMainWindow, QMenuBar, QMenu, QToolBar, QStatusBar,
    QDockWidget, QMessageBox
)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Frontend.core import SignalBus
from Frontend.styles import ThemeManager
from .dock_manager import DockManager


class MainWindow(QMainWindow):
    """
    主窗口
    
    功能：
    - Dock 窗口管理（三层面板）
    - 响应式布局
    - 菜单栏/工具栏
    - 状态栏
    - 窗口状态保存/恢复
    - 快捷键管理
    """
    
    sigThemeChanged = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("LOTT 量化可视化平台")
        self.setMinimumSize(1200, 800)
        
        # 初始化组件
        self._signal_bus = SignalBus()
        self._theme_manager = ThemeManager()
        self._dock_manager: Optional[DockManager] = None
        
        # 面板引用（可能初始化失败为 None）
        self._database_panel = None
        self._variable_panel = None
        self._backtest_panel = None
        
        self._init_menubar()
        self._init_toolbar()
        self._init_statusbar()
        self._init_docks()
        self._init_connections()
        
        # 加载窗口状态
        self._load_window_state()
    
    def _init_menubar(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        file_menu.addAction("导出数据...", self._export_data)
        file_menu.addAction("导出图表...", self._export_chart)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close, "Ctrl+Q")
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑(&E)")
        edit_menu.addAction("设置...", self._show_settings)
        
        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        view_menu.addAction("重置布局", self._reset_layout)
        view_menu.addSeparator()
        
        # 主题菜单
        theme_menu = menubar.addMenu("主题(&T)")
        theme_menu.addAction("深色主题", lambda: self._change_theme("dark"))
        theme_menu.addAction("浅色主题", lambda: self._change_theme("light"))
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")
        help_menu.addAction("关于...", self._show_about)
    
    def _init_toolbar(self):
        """初始化工具栏"""
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        toolbar.addAction("刷新", self._refresh_data)
        toolbar.addSeparator()
        toolbar.addAction("深色", lambda: self._change_theme("dark"))
        toolbar.addAction("浅色", lambda: self._change_theme("light"))
    
    def _init_statusbar(self):
        """初始化状态栏"""
        self._statusbar = QStatusBar()
        self.setStatusBar(self._statusbar)
        self._statusbar.showMessage("就绪")
    
    def _init_docks(self):
        """初始化 Dock 窗口（三层面板）"""
        self._dock_manager = DockManager(self)
        
        # 图层1：数据库面板
        try:
            from Frontend.panels.database import DatabasePanel
            self._database_panel = DatabasePanel()
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._database_panel)
            self._dock_manager.register_dock("database", self._database_panel)
        except Exception as e:
            print(f"[WARN] 数据库面板初始化失败: {e}")
        
        # 图层2：变量面板
        try:
            from Frontend.panels.variables import VariablePanel
            self._variable_panel = VariablePanel()
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._variable_panel)
            self._dock_manager.register_dock("variables", self._variable_panel)
        except Exception as e:
            print(f"[WARN] 变量面板初始化失败: {e}")
        
        # 图层3：回测面板
        try:
            from Frontend.panels.backtest import BacktestPanel
            self._backtest_panel = BacktestPanel()
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._backtest_panel)
            self._dock_manager.register_dock("backtest", self._backtest_panel)
        except Exception as e:
            print(f"[WARN] 回测面板初始化失败: {e}")
    
    def _init_connections(self):
        """初始化信号连接"""
        self._signal_bus.sigThemeChanged.connect(self._on_theme_changed)
    
    def _save_window_state(self):
        """保存窗口状态"""
        settings = QSettings("LOTT", "Frontend")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("state", self.saveState())
    
    def _load_window_state(self):
        """加载窗口状态"""
        settings = QSettings("LOTT", "Frontend")
        geometry = settings.value("geometry")
        state = settings.value("state")
        
        if geometry:
            self.restoreGeometry(geometry)
        if state:
            self.restoreState(state)
    
    def _adjust_layout(self):
        """调整布局（响应式）"""
        width = self.width()
        
        if width < 1400:
            # 窄屏模式：Tab 合并右侧面板
            if self._variable_panel and self._backtest_panel:
                self.tabifyDockWidget(self._variable_panel, self._backtest_panel)
        # 宽屏模式使用默认水平排列
    
    def resizeEvent(self, event):
        """窗口大小变化事件"""
        super().resizeEvent(event)
        self._adjust_layout()
    
    def closeEvent(self, event):
        """关闭事件"""
        self._save_window_state()
        event.accept()
    
    # ==================== 槽函数 ====================
    
    def _on_theme_changed(self, theme_name: str):
        """主题变化处理"""
        self._theme_manager.set_theme(theme_name)
        self.sigThemeChanged.emit(theme_name)
    
    def _change_theme(self, theme_name: str):
        """切换主题"""
        self._signal_bus.sigThemeChanged.emit(theme_name)
    
    def _reset_layout(self):
        """重置布局"""
        if self._dock_manager:
            self._dock_manager.apply_layout("default")
    
    def _refresh_data(self):
        """刷新数据"""
        self._statusbar.showMessage("刷新数据...", 2000)
    
    def _export_data(self):
        """导出数据"""
        self._statusbar.showMessage("导出数据功能开发中...", 2000)
    
    def _export_chart(self):
        """导出图表"""
        self._statusbar.showMessage("导出图表功能开发中...", 2000)
    
    def _show_settings(self):
        """显示设置对话框"""
        QMessageBox.information(self, "设置", "设置功能开发中...")
    
    def _show_about(self):
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 LOTT",
            "LOTT 量化可视化平台\n\n"
            "版本: 0.1.0\n"
            "技术栈: PyQt5 + pyqtgraph\n\n"
            "三层面板架构：\n"
            "  图层1 - 数据库总表浏览\n"
            "  图层2 - 策略变量分析\n"
            "  图层3 - 回测结果可视化"
        )
