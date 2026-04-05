"""
信息面板模块

显示图表相关的详细信息。
"""

from typing import Optional
from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtGui import QFont, QColor

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from Frontend.core import BarData


class InfoPanel(QWidget):
    """
    信息面板
    
    功能：
    - 显示当前K线信息
    - 显示持仓信息
    - 显示策略信号信息
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._bar_data: Optional[BarData] = None
        self._additional_info: dict = {}
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        # 设置样式
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a2e;
                color: #ffffff;
            }
            QLabel {
                padding: 2px;
            }
        """)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # 标题
        title_label = QLabel("信息面板")
        title_label.setFont(QFont("Arial", 12, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; border-bottom: 1px solid #444; padding: 5px;")
        layout.addWidget(title_label)
        
        # K线信息区域
        self._bar_frame = self._create_section("K线信息")
        layout.addWidget(self._bar_frame)
        
        # K线信息标签
        self._time_label = self._create_info_label("时间: -")
        self._price_label = self._create_info_label("价格: -")
        self._ohlc_label = self._create_info_label("OHLC: -")
        self._volume_label = self._create_info_label("成交量: -")
        
        self._bar_frame.layout().addWidget(self._time_label)
        self._bar_frame.layout().addWidget(self._price_label)
        self._bar_frame.layout().addWidget(self._ohlc_label)
        self._bar_frame.layout().addWidget(self._volume_label)
        
        # 持仓信息区域
        self._position_frame = self._create_section("持仓信息")
        layout.addWidget(self._position_frame)
        
        self._pos_label = self._create_info_label("持仓: -")
        self._pnl_label = self._create_info_label("盈亏: -")
        self._entry_label = self._create_info_label("开仓价: -")
        
        self._position_frame.layout().addWidget(self._pos_label)
        self._position_frame.layout().addWidget(self._pnl_label)
        self._position_frame.layout().addWidget(self._entry_label)
        
        # 信号信息区域
        self._signal_frame = self._create_section("信号信息")
        layout.addWidget(self._signal_frame)
        
        self._signal_label = self._create_info_label("信号: -")
        self._confidence_label = self._create_info_label("置信度: -")
        
        self._signal_frame.layout().addWidget(self._signal_label)
        self._signal_frame.layout().addWidget(self._confidence_label)
        
        # 添加弹性空间
        layout.addStretch()
    
    def _create_section(self, title: str) -> QFrame:
        """创建信息区域"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #252540;
                border: 1px solid #3a3a5a;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        title_label.setStyleSheet("color: #8888ff; border: none;")
        layout.addWidget(title_label)
        
        return frame
    
    def _create_info_label(self, text: str) -> QLabel:
        """创建信息标签"""
        label = QLabel(text)
        label.setFont(QFont("Consolas", 9))
        label.setStyleSheet("color: #cccccc; border: none;")
        return label
    
    def update_bar_info(self, bar_data: BarData):
        """
        更新K线信息
        
        Args:
            bar_data: Bar数据
        """
        self._bar_data = bar_data
        
        if bar_data is None:
            self._time_label.setText("时间: -")
            self._price_label.setText("价格: -")
            self._ohlc_label.setText("OHLC: -")
            self._volume_label.setText("成交量: -")
            return
        
        # 更新时间
        self._time_label.setText(
            f"时间: {bar_data.datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # 更新价格
        self._price_label.setText(f"收盘: {bar_data.close:.2f}")
        
        # 更新OHLC
        self._ohlc_label.setText(
            f"开:{bar_data.open:.2f} 高:{bar_data.high:.2f} "
            f"低:{bar_data.low:.2f} 收:{bar_data.close:.2f}"
        )
        
        # 更新成交量
        volume = bar_data.volume
        if volume >= 1e8:
            volume_str = f"{volume/1e8:.2f}亿"
        elif volume >= 1e4:
            volume_str = f"{volume/1e4:.2f}万"
        else:
            volume_str = f"{volume:.0f}"
        self._volume_label.setText(f"成交量: {volume_str}")
        
        # 涨跌颜色
        if bar_data.close >= bar_data.open:
            self._price_label.setStyleSheet("color: #ff0000; border: none;")
        else:
            self._price_label.setStyleSheet("color: #00ff00; border: none;")
    
    def update_position_info(
        self,
        position: int = 0,
        avg_price: float = 0.0,
        pnl: float = 0.0,
        pnl_percent: float = 0.0,
    ):
        """
        更新持仓信息
        
        Args:
            position: 持仓数量
            avg_price: 平均价格
            pnl: 盈亏
            pnl_percent: 盈亏百分比
        """
        if position == 0:
            self._pos_label.setText("持仓: 空仓")
            self._pnl_label.setText("盈亏: -")
            self._entry_label.setText("开仓价: -")
        else:
            direction = "多" if position > 0 else "空"
            self._pos_label.setText(f"持仓: {direction} {abs(position)}")
            self._entry_label.setText(f"开仓价: {avg_price:.2f}")
            
            # 盈亏显示
            pnl_color = "#ff0000" if pnl >= 0 else "#00ff00"
            self._pnl_label.setText(
                f"盈亏: {pnl:.2f} ({pnl_percent:.2f}%)"
            )
            self._pnl_label.setStyleSheet(f"color: {pnl_color}; border: none;")
    
    def update_signal_info(
        self,
        signal: str = "-",
        confidence: float = 0.0,
        strategy: str = "-",
    ):
        """
        更新信号信息
        
        Args:
            signal: 信号类型
            confidence: 置信度
            strategy: 策略名称
        """
        self._signal_label.setText(f"信号: {signal}")
        self._confidence_label.setText(f"置信度: {confidence*100:.1f}%")
        
        # 信号颜色
        if signal.lower() in ['buy', 'long']:
            self._signal_label.setStyleSheet("color: #ff0000; border: none;")
        elif signal.lower() in ['sell', 'short']:
            self._signal_label.setStyleSheet("color: #00ff00; border: none;")
        else:
            self._signal_label.setStyleSheet("color: #cccccc; border: none;")
    
    def clear(self):
        """清除所有信息"""
        self.update_bar_info(None)
        self.update_position_info()
        self.update_signal_info()