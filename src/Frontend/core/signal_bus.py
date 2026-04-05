"""
信号总线模块

提供组件间的解耦通信机制，采用单例模式。
"""

from PyQt5.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """
    信号总线（单例模式）
    
    用于组件之间的解耦通信，避免直接依赖。
    """
    
    # ==================== 单例实现 ====================
    _instance = None
    
    @classmethod
    def instance(cls) -> 'SignalBus':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # ==================== 数据信号 ====================
    sigDataLoaded = pyqtSignal(str, object)     # (source, data)
    sigDataUpdated = pyqtSignal(str, object)    # (source, data)
    sigDataCleared = pyqtSignal(str)            # (source)
    
    # ==================== 选择信号 ====================
    sigColumnSelected = pyqtSignal(list)        # 列哈希列表
    sigDateRangeChanged = pyqtSignal(tuple)     # (start_date, end_date)
    sigCodeSelected = pyqtSignal(str)           # 代码
    
    # ==================== 图表信号 ====================
    sigChartRangeChanged = pyqtSignal(tuple)    # (x_min, x_max)
    sigCursorMoved = pyqtSignal(int, float)     # (index, value)
    sigChartZoomed = pyqtSignal(float)          # zoom_factor
    sigChartPanned = pyqtSignal(tuple)          # (dx, dy)
    
    # ==================== 交易信号 ====================
    sigTradeSelected = pyqtSignal(dict)         # 交易信息字典
    sigMarkerClicked = pyqtSignal(object)       # Marker 对象
    sigMarkerDoubleClicked = pyqtSignal(object) # Marker 对象
    
    # ==================== UI 信号 ====================
    sigThemeChanged = pyqtSignal(str)           # 主题名称
    sigLayoutChanged = pyqtSignal(str)          # 布局名称
    sigLanguageChanged = pyqtSignal(str)        # 语言代码
    
    # ==================== 状态信号 ====================
    sigStatusMessage = pyqtSignal(str, int)     # (message, timeout)
    sigProgressChanged = pyqtSignal(int)        # progress (0-100)
    sigErrorOccurred = pyqtSignal(str)          # error_message
    
    # ==================== 变量面板信号 ====================
    sigVariableAdded = pyqtSignal(str)          # 变量名（列哈希）
    sigVariableRemoved = pyqtSignal(str)        # 变量名
    sigVariableConfigChanged = pyqtSignal(str, object)  # (变量名, 配置)
    
    # ==================== 回测面板信号 ====================
    sigBacktestLoaded = pyqtSignal(object)      # 回测结果
    sigBacktestCleared = pyqtSignal()           # 清除回测
    
    def __init__(self):
        super().__init__()
        self._debug = False
    
    def set_debug(self, enabled: bool):
        """
        设置调试模式
        
        Args:
            enabled: 是否启用调试
        """
        self._debug = enabled
    
    def _emit_with_debug(self, signal, *args):
        """带调试信息的信号发送"""
        if self._debug:
            print(f"[SignalBus] Emitting: {signal} with args: {args}")
        signal.emit(*args)


# 全局便捷函数
def get_signal_bus() -> SignalBus:
    """获取信号总线实例"""
    return SignalBus.instance()