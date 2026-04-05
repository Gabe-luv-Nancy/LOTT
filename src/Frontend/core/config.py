"""
全局配置模块

管理 Frontend 的全局配置，包括数据库连接、主题、图表参数等。
"""

from typing import Any, Dict, Optional
import json
import os


class FrontendConfig:
    """
    Frontend 全局配置
    
    职责：
    - 管理默认配置
    - 支持配置文件加载/保存
    - 提供配置访问接口
    """
    
    # 默认配置
    DEFAULT_CONFIG = {
        # 数据库配置
        'database': {
            'type': 'sqlite',
            'path': 'X:/LOTT/src/Data/DataSource/_db/data.db',
        },
        
        # 图表配置
        'chart': {
            'min_bar_count': 50,        # 最小显示 Bar 数量
            'max_bar_count': 1000,      # 最大显示 Bar 数量
            'default_bar_count': 200,   # 默认显示 Bar 数量
            'animation_enabled': True,  # 是否启用动画
            'downsampling': True,       # 是否启用降采样
        },
        
        # 主题配置
        'theme': {
            'name': 'dark',             # 主题名称
            'font_family': 'Microsoft YaHei',  # 字体
            'font_size': 9,             # 字体大小
        },
        
        # 标记配置
        'marker': {
            'default_size': 10,         # 默认标记大小
            'hover_scale': 1.2,         # 悬停放大比例
            'selected_scale': 1.3,      # 选中放大比例
        },
        
        # 缓存配置
        'cache': {
            'enabled': True,            # 是否启用缓存
            'max_size': 100,            # 最大缓存数量
            'ttl': 3600,                # 缓存过期时间（秒）
        },
        
        # 布局配置
        'layout': {
            'default': 'default',       # 默认布局
            'auto_save': True,          # 自动保存布局
            'auto_restore': True,       # 自动恢复布局
        },
    }
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径，为 None 时使用默认配置
        """
        if self._initialized:
            return
            
        self._config: Dict[str, Any] = {}
        self._config_path = config_path
        
        # 加载默认配置
        self._config = self._deep_copy(self.DEFAULT_CONFIG)
        
        # 如果有配置文件，加载并合并
        if config_path and os.path.exists(config_path):
            self.load(config_path)
        
        self._initialized = True
    
    def _deep_copy(self, obj: Any) -> Any:
        """深拷贝"""
        if isinstance(obj, dict):
            return {k: self._deep_copy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._deep_copy(item) for item in obj]
        else:
            return obj
    
    # ==================== 配置访问 ====================
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        支持点分隔的键，如 'chart.min_bar_count'
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置节
        
        Args:
            section: 节名称
            
        Returns:
            配置字典
        """
        return self._config.get(section, {})
    
    # ==================== 配置文件操作 ====================
    
    def load(self, config_path: str):
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            
            # 合并配置
            self._merge_config(self._config, user_config)
            self._config_path = config_path
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def save(self, config_path: str = None):
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径，为 None 时使用加载时的路径
        """
        path = config_path or self._config_path
        if not path:
            return
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def _merge_config(self, base: Dict, override: Dict):
        """
        合并配置
        
        Args:
            base: 基础配置（会被修改）
            override: 覆盖配置
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def reset(self):
        """重置为默认配置"""
        self._config = self._deep_copy(self.DEFAULT_CONFIG)
    
    # ==================== 便捷方法 ====================
    
    def get_chart_config(self) -> Dict[str, Any]:
        """获取图表配置"""
        return self.get_section('chart')
    
    def get_theme_config(self) -> Dict[str, Any]:
        """获取主题配置"""
        return self.get_section('theme')
    
    def get_cache_config(self) -> Dict[str, Any]:
        """获取缓存配置"""
        return self.get_section('cache')
    
    def get_database_path(self) -> str:
        """获取数据库路径"""
        return self.get('database.path', '')
    
    @classmethod
    def instance(cls) -> 'FrontendConfig':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    # ==================== 便捷属性 ====================
    
    @property
    def theme(self) -> str:
        """获取主题名称"""
        return self.get('theme.name', 'dark')
    
    @theme.setter
    def theme(self, value: str):
        """设置主题名称"""
        self.set('theme.name', value)
    
    @property
    def default_layout(self) -> str:
        """获取默认布局"""
        return self.get('layout.default', 'default')
    
    @default_layout.setter
    def default_layout(self, value: str):
        """设置默认布局"""
        self.set('layout.default', value)
    
    @property
    def cache_size(self) -> int:
        """获取缓存大小"""
        return self.get('cache.max_size', 100)
    
    @cache_size.setter
    def cache_size(self, value: int):
        """设置缓存大小"""
        self.set('cache.max_size', value)
