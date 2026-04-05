"""
数据缓存模块

提供内存缓存管理，提高数据访问效率。
支持 LRU 淘汰策略、TTL 过期、线程安全。

用法：
    from Service.cache import DataCache
    
    cache = DataCache(max_size=1000, default_ttl=3600)
    cache.set('prices_2024', df, ttl=7200)
    cached_df = cache.get('prices_2024')
    stats = cache.get_stats()
"""

import sys
sys.path.append('X:/LOTT/src/Cross_Layer')
from global_imports import *

from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta


class DataCache:
    """
    数据缓存管理器
    
    功能:
        - 内存缓存管理
        - TTL (Time To Live) 支持
        - LRU (Least Recently Used) 淘汰策略
        - 线程安全
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = Lock()
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键名
            
        Returns:
            缓存的数据，如果不存在或已过期则返回 None
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if self._is_expired(entry):
                del self._cache[key]
                self._misses += 1
                return None
            
            # LRU: 移到末尾（最近使用）
            self._cache.move_to_end(key)
            self._hits += 1
            
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键名
            value: 要缓存的数据
            ttl: 过期时间（秒），None 使用默认值
        """
        with self._lock:
            # 如果键已存在，先删除
            if key in self._cache:
                del self._cache[key]
            
            # 检查是否需要淘汰
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # 删除最旧的
                self._evictions += 1
            
            # 添加新条目
            expire_time = datetime.now() + timedelta(seconds=ttl or self._default_ttl)
            self._cache[key] = {
                'value': value,
                'expire_time': expire_time
            }
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键名
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            # 重置统计
            self._hits = 0
            self._misses = 0
            self._evictions = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            包含命中率、大小等统计信息的字典
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0
            
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': hit_rate,
                'usage_percent': len(self._cache) / self._max_size * 100 if self._max_size > 0 else 0
            }
    
    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在且未过期
        
        Args:
            key: 缓存键名
            
        Returns:
            是否存在有效缓存
        """
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if self._is_expired(entry):
                del self._cache[key]
                return False
            
            return True
    
    def get_or_set(self, key: str, factory: Callable, ttl: Optional[int] = None) -> Any:
        """
        获取缓存，如果不存在则通过工厂函数创建并缓存
        
        Args:
            key: 缓存键名
            factory: 数据工厂函数
            ttl: 过期时间（秒）
            
        Returns:
            缓存的数据或新创建的数据
        """
        value = self.get(key)
        if value is not None:
            return value
        
        value = factory()
        self.set(key, value, ttl)
        return value
    
    def _is_expired(self, entry: Dict) -> bool:
        """检查缓存条目是否过期"""
        return datetime.now() > entry['expire_time']
    
    def cleanup_expired(self) -> int:
        """
        清理所有过期的缓存条目
        
        Returns:
            清理的条目数量
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def get_many(self, keys: list) -> Dict[str, Any]:
        """
        批量获取缓存
        
        Args:
            keys: 缓存键名列表
            
        Returns:
            键值对字典（不包含不存在或过期的键）
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result
    
    def set_many(self, items: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """
        批量设置缓存
        
        Args:
            items: 键值对字典
            ttl: 过期时间（秒）
        """
        for key, value in items.items():
            self.set(key, value, ttl)
    
    def delete_many(self, keys: list) -> int:
        """
        批量删除缓存
        
        Args:
            keys: 缓存键名列表
            
        Returns:
            成功删除的数量
        """
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count
    
    def get_size_info(self) -> Dict[str, Any]:
        """
        获取缓存大小信息
        
        Returns:
            包含条目数、内存使用等信息的字典
        """
        import sys
        
        with self._lock:
            total_size = 0
            for key, entry in self._cache.items():
                try:
                    total_size += sys.getsizeof(key) + sys.getsizeof(entry)
                except:
                    pass
            
            return {
                'entry_count': len(self._cache),
                'max_size': self._max_size,
                'estimated_memory_bytes': total_size,
                'estimated_memory_mb': total_size / (1024 * 1024)
            }
    
    def __len__(self) -> int:
        """返回当前缓存大小"""
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """支持 'key in cache' 语法"""
        return self.exists(key)
    
    def __repr__(self) -> str:
        return f"DataCache(size={len(self._cache)}/{self._max_size}, hit_rate={self.get_stats()['hit_rate']:.2%})"


# 全局缓存实例（单例模式）
_global_cache: Optional[DataCache] = None


def get_cache(max_size: int = 1000, default_ttl: int = 3600) -> DataCache:
    """
    获取全局缓存实例
    
    Args:
        max_size: 最大缓存条目数
        default_ttl: 默认过期时间（秒）
        
    Returns:
        DataCache 实例
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = DataCache(max_size=max_size, default_ttl=default_ttl)
    return _global_cache


def cache_get(key: str) -> Optional[Any]:
    """快捷函数：从全局缓存获取数据"""
    return get_cache().get(key)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """快捷函数：设置全局缓存"""
    get_cache().set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """快捷函数：删除全局缓存"""
    return get_cache().delete(key)


def cache_clear() -> None:
    """快捷函数：清空全局缓存"""
    get_cache().clear()


def cache_stats() -> Dict[str, Any]:
    """快捷函数：获取全局缓存统计"""
    return get_cache().get_stats()