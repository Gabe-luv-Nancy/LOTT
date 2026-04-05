"""
策略变量面板模块

图层2：变量配置和显示
"""

from datetime import datetime
from typing import Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QSpinBox, QDoubleSpinBox, QComboBox,
    QPushButton, QSplitter
)

from Frontend.panels.base_panel import BasePanel
from Frontend.core import DataManager
from .types import VariableConfig
from .multi_line_chart import MultiLineChartWidget
from .variable_list import VariableListWidget


class VariablePanel(BasePanel):
    """
    策略变量面板（图层2）
    
    功能：
    - 多层折线图，同一时间轴
    - 自定义时间区间
    - 自定义颜色
    - lagging 阶数调整
    - 多 Y 轴支持
    - 变量列表管理
    
    信号：
    - sigVariableAdded: 变量添加
    - sigVariableRemoved: 变量移除
    - sigVariableConfigChanged: 变量配置变化
    - sigRangeChanged: 范围变化
    """
    
    sigVariableAdded = pyqtSignal(str)       # 变量名（列哈希）
    sigVariableRemoved = pyqtSignal(str)     # 变量名
    sigVariableConfigChanged = pyqtSignal(str, object)  # (变量名, 配置)
    sigRangeChanged = pyqtSignal(tuple)      # (start, end)
    
    # 预设颜色
    PRESET_COLORS = [
        QColor(255, 99, 132),   # 红
        QColor(54, 162, 235),   # 蓝
        QColor(255, 206, 86),   # 黄
        QColor(75, 192, 192),   # 青
        QColor(153, 102, 255),  # 紫
        QColor(255, 159, 64),   # 橙
    ]
    
    def __init__(self, parent=None):
        """初始化变量面板"""
        self._variables: Dict[str, VariableConfig] = {}
        self._data_manager: Optional[DataManager] = None
        self._color_index = 0
        super().__init__("策略变量层", parent)
    
    def _init_ui(self):
        """初始化 UI"""
        # 主容器
        main_widget = QWidget()
        self.setWidget(main_widget)
        
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧：控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(300)
        
        # 变量列表
        self._variable_list = VariableListWidget()
        self._variable_list.sigVariableToggled.connect(self._on_variable_toggled)
        control_layout.addWidget(self._variable_list)
        
        # 变量配置
        config_group = QGroupBox("变量配置")
        config_layout = QFormLayout(config_group)
        
        # 颜色选择
        from Frontend.ui.widgets.color_picker import ColorPickerButton
        self._color_picker = ColorPickerButton()
        self._color_picker.sigColorChanged.connect(self._on_color_changed)
        config_layout.addRow("颜色:", self._color_picker)
        
        # Lagging阶数
        self._lagging_spin = QSpinBox()
        self._lagging_spin.setRange(-100, 100)
        self._lagging_spin.setValue(0)
        self._lagging_spin.valueChanged.connect(self._on_lagging_changed)
        config_layout.addRow("滞后阶数:", self._lagging_spin)
        
        # Y轴选择
        self._y_axis_combo = QComboBox()
        self._y_axis_combo.addItems(["左Y轴", "右Y轴", "独立Y轴"])
        self._y_axis_combo.currentIndexChanged.connect(self._on_y_axis_changed)
        config_layout.addRow("Y轴:", self._y_axis_combo)
        
        # 线型选择
        self._line_style_combo = QComboBox()
        self._line_style_combo.addItems(["实线", "虚线", "点线", "点划线"])
        config_layout.addRow("线型:", self._line_style_combo)
        
        # 线宽
        self._line_width_spin = QDoubleSpinBox()
        self._line_width_spin.setRange(0.5, 5.0)
        self._line_width_spin.setValue(1.0)
        self._line_width_spin.setSingleStep(0.5)
        config_layout.addRow("线宽:", self._line_width_spin)
        
        control_layout.addWidget(config_group)
        
        # 添加/移除按钮
        btn_layout = QHBoxLayout()
        self._add_btn = QPushButton("添加变量")
        self._remove_btn = QPushButton("移除变量")
        btn_layout.addWidget(self._add_btn)
        btn_layout.addWidget(self._remove_btn)
        control_layout.addLayout(btn_layout)
        
        splitter.addWidget(control_panel)
        
        # 右侧：图表区域
        self._chart_widget = MultiLineChartWidget()
        splitter.addWidget(self._chart_widget)
        
        # 设置分割比例
        splitter.setSizes([250, 500])
        
        layout.addWidget(splitter)
    
    def set_data_manager(self, data_manager: DataManager):
        """设置数据管理器"""
        self._data_manager = data_manager
    
    def add_variable(self, col_hash: str, config: Optional[VariableConfig] = None):
        """添加变量"""
        if config is None:
            config = VariableConfig(
                color=self._get_next_color(),
                lagging=0,
                y_axis=0,
                line_style=0,
                line_width=1.0
            )
        
        self._variables[col_hash] = config
        self._variable_list.add_variable(
            col_hash,
            display_name=config.display_name or None,
            color=config.color.name() if config.color else None,
        )
        self._chart_widget.add_line(col_hash, config)
        self.sigVariableAdded.emit(col_hash)
    
    def remove_variable(self, col_hash: str):
        """移除变量"""
        if col_hash in self._variables:
            del self._variables[col_hash]
            self._variable_list.remove_variable(col_hash)
            self._chart_widget.remove_line(col_hash)
            self.sigVariableRemoved.emit(col_hash)
    
    def get_variable(self, col_hash: str) -> Optional[VariableConfig]:
        """获取变量配置"""
        return self._variables.get(col_hash)
    
    def get_all_variables(self) -> Dict[str, VariableConfig]:
        """获取所有变量"""
        return self._variables.copy()
    
    def clear_all_variables(self):
        """清除所有变量"""
        self._variables.clear()
        self._variable_list.clear_variables()
        self._chart_widget.clear_all()
    
    def set_lagging(self, col_hash: str, lagging: int):
        """设置滞后阶数"""
        if col_hash in self._variables:
            self._variables[col_hash].lagging = lagging
            self._chart_widget.update_line_config(col_hash, self._variables[col_hash])
            self.sigVariableConfigChanged.emit(col_hash, self._variables[col_hash])
    
    def set_color(self, col_hash: str, color: QColor):
        """设置颜色"""
        if col_hash in self._variables:
            self._variables[col_hash].color = color
            self._chart_widget.update_line_config(col_hash, self._variables[col_hash])
            self.sigVariableConfigChanged.emit(col_hash, self._variables[col_hash])
    
    def _get_next_color(self) -> QColor:
        """获取下一个预设颜色"""
        color = self.PRESET_COLORS[self._color_index % len(self.PRESET_COLORS)]
        self._color_index += 1
        return color
    
    def _on_variable_toggled(self, col_hash: str, visible: bool):
        """变量可见性切换"""
        if col_hash in self._variables:
            self._variables[col_hash].visible = visible
            self._chart_widget.set_line_visible(col_hash, visible)
    
    def _on_color_changed(self, color: QColor):
        """颜色变化处理"""
        selected = self._variable_list.selected_variable
        if selected:
            self.set_color(selected, color)
    
    def _on_lagging_changed(self, value: int):
        """滞后阶数变化处理"""
        selected = self._variable_list.selected_variable
        if selected:
            self.set_lagging(selected, value)
    
    def _on_y_axis_changed(self, index: int):
        """Y轴变化处理"""
        selected = self._variable_list.selected_variable
        if selected and selected in self._variables:
            self._variables[selected].y_axis = index
            self._chart_widget.update_line_config(selected, self._variables[selected])
    
    def load_data(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        """加载变量数据"""
        if self._data_manager is None:
            return
        
        for col_hash in self._variables:
            data = self._data_manager.get_column_data(col_hash, start_date, end_date)
            if data is not None:
                self._chart_widget.set_data(col_hash, data)
    
    def refresh(self):
        """刷新面板"""
        self.load_data()