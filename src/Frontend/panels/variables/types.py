"""
变量面板类型定义
"""

from dataclasses import dataclass, field
from PyQt5.QtGui import QColor


@dataclass
class VariableConfig:
    """
    变量配置
    
    管理单个变量的显示和计算参数。
    
    字段：
        column_hash: 列哈希值（数据库列标识）
        display_name: 用户可读的显示名称
        color: 线条颜色
        lagging: 滞后阶数（0=原始数据）
        y_axis: Y轴位置（0=左, 1=右, 2=独立）
        line_style: 线型（0=实线, 1=虚线, 2=点线, 3=点划线）
        line_width: 线宽
        visible: 是否可见
        show_confidence_band: 是否显示置信区间
        confidence_level: 置信水平
    """
    column_hash: str = ""                  # 列哈希标识
    display_name: str = ""                 # 显示名称
    color: QColor = field(default_factory=lambda: QColor(255, 99, 132))
    lagging: int = 0                       # 滞后阶数
    y_axis: int = 0                        # Y轴（0=左, 1=右, 2=独立）
    line_style: int = 0                    # 线型（0=实线, 1=虚线, 2=点线, 3=点划线）
    line_width: float = 1.0                # 线宽
    visible: bool = True                   # 是否可见
    show_confidence_band: bool = False     # 是否显示置信区间
    confidence_level: float = 0.95         # 置信水平
