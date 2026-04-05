"""
数据库面板模块

图层1：数据库总表面板
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QToolBar,
    QLabel, QDateEdit, QPushButton
)

from ..base_panel import BasePanel
from .column_tree import ColumnTreeWidget
from .metadata_view import MetadataViewWidget
from .table_view import TableViewWidget

if TYPE_CHECKING:
    from Data.DataManager import DataOperation


class DatabasePanel(BasePanel):
    """
    数据库总表面板（图层1）
    
    功能：
    - 查看可获取的数据库总表
    - 查看数据库元数据表（MetaColData）
    - 列树形导航（三级索引：代码-名称-指标）
    - 数据预览
    - 日期范围选择
    
    信号：
    - sigColumnSelected: 选中的列哈希列表
    - sigDateRangeSelected: 日期范围变化
    - sigCodeSelected: 代码选择变化
    """
    
    sigColumnSelected = pyqtSignal(list)      # 选中的列哈希列表
    sigDateRangeSelected = pyqtSignal(tuple)  # (start_date, end_date)
    sigCodeSelected = pyqtSignal(str)         # 代码
    
    def __init__(self, data_operation: 'DataOperation' = None, parent=None):
        """
        初始化数据库面板
        
        Args:
            data_operation: 数据操作实例
            parent: 父窗口
        """
        self._data_op = data_operation
        self._metadata_df = None
        super().__init__("数据库总表", parent)
    
    def _init_ui(self):
        """初始化 UI"""
        # 主容器
        main_widget = QWidget()
        self.setWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 顶部工具栏
        toolbar = QToolBar()
        toolbar.addAction("刷新", self._refresh_data)
        toolbar.addAction("筛选", self._show_filter_dialog)
        layout.addWidget(toolbar)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 上部：列树形导航
        self._column_tree = ColumnTreeWidget()
        self._column_tree.sigSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._column_tree)
        
        # 下部：元数据详情
        self._metadata_view = MetadataViewWidget()
        splitter.addWidget(self._metadata_view)
        
        # 数据预览
        self._table_view = TableViewWidget()
        splitter.addWidget(self._table_view)
        
        # 设置分割比例
        splitter.setSizes([300, 200, 200])
        
        layout.addWidget(splitter, stretch=1)
        
        # 底部：日期范围选择
        date_widget = QWidget()
        date_layout = QHBoxLayout(date_widget)
        date_layout.setContentsMargins(5, 5, 5, 5)
        
        date_layout.addWidget(QLabel("开始:"))
        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setDateTime(datetime.now())
        date_layout.addWidget(self._start_date)
        
        date_layout.addWidget(QLabel("结束:"))
        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setDateTime(datetime.now())
        date_layout.addWidget(self._end_date)
        
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self._on_date_range_changed)
        date_layout.addWidget(apply_btn)
        
        date_layout.addStretch()
        layout.addWidget(date_widget)
    
    def set_data_operation(self, data_operation: 'DataOperation'):
        """
        设置数据操作实例
        
        Args:
            data_operation: 数据操作实例
        """
        self._data_op = data_operation
    
    def load_database_info(self):
        """加载数据库信息"""
        if self._data_op is None:
            return
        
        # 获取元数据
        try:
            if hasattr(self._data_op, 'get_column_info'):
                self._metadata_df = self._data_op.get_column_info()
                self._column_tree.build_from_metadata(self._metadata_df)
        except Exception as e:
            print(f"加载数据库信息失败: {e}")
    
    def load_metadata(self, col_hash: str) -> Dict[str, Any]:
        """
        加载指定列的元数据
        
        Args:
            col_hash: 列哈希值
            
        Returns:
            元数据字典
        """
        if self._metadata_df is None:
            return {}
        
        # 查找元数据
        mask = self._metadata_df['colname_hash'] == col_hash
        if mask.any():
            return self._metadata_df[mask].iloc[0].to_dict()
        return {}
    
    def get_selected_columns(self) -> List[str]:
        """获取选中的列哈希列表"""
        return self._column_tree.get_selected_columns()
    
    def get_date_range(self) -> Tuple[datetime, datetime]:
        """获取选中的日期范围"""
        start = self._start_date.dateTime().toPyDateTime()
        end = self._end_date.dateTime().toPyDateTime()
        return (start, end)
    
    def set_date_range(self, start: datetime, end: datetime):
        """设置日期范围"""
        self._start_date.setDateTime(start)
        self._end_date.setDateTime(end)
    
    def _on_selection_changed(self, selected: List[str]):
        """选择变化处理"""
        if selected:
            # 显示第一个选中列的元数据
            metadata = self.load_metadata(selected[0])
            self._metadata_view.show_metadata(metadata)
            
            # 加载数据预览
            self._load_data_preview(selected[0])
        
        self.sigColumnSelected.emit(selected)
    
    def _load_data_preview(self, col_hash: str):
        """加载数据预览"""
        if self._data_op is None:
            return
        
        try:
            start, end = self.get_date_range()
            if hasattr(self._data_op, 'get_column_data'):
                data = self._data_op.get_column_data(col_hash, start, end)
                if data is not None:
                    import pandas as pd
                    df = pd.DataFrame({'value': data})
                    self._table_view.show_data(df)
        except Exception as e:
            print(f"加载数据预览失败: {e}")
    
    def _on_date_range_changed(self):
        """日期范围变化处理"""
        start, end = self.get_date_range()
        self.sigDateRangeSelected.emit((start, end))
        
        # 刷新数据预览
        selected = self.get_selected_columns()
        if selected:
            self._load_data_preview(selected[0])
    
    def _refresh_data(self):
        """刷新数据"""
        self.load_database_info()
    
    def _show_filter_dialog(self):
        """显示筛选对话框"""
        # TODO: 实现筛选对话框
        pass
    
    def refresh(self):
        """刷新面板"""
        self.load_database_info()