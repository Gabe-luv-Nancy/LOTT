"""
BaseAdapter - 适配器基类

所有框架适配器的抽象基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from ..config import UniConfig
from ..data import UniData
from ..strategy import UniStrategy
from ..result import UniResult


class BaseAdapter(ABC):
    """
    回测框架适配器基类
    
    所有具体框架适配器必须继承此类并实现:
    - run(): 执行回测
    - normalize_result(): 转换为统一结果格式
    - plot(): 绘图功能 (可选)
    """
    
    name: str = "base"
    
    def __init__(self, config: UniConfig = None):
        """
        初始化适配器
        
        Args:
            config: 统一配置对象
        """
        self.config = config
        self._native_data = None
        self._wrapped_strategy = None
    
    @property
    def framework_version(self) -> str:
        """
        底层框架版本
        
        Returns:
            str: 框架版本号
        """
        return "unknown"
    
    def is_available(self) -> bool:
        """
        检查底层框架是否可用
        
        Returns:
            bool: 框架是否可用
        """
        return True
    
    def load_data(self, data: UniData) -> Any:
        """
        加载并转换数据为框架特定格式
        
        Args:
            data: 统一格式数据
            
        Returns:
            Any: 框架特定的数据格式
        """
        self._native_data = data
        return data
    
    def wrap_strategy(self, strategy: UniStrategy) -> Any:
        """
        将统一策略包装为框架特定策略
        
        Args:
            strategy: 统一策略对象
            
        Returns:
            Any: 框架特定的策略对象
        """
        self._wrapped_strategy = strategy
        return strategy
    
    @abstractmethod
    def run(
        self,
        strategy: UniStrategy,
        data: UniData,
        config: UniConfig
    ) -> UniResult:
        """
        执行回测 (必须实现)
        
        Args:
            strategy: 策略对象
            data: 统一格式的历史数据
            config: 统一配置对象
            
        Returns:
            UniResult: 统一格式的回测结果
        """
        pass
    
    @abstractmethod
    def normalize_result(self, native_result: Any) -> UniResult:
        """
        将框架原生结果转换为统一格式 (必须实现)
        
        Args:
            native_result: 框架原生的结果对象
            
        Returns:
            UniResult: 统一格式的结果
        """
        pass
    
    def optimize(
        self,
        strategy: UniStrategy,
        data: UniData,
        config: UniConfig,
        param_grid: Dict,
        maximize: str = "Sharpe Ratio",
        constraint = None,
        max_trials: Optional[int] = None
    ) -> UniResult:
        """
        参数优化 (默认暴力网格搜索，子类可覆盖)
        
        Args:
            strategy: 策略对象
            data: 数据对象
            config: 配置对象
            param_grid: 参数网格
            maximize: 优化目标
            constraint: 约束条件
            max_trials: 最大试验次数
            
        Returns:
            UniResult: 最优结果
        """
        from itertools import product
        import time
        
        best_result: Optional[UniResult] = None
        best_score = float('-inf')
        best_params: Dict = {}
        
        param_names = list(param_grid.keys())
        param_values_list = [param_grid[name] for name in param_names]
        
        total_trials = 1
        for values in param_values_list:
            total_trials *= len(values)
        
        trial_count = 0
        start_time = time.time()
        
        for param_combo in product(*param_values_list):
            param_dict = dict(zip(param_names, param_combo))
            
            # 设置参数
            strategy.set_parameters(**param_dict)
            
            # 运行回测
            result = self.run(strategy, data, config)
            
            # 选择最优
            score = getattr(result, maximize.replace(" ", "_").lower(), 0)
            if score > best_score:
                best_score = score
                best_result = result
                best_params = param_dict
            
            trial_count += 1
            print(f"  Trial {trial_count}/{total_trials}: {param_dict} -> {score:.3f}")
        
        duration = time.time() - start_time
        print(f"优化完成: {total_trials} 次试验, 耗时 {duration:.1f}s")
        
        # 设置最优参数
        if best_result is not None:
            best_result.optimized_params = best_params
        
        return best_result  # type: ignore
    
    def plot(self, result: UniResult, **kwargs):
        """绘图 (子类实现)"""
        raise NotImplementedError(
            f"框架 {self.name} 不支持绘图功能"
        )
    
    def _validate_strategy(self, strategy: UniStrategy) -> None:
        """验证策略"""
        if not isinstance(strategy, UniStrategy):
            raise TypeError(
                f"strategy 必须是 UniStrategy 的子类, 实际是 {type(strategy)}"
            )
    
    def _validate_data(self, data: UniData) -> None:
        """验证数据"""
        if not isinstance(data, UniData):
            raise TypeError(
                f"data 必须是 UniData 类型, 实际是 {type(data)}"
            )
        if data.empty:
            raise ValueError("数据为空")