"""
导出工具函数

数据和图表导出相关工具
"""

import os
from datetime import datetime
from typing import Optional, List, Any
import pandas as pd


class ExportUtils:
    """导出工具类"""
    
    @staticmethod
    def export_dataframe(
        df: pd.DataFrame,
        file_path: str,
        format: str = "csv",
        **kwargs
    ) -> bool:
        """
        导出 DataFrame
        
        Args:
            df: DataFrame 数据
            file_path: 文件路径
            format: 格式（csv, excel, json）
            **kwargs: 额外参数
            
        Returns:
            是否成功
        """
        try:
            if format == "csv":
                df.to_csv(file_path, index=True, **kwargs)
            elif format == "excel":
                df.to_excel(file_path, index=True, **kwargs)
            elif format == "json":
                df.to_json(file_path, orient="records", **kwargs)
            else:
                return False
            return True
        except Exception as e:
            print(f"导出失败: {e}")
            return False
    
    @staticmethod
    def export_chart(
        chart_widget: Any,
        file_path: str,
        format: str = "png",
        width: int = 1920,
        height: int = 1080
    ) -> bool:
        """
        导出图表
        
        Args:
            chart_widget: 图表控件
            file_path: 文件路径
            format: 格式（png, svg, pdf）
            width: 宽度
            height: 高度
            
        Returns:
            是否成功
        """
        try:
            # 使用 pyqtgraph 的导出功能
            if hasattr(chart_widget, 'grab'):
                # PyQt5 截图
                pixmap = chart_widget.grab()
                if format == "png":
                    pixmap.save(file_path, "PNG")
                elif format == "jpg":
                    pixmap.save(file_path, "JPEG")
                return True
            return False
        except Exception as e:
            print(f"导出图表失败: {e}")
            return False
    
    @staticmethod
    def get_default_filename(prefix: str = "export", ext: str = "csv") -> str:
        """
        生成默认文件名
        
        Args:
            prefix: 文件名前缀
            ext: 扩展名
            
        Returns:
            文件名
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{ext}"
    
    @staticmethod
    def ensure_directory(file_path: str) -> bool:
        """
        确保目录存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功
        """
        try:
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            return True
        except Exception as e:
            print(f"创建目录失败: {e}")
            return False
    
    @staticmethod
    def get_supported_formats() -> List[str]:
        """获取支持的数据导出格式"""
        return ["csv", "excel", "json"]
    
    @staticmethod
    def get_chart_formats() -> List[str]:
        """获取支持的图表导出格式"""
        return ["png", "jpg", "svg", "pdf"]
    
    # ==================== 便捷方法 ====================
    
    @staticmethod
    def export_to_csv(df: pd.DataFrame, file_path: str, **kwargs) -> bool:
        """
        导出为 CSV 文件
        
        Args:
            df: DataFrame 数据
            file_path: 文件路径
            **kwargs: 额外参数
            
        Returns:
            是否成功
        """
        return ExportUtils.export_dataframe(df, file_path, format="csv", **kwargs)
    
    @staticmethod
    def export_to_excel(df: pd.DataFrame, file_path: str, **kwargs) -> bool:
        """
        导出为 Excel 文件
        
        Args:
            df: DataFrame 数据
            file_path: 文件路径
            **kwargs: 额外参数
            
        Returns:
            是否成功
        """
        return ExportUtils.export_dataframe(df, file_path, format="excel", **kwargs)


# 模块级便捷函数（兼容直接导入）
export_to_csv = ExportUtils.export_to_csv
export_to_excel = ExportUtils.export_to_excel
export_dataframe = ExportUtils.export_dataframe
export_chart = ExportUtils.export_chart
export_chart_png = ExportUtils.export_chart  # 别名
