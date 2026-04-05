"""
标记管理器模块

管理所有标记的创建、删除、更新和查询。
"""

from typing import Dict, List, Optional
import uuid

from .base_marker import BaseMarker, MarkerType
from .trade_marker import TradeMarker


class MarkerManager:
    """
    标记管理器
    
    功能：
    - 管理标记生命周期
    - 支持按类型/策略/时间筛选
    - 维护索引以优化查询
    """
    
    def __init__(self):
        self._markers: Dict[str, BaseMarker] = {}      # id -> marker
        self._type_index: Dict[MarkerType, List[str]] = {}  # 类型索引
        self._strategy_index: Dict[str, List[str]] = {}     # 策略索引
        self._time_index: List[tuple] = []                   # 时间索引 (x, marker_id)
    
    def add_marker(self, marker: BaseMarker) -> str:
        """
        添加标记
        
        Args:
            marker: 标记对象
            
        Returns:
            标记ID
        """
        # 生成唯一ID
        marker_id = str(uuid.uuid4())
        
        # 存储标记
        self._markers[marker_id] = marker
        
        # 更新类型索引
        marker_type = marker.marker_type
        if marker_type not in self._type_index:
            self._type_index[marker_type] = []
        self._type_index[marker_type].append(marker_id)
        
        # 更新策略索引
        strategy_name = marker.data.strategy_name
        if strategy_name:
            if strategy_name not in self._strategy_index:
                self._strategy_index[strategy_name] = []
            self._strategy_index[strategy_name].append(marker_id)
        
        # 更新时间索引
        self._time_index.append((marker.x, marker_id))
        self._time_index.sort(key=lambda x: x[0])
        
        return marker_id
    
    def remove_marker(self, marker_id: str) -> bool:
        """
        移除标记
        
        Args:
            marker_id: 标记ID
            
        Returns:
            是否成功
        """
        if marker_id not in self._markers:
            return False
        
        marker = self._markers[marker_id]
        
        # 从类型索引中移除
        marker_type = marker.marker_type
        if marker_type in self._type_index:
            if marker_id in self._type_index[marker_type]:
                self._type_index[marker_type].remove(marker_id)
        
        # 从策略索引中移除
        strategy_name = marker.data.strategy_name
        if strategy_name and strategy_name in self._strategy_index:
            if marker_id in self._strategy_index[strategy_name]:
                self._strategy_index[strategy_name].remove(marker_id)
        
        # 从时间索引中移除
        self._time_index = [(x, mid) for x, mid in self._time_index if mid != marker_id]
        
        # 从主存储中移除
        del self._markers[marker_id]
        
        return True
    
    def get_marker(self, marker_id: str) -> Optional[BaseMarker]:
        """获取标记"""
        return self._markers.get(marker_id)
    
    def get_markers_by_type(self, marker_type: MarkerType) -> List[BaseMarker]:
        """按类型获取标记"""
        marker_ids = self._type_index.get(marker_type, [])
        return [self._markers[mid] for mid in marker_ids if mid in self._markers]
    
    def get_markers_by_strategy(self, strategy_name: str) -> List[BaseMarker]:
        """按策略获取标记"""
        marker_ids = self._strategy_index.get(strategy_name, [])
        return [self._markers[mid] for mid in marker_ids if mid in self._markers]
    
    def get_markers_in_range(self, x_min: int, x_max: int) -> List[BaseMarker]:
        """获取时间范围内的标记"""
        result = []
        for x, marker_id in self._time_index:
            if x_min <= x <= x_max:
                if marker_id in self._markers:
                    result.append(self._markers[marker_id])
        return result
    
    def clear_all(self):
        """清除所有标记"""
        self._markers.clear()
        self._type_index.clear()
        self._strategy_index.clear()
        self._time_index.clear()
    
    def get_all_markers(self) -> List[BaseMarker]:
        """获取所有标记"""
        return list(self._markers.values())
    
    def get_marker_count(self) -> int:
        """获取标记数量"""
        return len(self._markers)
    
    def get_marker_count_by_type(self, marker_type: MarkerType) -> int:
        """按类型获取标记数量"""
        return len(self._type_index.get(marker_type, []))
    
    def update_indices(self):
        """更新所有索引"""
        # 重建类型索引
        self._type_index.clear()
        for marker_id, marker in self._markers.items():
            marker_type = marker.marker_type
            if marker_type not in self._type_index:
                self._type_index[marker_type] = []
            self._type_index[marker_type].append(marker_id)
        
        # 重建策略索引
        self._strategy_index.clear()
        for marker_id, marker in self._markers.items():
            strategy_name = marker.data.strategy_name
            if strategy_name:
                if strategy_name not in self._strategy_index:
                    self._strategy_index[strategy_name] = []
                self._strategy_index[strategy_name].append(marker_id)
        
        # 重建时间索引
        self._time_index = [(marker.x, mid) for mid, marker in self._markers.items()]
        self._time_index.sort(key=lambda x: x[0])
    
    # ==================== 兼容性别名方法 ====================
    
    def get_count(self) -> int:
        """获取标记数量（兼容性别名）"""
        return self.get_marker_count()
