"""
Chart 模块测试用例
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Frontend.core import BarData, DataManager
from Frontend.chart.markers import MarkerManager, MarkerType, MarkerData, MarkerStyle
from Frontend.chart.overlays import ConfidenceBand, BandConfig, BandData


class TestMarkerManager(unittest.TestCase):
    """MarkerManager 测试"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = MarkerManager()
    
    def test_add_marker(self):
        """测试添加标记"""
        from Frontend.chart.markers import TradeMarker
        
        data = MarkerData(
            marker_type=MarkerType.BUY,
            x=10,
            y=100.0,
        )
        marker = TradeMarker(data)
        
        marker_id = self.manager.add_marker(marker)
        
        self.assertIsNotNone(marker_id)
        self.assertEqual(self.manager.get_marker_count(), 1)
        self.assertEqual(self.manager.get_marker(marker_id), marker)
    
    def test_remove_marker(self):
        """测试移除标记"""
        from Frontend.chart.markers import TradeMarker
        
        data = MarkerData(
            marker_type=MarkerType.SELL,
            x=20,
            y=105.0,
        )
        marker = TradeMarker(data)
        
        marker_id = self.manager.add_marker(marker)
        self.assertEqual(self.manager.get_marker_count(), 1)
        
        result = self.manager.remove_marker(marker_id)
        self.assertTrue(result)
        self.assertEqual(self.manager.get_marker_count(), 0)
    
    def test_get_markers_by_type(self):
        """测试按类型获取标记"""
        from Frontend.chart.markers import TradeMarker
        
        # 添加不同类型的标记
        buy_data = MarkerData(marker_type=MarkerType.BUY, x=10, y=100.0)
        sell_data = MarkerData(marker_type=MarkerType.SELL, x=20, y=105.0)
        
        self.manager.add_marker(TradeMarker(buy_data))
        self.manager.add_marker(TradeMarker(sell_data))
        
        buy_markers = self.manager.get_markers_by_type(MarkerType.BUY)
        self.assertEqual(len(buy_markers), 1)
    
    def test_get_markers_in_range(self):
        """测试获取范围内的标记"""
        from Frontend.chart.markers import TradeMarker
        
        # 添加不同位置的标记
        for i in range(5):
            data = MarkerData(marker_type=MarkerType.BUY, x=i*10, y=100.0)
            self.manager.add_marker(TradeMarker(data))
        
        markers = self.manager.get_markers_in_range(15, 35)
        self.assertEqual(len(markers), 2)  # x=20 和 x=30


class TestConfidenceBand(unittest.TestCase):
    """ConfidenceBand 测试"""
    
    def test_create_band(self):
        """测试创建置信区间带"""
        config = BandConfig()
        band = ConfidenceBand(config)
        
        self.assertIsNotNone(band)
    
    def test_set_data(self):
        """测试设置数据"""
        band = ConfidenceBand()
        
        data = [
            BandData(x=0, upper=105.0, lower=95.0, mid=100.0),
            BandData(x=1, upper=106.0, lower=96.0, mid=101.0),
            BandData(x=2, upper=107.0, lower=97.0, mid=102.0),
        ]
        
        band.set_data(data)
        
        y_min, y_max = band.get_y_range()
        self.assertEqual(y_min, 95.0)
        self.assertEqual(y_max, 107.0)
    
    def test_clear(self):
        """测试清除数据"""
        band = ConfidenceBand()
        
        data = [
            BandData(x=0, upper=105.0, lower=95.0, mid=100.0),
        ]
        
        band.set_data(data)
        band.clear()
        
        y_min, y_max = band.get_y_range()
        self.assertEqual(y_min, 0.0)
        self.assertEqual(y_max, 1.0)


class TestMarkerData(unittest.TestCase):
    """MarkerData 测试"""
    
    def test_create_marker_data(self):
        """测试创建标记数据"""
        data = MarkerData(
            marker_type=MarkerType.BUY,
            x=100,
            y=50.5,
            order_id="ORDER_001",
            strategy_name="TestStrategy",
            display_text="买入信号",
        )
        
        self.assertEqual(data.marker_type, MarkerType.BUY)
        self.assertEqual(data.x, 100)
        self.assertEqual(data.y, 50.5)
        self.assertEqual(data.order_id, "ORDER_001")
        self.assertEqual(data.strategy_name, "TestStrategy")
        self.assertEqual(data.display_text, "买入信号")
    
    def test_default_style(self):
        """测试默认样式"""
        data = MarkerData(
            marker_type=MarkerType.BUY,
            x=0,
            y=0,
        )
        
        self.assertIsNotNone(data.style)


class TestBandConfig(unittest.TestCase):
    """BandConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = BandConfig()
        
        self.assertEqual(config.fill_opacity, 0.3)
        self.assertEqual(config.line_width, 1.0)
        self.assertTrue(config.show_mid_line)
    
    def test_custom_config(self):
        """测试自定义配置"""
        from PyQt5.QtGui import QColor
        
        config = BandConfig(
            fill_color=QColor(255, 0, 0),
            fill_opacity=0.5,
            show_mid_line=False,
        )
        
        self.assertEqual(config.fill_opacity, 0.5)
        self.assertFalse(config.show_mid_line)


if __name__ == '__main__':
    unittest.main()