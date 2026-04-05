"""
交易列表模块

显示回测期间的交易记录列表。
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from PyQt5.QtCore import Qt, pyqtSignal, QModelIndex
from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, 
    QAbstractItemView, QWidget, QVBoxLayout, QLabel
)
from PyQt5.QtGui import QColor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))


@dataclass
class Trade:
    """交易记录数据结构"""
    index: int = 0              # 交易索引
    bar_index: int = 0          # K线索引
    action: str = ''            # 动作: buy, sell, stop_loss, take_profit
    price: float = 0.0          # 成交价格
    quantity: float = 0.0       # 成交数量
    timestamp: Any = None       # 时间戳
    pnl: float = 0.0            # 盈亏
    commission: float = 0.0     # 手续费
    
    # 兼容性别名 - 支持 notebook 中使用的字段名
    trade_id: str = ''          # 交易ID（兼容性别名，映射到 index）
    symbol: str = ''            # 交易标的
    volume: float = 0.0         # 成交数量（兼容性别名，映射到 quantity）
    
    def __post_init__(self):
        """初始化后处理 - 处理兼容性字段"""
        # 如果使用了 trade_id，自动设置 index（如果是数字）
        if self.trade_id and not self.index:
            try:
                self.index = int(self.trade_id.replace('T', ''))
            except ValueError:
                pass
        
        # volume 作为 quantity 的别名
        if self.volume and not self.quantity:
            self.quantity = self.volume
        elif self.quantity and not self.volume:
            self.volume = self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'index': self.index,
            'bar_index': self.bar_index,
            'action': self.action,
            'price': self.price,
            'quantity': self.quantity,
            'timestamp': self.timestamp,
            'pnl': self.pnl,
            'commission': self.commission,
            'trade_id': self.trade_id or str(self.index),
            'symbol': self.symbol,
            'volume': self.volume or self.quantity,
        }


class TradeList(QWidget):
    """
    交易列表控件
    
    功能：
    - 显示交易记录表格
    - 支持点击定位
    - 支持筛选（按类型）
    - 支持排序
    """
    
    sigTradeClicked = pyqtSignal(Trade)  # 点击交易信号
    sigTradeDoubleClicked = pyqtSignal(Trade)  # 双击交易信号
    
    # 表格列定义
    COLUMNS = [
        ('index', '序号', 60),
        ('action', '类型', 80),
        ('price', '价格', 100),
        ('quantity', '数量', 80),
        ('pnl', '盈亏', 100),
        ('commission', '手续费', 80),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._trades: List[Trade] = []
        self._filtered_trades: List[Trade] = []
        self._filter_type: Optional[str] = None
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 标题
        title = QLabel("交易记录")
        layout.addWidget(title)
        
        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels([col[1] for col in self.COLUMNS])
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        
        # 设置列宽
        header = self._table.horizontalHeader()
        for i, (_, _, width) in enumerate(self.COLUMNS):
            header.setSectionResizeMode(i, QHeaderView.Fixed)
            self._table.setColumnWidth(i, width)
        
        # 连接信号
        self._table.cellClicked.connect(self._on_cell_clicked)
        self._table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        
        layout.addWidget(self._table)
        
        # 统计标签
        self._stats_label = QLabel()
        layout.addWidget(self._stats_label)
    
    def set_trades(self, trades: List[Trade]):
        """设置交易列表"""
        self._trades = trades
        self._apply_filter()
        self._update_table()
        self._update_stats()
    
    def set_filter(self, action_type: Optional[str]):
        """设置筛选类型"""
        self._filter_type = action_type
        self._apply_filter()
        self._update_table()
    
    def _apply_filter(self):
        """应用筛选"""
        if self._filter_type is None:
            self._filtered_trades = self._trades.copy()
        else:
            self._filtered_trades = [
                t for t in self._trades if t.action == self._filter_type
            ]
    
    def _update_table(self):
        """更新表格"""
        self._table.setRowCount(len(self._filtered_trades))
        
        for row, trade in enumerate(self._filtered_trades):
            data = trade.to_dict()
            
            for col, (key, _, _) in enumerate(self.COLUMNS):
                value = data.get(key, '')
                
                item = QTableWidgetItem(str(value) if value is not None else '')
                item.setData(Qt.UserRole, trade)  # 存储交易对象
                
                # 设置颜色
                if key == 'action':
                    if value == 'buy':
                        item.setForeground(QColor(255, 75, 75))
                    elif value == 'sell':
                        item.setForeground(QColor(0, 255, 255))
                    elif value == 'stop_loss':
                        item.setForeground(QColor(255, 165, 0))
                    elif value == 'take_profit':
                        item.setForeground(QColor(255, 215, 0))
                
                elif key == 'pnl':
                    if value > 0:
                        item.setForeground(QColor(255, 75, 75))
                    elif value < 0:
                        item.setForeground(QColor(0, 255, 255))
                
                self._table.setItem(row, col, item)
    
    def _update_stats(self):
        """更新统计信息"""
        if not self._trades:
            self._stats_label.setText("无交易记录")
            return
        
        total_pnl = sum(t.pnl for t in self._trades)
        total_commission = sum(t.commission for t in self._trades)
        win_count = sum(1 for t in self._trades if t.pnl > 0)
        win_rate = win_count / len(self._trades) * 100 if self._trades else 0
        
        self._stats_label.setText(
            f"总交易: {len(self._trades)} | "
            f"胜率: {win_rate:.1f}% | "
            f"总盈亏: {total_pnl:.2f} | "
            f"总手续费: {total_commission:.2f}"
        )
    
    def _on_cell_clicked(self, row: int, col: int):
        """单元格点击"""
        item = self._table.item(row, 0)
        if item:
            trade = item.data(Qt.UserRole)
            self.sigTradeClicked.emit(trade)
    
    def _on_cell_double_clicked(self, row: int, col: int):
        """单元格双击"""
        item = self._table.item(row, 0)
        if item:
            trade = item.data(Qt.UserRole)
            self.sigTradeDoubleClicked.emit(trade)
    
    def highlight_trade(self, index: int):
        """高亮指定交易"""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item:
                trade = item.data(Qt.UserRole)
                if trade.index == index:
                    self._table.selectRow(row)
                    self._table.scrollToItem(item)
                    break
    
    def clear_trades(self):
        """清除交易列表"""
        self._trades.clear()
        self._filtered_trades.clear()
        self._table.setRowCount(0)
        self._stats_label.setText("无交易记录")