"""
表格视图组件

数据预览表格
"""

from typing import Optional
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView
from PyQt5.QtGui import QStandardItemModel, QStandardItem


class TableViewWidget(QWidget):
    """
    表格视图组件
    
    显示数据预览
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_data: Optional[pd.DataFrame] = None
        self._init_ui()
    
    def _init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._table = QTableView()
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # 创建空模型
        self._model = QStandardItemModel()
        self._table.setModel(self._model)
        
        layout.addWidget(self._table)
    
    def show_data(self, data: pd.DataFrame, max_rows: int = 1000):
        """
        显示数据
        
        Args:
            data: DataFrame 数据
            max_rows: 最大显示行数
        """
        self._current_data = data
        
        if data is None or data.empty:
            self._clear_display()
            return
        
        # 限制行数
        if len(data) > max_rows:
            data = data.head(max_rows)
        
        # 设置模型
        self._model.clear()
        self._model.setHorizontalHeaderLabels(list(data.columns))
        
        for i, row in data.iterrows():
            items = []
            for value in row:
                item = QStandardItem(str(value))
                item.setEditable(False)
                items.append(item)
            self._model.appendRow(items)
        
        # 调整列宽
        self._table.horizontalHeader().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
    
    def _clear_display(self):
        """清除显示"""
        self._model.clear()
    
    def get_current_data(self) -> Optional[pd.DataFrame]:
        """获取当前显示的数据"""
        return self._current_data