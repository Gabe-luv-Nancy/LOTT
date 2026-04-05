"""
列树形导航组件

三级列树形导航：代码-名称-指标
"""

from typing import Dict, List, Optional
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem


class ColumnTreeWidget(QTreeWidget):
    """
    列树形导航组件
    
    三级结构：
    - 代码 (level_0)
      - 名称 (level_1)
        - 指标 (level_2)
    
    信号：
    - sigSelectionChanged: 选择变化时发出，参数为列哈希列表
    """
    
    sigSelectionChanged = pyqtSignal(list)  # 列哈希列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._metadata: Optional[pd.DataFrame] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """设置 UI"""
        self.setHeaderLabels(['名称', '数据类型', '有效数据量'])
        self.setColumnCount(3)
        
        # 设置列宽
        self.setColumnWidth(0, 200)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 100)
        
        # 启用多选
        self.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
        # 连接信号
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def build_from_metadata(self, metadata_df: pd.DataFrame):
        """
        从元数据构建树
        
        Args:
            metadata_df: 元数据 DataFrame，包含以下列：
                - colname_hash: 列哈希
                - level_0: 代码
                - level_1: 名称
                - level_2: 指标
                - data_type: 数据类型
                - total_count: 总数量
                - invalid_count: 无效数量
        """
        self._metadata = metadata_df
        self.clear()
        
        if metadata_df is None or metadata_df.empty:
            return
        
        # 按三级结构构建树
        level_0_items: Dict[str, QTreeWidgetItem] = {}
        level_1_items: Dict[str, QTreeWidgetItem] = {}
        
        for _, row in metadata_df.iterrows():
            code = str(row.get('level_0', ''))
            name = str(row.get('level_1', ''))
            metric = str(row.get('level_2', ''))
            col_hash = str(row.get('colname_hash', ''))
            data_type = str(row.get('data_type', ''))
            total_count = row.get('total_count', 0)
            invalid_count = row.get('invalid_count', 0)
            
            # Level 0: 代码
            if code not in level_0_items:
                level_0_item = QTreeWidgetItem([code, '', ''])
                level_0_items[code] = level_0_item
                self.addTopLevelItem(level_0_item)
            
            # Level 1: 名称
            level_1_key = f"{code}_{name}"
            if level_1_key not in level_1_items:
                level_1_item = QTreeWidgetItem([name, '', ''])
                level_1_items[level_1_key] = level_1_item
                level_0_items[code].addChild(level_1_item)
            
            # Level 2: 指标
            valid_count = total_count - invalid_count
            level_2_item = QTreeWidgetItem([
                metric,
                data_type,
                str(valid_count)
            ])
            level_2_item.setData(0, Qt.ItemDataRole.UserRole, col_hash)
            level_1_items[level_1_key].addChild(level_2_item)
        
        self.expandAll()
    
    def get_selected_columns(self) -> List[str]:
        """
        获取选中的列哈希列表
        
        Returns:
            列哈希列表
        """
        selected = []
        for item in self.selectedItems():
            col_hash = item.data(0, Qt.ItemDataRole.UserRole)
            if col_hash:
                selected.append(col_hash)
        return selected
    
    def filter_by_code(self, code_pattern: str):
        """
        按代码筛选
        
        Args:
            code_pattern: 代码模式
        """
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            visible = code_pattern.lower() in item.text(0).lower()
            item.setHidden(not visible)
    
    def filter_by_name(self, name_pattern: str):
        """按名称筛选"""
        # 递归隐藏/显示
        pass
    
    def filter_by_metric(self, metric_pattern: str):
        """按指标筛选"""
        pass
    
    def _on_selection_changed(self):
        """选择变化处理"""
        selected = self.get_selected_columns()
        self.sigSelectionChanged.emit(selected)