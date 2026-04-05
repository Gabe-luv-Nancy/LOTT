"""
回测面板模块

整合价格图表、仓位图表、收益率图表和交易列表的完整回测结果面板。
"""

from typing import List, Optional
from dataclasses import dataclass
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QLabel, QSplitter, QCheckBox
)
from PyQt5.QtGui import QColor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from Frontend.core import DataManager, BarData
from .price_chart import PriceChart
from .position_chart import PositionChart
from .return_chart import ReturnChart
from .trade_list import TradeList, Trade
from Frontend.chart.markers import TradeMarker, MarkerData, MarkerType


@dataclass
class BacktestResult:
    """回测结果数据结构"""
    price_history: List[BarData]     # 价格历史
    positions: List[float]           # 仓位历史
    returns: List[float]             # 收益率历史
    trades: List[Trade]              # 交易记录
    benchmark_returns: List[float] = None  # 基准收益
    
    # 统计指标
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0


class BacktestPanel(QDockWidget):
    """
    回测结果面板
    
    功能：
    - 价格图表（含交易标记）
    - 仓位图表
    - 收益率图表
    - 交易列表
    - X轴联动
    """
    
    sigTradeSelected = pyqtSignal(dict)  # 选中交易
    sigTimeRangeChanged = pyqtSignal(tuple)  # 时间范围变化
    
    def __init__(self, parent=None):
        super().__init__("回测结果", parent)
        
        self._result: Optional[BacktestResult] = None
        
        self._init_ui()
        self._init_connections()
    
    def _init_ui(self):
        """初始化UI"""
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | 
            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea
        )
        
        # 主容器
        main_widget = QWidget()
        self.setWidget(main_widget)
        
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 顶部工具栏
        toolbar = QToolBar()
        toolbar.addAction("导出图表", self._export_chart)
        toolbar.addAction("导出数据", self._export_data)
        toolbar.addSeparator()
        
        # 显示选项
        self._show_position_check = QCheckBox("显示仓位")
        self._show_position_check.setChecked(True)
        toolbar.addWidget(self._show_position_check)
        
        self._show_return_check = QCheckBox("显示收益率")
        self._show_return_check.setChecked(True)
        toolbar.addWidget(self._show_return_check)
        
        self._show_trades_check = QCheckBox("显示交易标记")
        self._show_trades_check.setChecked(True)
        toolbar.addWidget(self._show_trades_check)
        
        layout.addWidget(toolbar)
        
        # 分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 价格图表
        self._price_chart = PriceChart()
        splitter.addWidget(self._price_chart)
        
        # 仓位图表
        self._position_chart = PositionChart()
        splitter.addWidget(self._position_chart)
        
        # 收益率图表
        self._return_chart = ReturnChart()
        splitter.addWidget(self._return_chart)
        
        # 交易列表
        self._trade_list = TradeList()
        self._trade_list.setMaximumHeight(180)
        splitter.addWidget(self._trade_list)
        
        # 设置分割比例
        splitter.setSizes([300, 100, 100, 150])
        
        layout.addWidget(splitter, stretch=1)
        
        # 状态栏
        self._status_label = QLabel()
        layout.addWidget(self._status_label)
        
        # 连接显示选项
        self._show_position_check.stateChanged.connect(
            lambda s: self._position_chart.setVisible(s == Qt.Checked)
        )
        self._show_return_check.stateChanged.connect(
            lambda s: self._return_chart.setVisible(s == Qt.Checked)
        )
        self._show_trades_check.stateChanged.connect(
            lambda s: self._price_chart.set_show_markers(s == Qt.Checked)
        )
    
    def _init_connections(self):
        """初始化信号连接"""
        # 交易列表点击 -> 图表定位
        self._trade_list.sigTradeClicked.connect(self._on_trade_clicked)
        
        # 价格图表范围变化 -> 联动其他图表
        self._price_chart.sigRangeChanged.connect(self._on_price_range_changed)
    
    def load_backtest_result(self, result: BacktestResult):
        """加载回测结果"""
        self._result = result
        
        # 加载价格数据
        self._price_chart.load_price_data(result.price_history)
        
        # 添加交易标记
        self._add_trade_markers(result.trades)
        
        # 加载仓位数据
        self._position_chart.load_positions(result.positions)
        
        # 加载收益率数据
        self._return_chart.load_returns(result.returns, result.benchmark_returns)
        
        # 更新交易列表
        self._trade_list.set_trades(result.trades)
        
        # 更新状态
        self._update_status()
    
    def _add_trade_markers(self, trades: List[Trade]):
        """添加交易标记"""
        self._price_chart.clear_trade_markers()
        
        for trade in trades:
            # 根据交易类型创建标记
            marker_type = self._get_marker_type(trade.action)
            
            marker_data = MarkerData(
                marker_type=marker_type,
                x=trade.bar_index,
                y=trade.price,
                display_text=f"{trade.action}\n{trade.price:.2f}",
            )
            
            marker = TradeMarker(marker_data)
            self._price_chart.add_trade_marker(marker)
    
    def _get_marker_type(self, action: str) -> MarkerType:
        """获取标记类型"""
        mapping = {
            'buy': MarkerType.BUY,
            'sell': MarkerType.SELL,
            'stop_loss': MarkerType.STOP_LOSS,
            'take_profit': MarkerType.TAKE_PROFIT,
        }
        return mapping.get(action, MarkerType.CUSTOM)
    
    def _on_trade_clicked(self, trade: Trade):
        """交易点击处理"""
        # 移动图表到交易位置
        self._price_chart.move_to_index(trade.bar_index)
        self.sigTradeSelected.emit(trade.to_dict())
    
    def _on_price_range_changed(self, range_tuple):
        """价格图表范围变化处理"""
        self.sigTimeRangeChanged.emit(range_tuple)
    
    def _update_status(self):
        """更新状态栏"""
        if self._result:
            self._status_label.setText(
                f"总收益率: {self._result.total_return:.2%} | "
                f"夏普比率: {self._result.sharpe_ratio:.2f} | "
                f"最大回撤: {self._result.max_drawdown:.2%} | "
                f"胜率: {self._result.win_rate:.2%}"
            )
        else:
            self._status_label.setText("未加载回测结果")
    
    def _export_chart(self):
        """导出图表为 PNG"""
        from PyQt5.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出图表", "backtest_chart.png",
            "PNG 图片 (*.png);;所有文件 (*)"
        )
        if filepath:
            try:
                from Frontend.utils.export_utils import export_chart_png
                export_chart_png(self._price_chart, filepath)
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "导出失败", f"图表导出失败: {e}")
    
    def _export_data(self):
        """导出回测数据为 CSV"""
        if self._result is None:
            return
        
        from PyQt5.QtWidgets import QFileDialog
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "backtest_data.csv",
            "CSV 文件 (*.csv);;所有文件 (*)"
        )
        if filepath:
            try:
                import pandas as pd
                data = {
                    'positions': self._result.positions,
                    'returns': self._result.returns,
                }
                df = pd.DataFrame(data)
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "导出失败", f"数据导出失败: {e}")
    
    def clear(self):
        """清除所有数据"""
        self._result = None
        self._price_chart.clear_trade_markers()
        self._position_chart.clear_data()
        self._return_chart.clear_data()
        self._trade_list.clear_trades()
        self._status_label.setText("未加载回测结果")