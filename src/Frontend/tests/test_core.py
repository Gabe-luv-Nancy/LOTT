"""
Core 模块测试用例
"""

import unittest
from datetime import datetime, timedelta
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Frontend.core import BarData, DataManager, SignalBus, FrontendConfig


class TestBarData(unittest.TestCase):
    """BarData 测试"""
    
    def test_create_bar_data(self):
        """测试创建 BarData"""
        bar = BarData(
            datetime=datetime(2024, 1, 1, 10, 0),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=10000,
        )
        
        self.assertEqual(bar.open, 100.0)
        self.assertEqual(bar.high, 105.0)
        self.assertEqual(bar.low, 98.0)
        self.assertEqual(bar.close, 103.0)
        self.assertEqual(bar.volume, 10000)
    
    def test_bar_is_up(self):
        """测试涨跌判断"""
        up_bar = BarData(
            datetime=datetime.now(),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=10000,
        )
        self.assertTrue(up_bar.close >= up_bar.open)
        
        down_bar = BarData(
            datetime=datetime.now(),
            open=105.0,
            high=105.0,
            low=98.0,
            close=100.0,
            volume=10000,
        )
        self.assertTrue(down_bar.close < down_bar.open)


class TestDataManager(unittest.TestCase):
    """DataManager 测试"""
    
    def setUp(self):
        """测试前准备"""
        self.manager = DataManager()
        
        # 创建测试数据
        self.test_bars = []
        base_time = datetime(2024, 1, 1, 9, 30)
        for i in range(10):
            bar = BarData(
                datetime=base_time + timedelta(minutes=i),
                open=100.0 + i,
                high=105.0 + i,
                low=98.0 + i,
                close=103.0 + i,
                volume=10000 + i * 100,
            )
            self.test_bars.append(bar)
    
    def test_update_bar(self):
        """测试更新单个 Bar"""
        bar = self.test_bars[0]
        self.manager.update_bar(bar)
        
        self.assertEqual(self.manager.get_count(), 1)
        self.assertEqual(self.manager.get_bar(0), bar)
    
    def test_update_history(self):
        """测试批量更新历史数据"""
        self.manager.update_history(self.test_bars)
        
        self.assertEqual(self.manager.get_count(), 10)
    
    def test_get_bars(self):
        """测试获取范围"""
        self.manager.update_history(self.test_bars)
        
        bars = self.manager.get_bars(2, 5)
        self.assertEqual(len(bars), 3)
        self.assertEqual(bars[0], self.test_bars[2])
    
    def test_get_price_range(self):
        """测试价格范围"""
        self.manager.update_history(self.test_bars)
        
        low, high = self.manager.get_price_range()
        self.assertEqual(low, 98.0)  # 第一个 bar 的 low
        self.assertEqual(high, 114.0)  # 最后一个 bar 的 high
    
    def test_get_index(self):
        """测试索引获取"""
        self.manager.update_history(self.test_bars)
        
        index = self.manager.get_index(self.test_bars[5].datetime)
        self.assertEqual(index, 5)
    
    def test_clear_all(self):
        """测试清除"""
        self.manager.update_history(self.test_bars)
        
        self.manager.clear_all()
        self.assertEqual(self.manager.get_count(), 0)


class TestSignalBus(unittest.TestCase):
    """SignalBus 测试"""
    
    def setUp(self):
        """测试前准备"""
        self.bus = SignalBus()
        self.received_signals = []
    
    def _on_signal(self, signal_type, data):
        """信号处理"""
        self.received_signals.append((signal_type, data))
    
    def test_signal_bus_creation(self):
        """测试信号总线创建"""
        self.assertIsNotNone(self.bus)


class TestFrontendConfig(unittest.TestCase):
    """FrontendConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        # 重置单例以进行测试
        FrontendConfig._instance = None
        config = FrontendConfig()
        
        self.assertEqual(config.get('theme.name'), "dark")
        self.assertEqual(config.get('chart.min_bar_count'), 50)
        self.assertEqual(config.get('chart.max_bar_count'), 1000)
    
    def test_config_get_set(self):
        """测试配置读写"""
        FrontendConfig._instance = None
        config = FrontendConfig()
        
        # 测试设置值
        config.set('theme.name', 'light')
        self.assertEqual(config.get('theme.name'), 'light')
        
        # 测试设置新值
        config.set('custom.value', 123)
        self.assertEqual(config.get('custom.value'), 123)
    
    def test_get_section(self):
        """测试获取配置节"""
        FrontendConfig._instance = None
        config = FrontendConfig()
        
        chart_config = config.get_section('chart')
        self.assertIsNotNone(chart_config)
        self.assertIn('min_bar_count', chart_config)


if __name__ == '__main__':
    unittest.main()

# ---------------------------------------------------------------------------
# 任务要求补充：仅测试 import，不运行 GUI
# ---------------------------------------------------------------------------

def test_signal_bus_import():
    """SignalBus 导入测试"""
    import sys
    sys.path.insert(0, '/mnt/x/LOTT/src/')
    from Frontend.core.signal_bus import SignalBus
    assert SignalBus is not None


def test_data_proxy_import():
    """DataProxy 导入测试"""
    import sys
    sys.path.insert(0, '/mnt/x/LOTT/src/')
    from Frontend.core.data_proxy import DataProxy
    assert DataProxy is not None
