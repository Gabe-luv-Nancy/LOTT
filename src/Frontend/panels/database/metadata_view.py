"""
元数据视图组件

显示选中列的元数据详情
"""

from typing import Any, Dict, Optional
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QLabel, QGroupBox
)


class MetadataViewWidget(QWidget):
    """
    元数据视图组件
    
    显示选中列的详细元数据信息
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_metadata: Optional[Dict] = None
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 基本信息组
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        self._colname_label = QLabel("-")
        self._colname_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        basic_layout.addRow("列名:", self._colname_label)
        
        self._hash_label = QLabel("-")
        self._hash_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        basic_layout.addRow("哈希:", self._hash_label)
        
        self._type_label = QLabel("-")
        basic_layout.addRow("数据类型:", self._type_label)
        
        layout.addWidget(basic_group)
        
        # 数据统计组
        stats_group = QGroupBox("数据统计")
        stats_layout = QFormLayout(stats_group)
        
        self._total_label = QLabel("-")
        stats_layout.addRow("总数量:", self._total_label)
        
        self._valid_label = QLabel("-")
        stats_layout.addRow("有效数量:", self._valid_label)
        
        self._invalid_label = QLabel("-")
        stats_layout.addRow("无效数量:", self._invalid_label)
        
        self._start_label = QLabel("-")
        stats_layout.addRow("开始日期:", self._start_label)
        
        self._end_label = QLabel("-")
        stats_layout.addRow("结束日期:", self._end_label)
        
        layout.addWidget(stats_group)
        
        # 扩展信息组
        self._extra_group = QGroupBox("扩展信息")
        self._extra_layout = QFormLayout(self._extra_group)
        layout.addWidget(self._extra_group)
        
        layout.addStretch()
    
    def show_metadata(self, metadata: Dict[str, Any]):
        """
        显示元数据
        
        Args:
            metadata: 元数据字典
        """
        self._current_metadata = metadata
        
        if not metadata:
            self._clear_display()
            return
        
        # 更新基本信息
        self._colname_label.setText(str(metadata.get('colname', '-')))
        self._hash_label.setText(str(metadata.get('colname_hash', '-')))
        self._type_label.setText(str(metadata.get('data_type', '-')))
        
        # 更新数据统计
        total = metadata.get('total_count', 0)
        invalid = metadata.get('invalid_count', 0)
        valid = total - invalid
        
        self._total_label.setText(str(total))
        self._valid_label.setText(str(valid))
        self._invalid_label.setText(str(invalid))
        
        self._start_label.setText(str(metadata.get('start_date', '-')))
        self._end_label.setText(str(metadata.get('end_date', '-')))
        
        # 更新扩展信息
        self._update_extra_info(metadata)
    
    def _update_extra_info(self, metadata: Dict[str, Any]):
        """更新扩展信息"""
        # 清除旧的扩展信息
        while self._extra_layout.count():
            item = self._extra_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 已知字段
        known_keys = {
            'colname', 'colname_hash', 'data_type',
            'total_count', 'invalid_count',
            'start_date', 'end_date',
            'level_0', 'level_1', 'level_2'
        }
        
        # 显示其他字段
        for key, value in metadata.items():
            if key not in known_keys:
                label = QLabel(str(value))
                label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self._extra_layout.addRow(f"{key}:", label)
    
    def _clear_display(self):
        """清除显示"""
        self._colname_label.setText("-")
        self._hash_label.setText("-")
        self._type_label.setText("-")
        self._total_label.setText("-")
        self._valid_label.setText("-")
        self._invalid_label.setText("-")
        self._start_label.setText("-")
        self._end_label.setText("-")
        
        # 清除扩展信息
        while self._extra_layout.count():
            item = self._extra_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def get_current_metadata(self) -> Optional[Dict]:
        """获取当前显示的元数据"""
        return self._current_metadata