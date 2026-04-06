"""
集成测试用例

测试模块之间的集成。
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestStylesIntegration(unittest.TestCase):
    """样式模块集成测试"""
    
    def test_theme_to_style(self):
        """测试主题转换为样式"""
        from Frontend.styles import Theme, ChartStyle, ColorScheme
        
        theme = Theme(name="TestTheme", scheme=ColorScheme.DARK)
        style = ChartStyle.from_theme(theme)
        
        self.assertEqual(style.name, "TestTheme")
        self.assertIsNotNone(style.candle)
        self.assertIsNotNone(style.volume)
    
    def test_theme_manager(self):
        """测试主题管理器"""
        from Frontend.styles import ThemeManager
        
        manager = ThemeManager()
        
        # 测试默认主题
        theme = manager.get_current_theme()
        self.assertIsNotNone(theme)
        
        # 测试切换主题
        result = manager.set_theme("light")
        self.assertTrue(result)
        
        theme = manager.get_current_theme()
        self.assertEqual(theme.name, "Light")


class TestChartItemsIntegration(unittest.TestCase):
    """图表元素集成测试"""
    
    def setUp(self):
        """测试前准备"""
        from Frontend.core import DataManager, BarData
        
        self.data_manager = DataManager()
        
        # 创建测试数据
        base_time = datetime(2024, 1, 1, 9, 30)
        for i in range(20):
            bar = BarData(
                datetime=base_time + timedelta(minutes=i),
                open=100.0 + i,
                high=105.0 + i,
                low=98.0 + i,
                close=103.0 + i,
                volume=10000 + i * 100,
            )
            self.data_manager.update_bar(bar)
    
    def test_candle_item_creation(self):
        """测试K线元素创建"""
        from Frontend.chart.items import CandleItem
        
        candle = CandleItem(self.data_manager)
        
        self.assertIsNotNone(candle)
        
        # 测试Y轴范围
        y_min, y_max = candle.get_y_range()
        self.assertLess(y_min, y_max)
    
    def test_bar_item_creation(self):
        """测试柱状图元素创建"""
        from Frontend.chart.items import BarItem
        
        bar_item = BarItem(self.data_manager, field='volume')
        
        self.assertIsNotNone(bar_item)
        
        # 测试Y轴范围
        y_min, y_max = bar_item.get_y_range()
        self.assertEqual(y_min, 0.0)
        self.assertLess(y_min, y_max)
    
    def test_line_item_creation(self):
        """测试折线元素创建"""
        from Frontend.chart.items import LineItem
        
        line = LineItem(self.data_manager, field='close')
        
        self.assertIsNotNone(line)
        
        # 测试Y轴范围
        y_min, y_max = line.get_y_range()
        self.assertLess(y_min, y_max)


class TestMarkerIntegration(unittest.TestCase):
    """标记系统集成测试"""
    
    def test_marker_with_style(self):
        """测试带样式的标记"""
        from Frontend.chart.markers import (
            TradeMarker, MarkerData, MarkerType, MarkerStyle, MarkerShape
        )
        
        style = MarkerStyle(
            shape=MarkerShape.TRIANGLE_UP,
            size=12.0,
            show_text=True,
        )
        
        data = MarkerData(
            marker_type=MarkerType.BUY,
            x=10,
            y=100.0,
            style=style,
            display_text="买入",
        )
        
        marker = TradeMarker(data)
        
        self.assertIsNotNone(marker)
        self.assertEqual(marker.x, 10)
        self.assertEqual(marker.y, 100.0)


class TestFullIntegration(unittest.TestCase):
    """完整集成测试"""
    
    def test_data_to_chart_flow(self):
        """测试数据到图表的完整流程"""
        from Frontend.core import DataManager, BarData
        from Frontend.chart.markers import MarkerManager, TradeMarker, MarkerData, MarkerType
        
        # 1. 创建数据管理器
        data_manager = DataManager()
        
        # 2. 添加数据
        base_time = datetime(2024, 1, 1, 9, 30)
        for i in range(50):
            bar = BarData(
                datetime=base_time + timedelta(minutes=i),
                open=100.0 + i * 0.5,
                high=105.0 + i * 0.5,
                low=98.0 + i * 0.5,
                close=103.0 + i * 0.5,
                volume=10000,
            )
            data_manager.update_bar(bar)
        
        # 3. 验证数据
        self.assertEqual(data_manager.get_count(), 50)
        
        # 4. 添加标记
        marker_manager = MarkerManager()
        
        buy_data = MarkerData(
            marker_type=MarkerType.BUY,
            x=10,
            y=103.0,
        )
        buy_marker = TradeMarker(buy_data)
        marker_manager.add_marker(buy_marker)
        
        sell_data = MarkerData(
            marker_type=MarkerType.SELL,
            x=40,
            y=123.0,
        )
        sell_marker = TradeMarker(sell_data)
        marker_manager.add_marker(sell_marker)
        
        # 5. 验证标记
        self.assertEqual(marker_manager.get_marker_count(), 2)
        
        buy_markers = marker_manager.get_markers_by_type(MarkerType.BUY)
        self.assertEqual(len(buy_markers), 1)
        
        # 6. 测试范围查询
        markers_in_range = marker_manager.get_markers_in_range(5, 15)
        self.assertEqual(len(markers_in_range), 1)


if __name__ == '__main__':
    unittest.main()

# ---------------------------------------------------------------------------
# 任务要求补充：仅测试 import，不运行 GUI
# ---------------------------------------------------------------------------

def test_import_all_panels():
    """三大 Panel 导入测试"""
    import sys
    sys.path.insert(0, '/mnt/x/LOTT/src/')
    from Frontend.panels.database.database_panel import DatabasePanel
    from Frontend.panels.variables.variable_panel import VariablePanel
    from Frontend.panels.backtest.backtest_panel import BacktestPanel
    assert all([DatabasePanel, VariablePanel, BacktestPanel])
