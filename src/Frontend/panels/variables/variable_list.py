"""
变量列表组件模块

提供可添加/删除/配置的变量列表管理界面。
"""

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton,
    QColorDialog, QMenu, QAction, QLabel,
    QAbstractItemView,
)

from .types import VariableConfig


class VariableListItem(QListWidgetItem):
    """
    变量列表项
    
    显示变量名称、颜色标记、可见性状态。
    """
    
    def __init__(self, config: VariableConfig, parent=None):
        super().__init__(parent)
        self._config = config
        self._update_display()
    
    @property
    def config(self) -> VariableConfig:
        return self._config
    
    @config.setter
    def config(self, value: VariableConfig):
        self._config = value
        self._update_display()
    
    def _update_display(self):
        """更新显示内容"""
        # 显示名称
        display_name = self._config.display_name or self._config.column_hash
        self.setText(display_name)
        
        # 颜色标记
        self.setForeground(self._config.color)
        
        # 可见性
        flags = self.flags()
        if not self._config.visible:
            self.setFlags(Qt.ItemFlags(flags & ~Qt.ItemFlag.ItemIsEnabled))  # type: ignore[operator]
        else:
            self.setFlags(Qt.ItemFlags(flags | Qt.ItemFlag.ItemIsEnabled))  # type: ignore[operator]
    
    @property
    def column_hash(self) -> str:
        return self._config.column_hash
    
    @property
    def visible(self) -> bool:
        return self._config.visible
    
    @visible.setter
    def visible(self, value: bool):
        self._config.visible = value
        self._update_display()


class VariableListWidget(QWidget):
    """
    变量列表管理组件
    
    功能：
    - 显示已添加的变量列表
    - 支持添加/删除变量
    - 支持修改变量颜色
    - 支持变量可见性切换
    - 支持拖拽排序
    - 右键菜单操作
    
    信号：
    - sigVariableAdded: 变量添加 (column_hash)
    - sigVariableRemoved: 变量移除 (column_hash)
    - sigVariableToggled: 变量可见性切换 (column_hash, visible)
    - sigColorChanged: 颜色修改 (column_hash, color_str)
    - sigSelectionChanged: 选中变量变化 (column_hash)
    """
    
    sigVariableAdded = pyqtSignal(str)
    sigVariableRemoved = pyqtSignal(str)
    sigVariableToggled = pyqtSignal(str, bool)
    sigColorChanged = pyqtSignal(str, str)
    sigSelectionChanged = pyqtSignal(str)
    
    # 默认颜色列表（循环使用）
    DEFAULT_COLORS = [
        '#FF6B6B',  # 红
        '#4ECDC4',  # 青
        '#45B7D1',  # 蓝
        '#96CEB4',  # 绿
        '#FFEAA7',  # 黄
        '#DDA0DD',  # 紫
        '#FF8C00',  # 橙
        '#87CEEB',  # 天蓝
        '#98D8C8',  # 薄荷
        '#F7DC6F',  # 金
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._variables: Dict[str, VariableListItem] = {}
        self._color_index = 0
        
        self._init_ui()
        self._init_connections()
    
    def _init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)
        
        # 标题行
        header = QHBoxLayout()
        header.addWidget(QLabel("变量列表"))
        header.addStretch()
        
        # 操作按钮
        self._btn_remove = QPushButton("删除")
        self._btn_remove.setFixedWidth(50)
        self._btn_remove.setEnabled(False)
        header.addWidget(self._btn_remove)
        
        self._btn_clear = QPushButton("清空")
        self._btn_clear.setFixedWidth(50)
        header.addWidget(self._btn_clear)
        
        layout.addLayout(header)
        
        # 列表
        self._list_widget = QListWidget()
        self._list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self._list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self._list_widget)
    
    def _init_connections(self):
        """初始化信号连接"""
        self._btn_remove.clicked.connect(self._on_remove_clicked)
        self._btn_clear.clicked.connect(self._on_clear_clicked)
        self._list_widget.currentItemChanged.connect(self._on_selection_changed)
        self._list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list_widget.customContextMenuRequested.connect(self._on_context_menu)
    
    # ==================== 公开接口 ====================
    
    def add_variable(self, column_hash: str, display_name: Optional[str] = None,
                     color: Optional[str] = None) -> VariableConfig:
        """
        添加变量到列表
        
        Args:
            column_hash: 列哈希值
            display_name: 显示名称（可选）
            color: 颜色（可选，自动分配）
            
        Returns:
            创建的 VariableConfig
        """
        if column_hash in self._variables:
            return self._variables[column_hash].config
        
        # 自动分配颜色
        if color is None:
            color = self.DEFAULT_COLORS[self._color_index % len(self.DEFAULT_COLORS)]
            self._color_index += 1
        
        config = VariableConfig(
            column_hash=column_hash,
            display_name=display_name or column_hash[:12],
            color=QColor(color),
            visible=True,
            y_axis=0,
            lagging=0,
        )
        
        item = VariableListItem(config)
        self._variables[column_hash] = item
        self._list_widget.addItem(item)
        
        self.sigVariableAdded.emit(column_hash)
        return config
    
    def remove_variable(self, column_hash: str):
        """移除变量"""
        if column_hash not in self._variables:
            return
        
        item = self._variables.pop(column_hash)
        row = self._list_widget.row(item)
        self._list_widget.takeItem(row)
        
        self.sigVariableRemoved.emit(column_hash)
    
    def clear_variables(self):
        """清空所有变量"""
        for col_hash in list(self._variables.keys()):
            self.remove_variable(col_hash)
        self._color_index = 0
    
    def get_variable_config(self, column_hash: str) -> Optional[VariableConfig]:
        """获取变量配置"""
        item = self._variables.get(column_hash)
        return item.config if item else None
    
    def get_all_configs(self) -> List[VariableConfig]:
        """获取所有变量配置（按列表顺序）"""
        configs = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if isinstance(item, VariableListItem):
                configs.append(item.config)
        return configs
    
    def get_visible_configs(self) -> List[VariableConfig]:
        """获取所有可见变量配置"""
        return [c for c in self.get_all_configs() if c.visible]
    
    def set_variable_color(self, column_hash: str, color: str):
        """设置变量颜色"""
        item = self._variables.get(column_hash)
        if item:
            item.config.color = QColor(color)
            item._update_display()
            self.sigColorChanged.emit(column_hash, color)
    
    def toggle_variable(self, column_hash: str):
        """切换变量可见性"""
        item = self._variables.get(column_hash)
        if item:
            item.visible = not item.visible
            self.sigVariableToggled.emit(column_hash, item.visible)
    
    @property
    def variable_count(self) -> int:
        return len(self._variables)
    
    @property
    def selected_variable(self) -> Optional[str]:
        """当前选中的变量哈希"""
        item = self._list_widget.currentItem()
        if isinstance(item, VariableListItem):
            return item.column_hash
        return None
    
    # ==================== 私有方法 ====================
    
    def _on_remove_clicked(self):
        """删除按钮点击"""
        col_hash = self.selected_variable
        if col_hash:
            self.remove_variable(col_hash)
    
    def _on_clear_clicked(self):
        """清空按钮点击"""
        self.clear_variables()
    
    def _on_selection_changed(self, current, previous):
        """选中项变化"""
        if isinstance(current, VariableListItem):
            self._btn_remove.setEnabled(True)
            self.sigSelectionChanged.emit(current.column_hash)
        else:
            self._btn_remove.setEnabled(False)
    
    def _on_item_double_clicked(self, item):
        """双击切换可见性"""
        if isinstance(item, VariableListItem):
            self.toggle_variable(item.column_hash)
    
    def _on_context_menu(self, pos):
        """右键菜单"""
        item = self._list_widget.itemAt(pos)
        if not isinstance(item, VariableListItem):
            return
        
        menu = QMenu(self)
        
        # 修改颜色
        action_color = QAction("修改颜色...", self)
        action_color.triggered.connect(lambda: self._change_color(item))
        menu.addAction(action_color)
        
        # 切换可见性
        vis_text = "隐藏" if item.visible else "显示"
        action_toggle = QAction(f"{vis_text}变量", self)
        action_toggle.triggered.connect(lambda: self.toggle_variable(item.column_hash))
        menu.addAction(action_toggle)
        
        menu.addSeparator()
        
        # 删除
        action_remove = QAction("删除", self)
        action_remove.triggered.connect(lambda: self.remove_variable(item.column_hash))
        menu.addAction(action_remove)
        
        menu.exec_(self._list_widget.mapToGlobal(pos))
    
    def _change_color(self, item: VariableListItem):
        """修改变量颜色"""
        current_color = QColor(item.config.color)
        color = QColorDialog.getColor(current_color, self, "选择变量颜色")
        if color.isValid():
            self.set_variable_color(item.column_hash, color.name())
