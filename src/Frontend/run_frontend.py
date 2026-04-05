#!/usr/bin/env python3
"""
LOTT 前端启动入口

三层快速使用结构：
  图层1 - 数据库总表层（DatabasePanel）
  图层2 - 策略变量层  （VariablePanel）
  图层3 - 回测可视化层（BacktestPanel）

用法::

    # 启动完整 GUI
    python run_frontend.py

    # 仅启动数据库浏览器
    python run_frontend.py --mode database

    # 仅启动回测可视化
    python run_frontend.py --mode backtest

    # 指定数据库路径
    python run_frontend.py --db-path /path/to/data.db
"""

import sys
import os
import argparse

# 确保项目根目录在路径中
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='LOTT 量化可视化平台',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--mode', 
        choices=['full', 'database', 'backtest', 'variables'],
        default='full',
        help='启动模式: full=完整界面, database=数据库浏览器, '
             'backtest=回测可视化, variables=变量分析'
    )
    parser.add_argument(
        '--db-path',
        type=str,
        default=None,
        help='SQLite 数据库路径（覆盖默认配置）'
    )
    parser.add_argument(
        '--theme',
        choices=['dark', 'light'],
        default='dark',
        help='界面主题'
    )
    parser.add_argument(
        '--no-qdarkstyle',
        action='store_true',
        help='禁用 qdarkstyle（使用系统默认主题）'
    )
    return parser.parse_args()


def setup_app(args):
    """设置 QApplication"""
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    
    # 高 DPI 支持
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("LOTT 量化可视化平台")
    app.setOrganizationName("LOTT")
    
    # 应用主题
    if not args.no_qdarkstyle:
        try:
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        except ImportError:
            print("[INFO] qdarkstyle 未安装，使用系统默认主题")
    
    return app


def setup_config(args):
    """设置前端配置"""
    from Frontend.core import FrontendConfig
    
    config = FrontendConfig()
    
    if args.db_path:
        config.set('database.path', args.db_path)
    
    if args.theme:
        config.set('theme.name', args.theme)
    
    return config


def launch_full(config):
    """启动完整界面"""
    from Frontend.ui import MainWindow
    
    window = MainWindow()
    window.show()
    return window


def launch_database(config):
    """启动数据库浏览器（图层1）"""
    from PyQt5.QtWidgets import QMainWindow
    from Frontend.panels.database import DatabasePanel
    
    # 初始化数据操作层
    data_op = _get_data_operation(config)
    
    window = QMainWindow()
    window.setWindowTitle("LOTT - 数据库浏览器")
    window.setMinimumSize(1000, 600)
    
    panel = DatabasePanel(data_operation=data_op)
    window.setCentralWidget(panel)
    window.show()
    return window


def launch_variables(config):
    """启动变量分析器（图层2）"""
    from PyQt5.QtWidgets import QMainWindow
    from Frontend.panels.variables import VariablePanel
    
    window = QMainWindow()
    window.setWindowTitle("LOTT - 策略变量分析")
    window.setMinimumSize(1200, 700)
    
    panel = VariablePanel()
    window.setCentralWidget(panel)
    window.show()
    return window


def launch_backtest(config):
    """启动回测可视化（图层3）"""
    from PyQt5.QtWidgets import QMainWindow
    from Frontend.panels.backtest import BacktestPanel
    
    window = QMainWindow()
    window.setWindowTitle("LOTT - 回测结果可视化")
    window.setMinimumSize(1200, 800)
    
    panel = BacktestPanel()
    window.setCentralWidget(panel)
    window.show()
    return window


def _get_data_operation(config):
    """
    获取数据操作实例（连接到后端 Data 层）
    
    Returns:
        DataOperation 实例，如果 Data 层不可用则返回 None
    """
    try:
        from Data.DataManager.data_operation import DataOperation
        from Data.DatabaseManager.database_config import DatabaseConfig
        
        db_path = config.get('database.path')
        db_config = DatabaseConfig(
            db_type='sqlite',
            db_url=f"sqlite:///{db_path}",
        )
        data_op = DataOperation(db_config)
        return data_op
    except ImportError:
        print("[WARN] Data 层未找到，数据库面板将使用演示模式")
        return None
    except Exception as e:
        print(f"[WARN] 连接数据库失败: {e}")
        return None


# ==================== 快捷启动函数（供 notebook 调用） ====================

def quick_database(db_path: str = None):  # type: ignore[assignment]
    """
    快速启动数据库浏览器
    
    Example::
    
        from Frontend.run_frontend import quick_database
        quick_database('path/to/data.db')
    """
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication.instance() or QApplication(sys.argv)
    try:
        import qdarkstyle  # type: ignore[import-untyped]
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())  # type: ignore[union-attr]
    except ImportError:
        pass
    
    from Frontend.core import FrontendConfig
    config = FrontendConfig()
    if db_path:
        config.set('database.path', db_path)
    
    window = launch_database(config)
    
    instance = QApplication.instance()
    if instance and not instance.startingUp():
        app.exec_()
    return window


def quick_backtest(result=None):
    """
    快速启动回测可视化
    
    Args:
        result: BacktestResult 数据（可选），None 则显示空面板
    
    Example::
    
        from Frontend.run_frontend import quick_backtest
        quick_backtest(backtest_result)
    """
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication.instance() or QApplication(sys.argv)
    try:
        import qdarkstyle  # type: ignore[import-untyped]
        app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())  # type: ignore[union-attr]
    except ImportError:
        pass
    
    from Frontend.core import FrontendConfig
    config = FrontendConfig()
    window = launch_backtest(config)
    
    if result is not None:
        # 获取 BacktestPanel 并加载数据
        panel = window.centralWidget()
        if panel is not None and hasattr(panel, 'load_result'):
            panel.load_result(result)
    
    instance = QApplication.instance()
    if instance and not instance.startingUp():
        app.exec_()
    return window


# ==================== 主入口 ====================

def main():
    """主入口函数"""
    args = parse_args()
    app = setup_app(args)
    config = setup_config(args)
    
    launchers = {
        'full': launch_full,
        'database': launch_database,
        'backtest': launch_backtest,
        'variables': launch_variables,
    }
    
    launcher = launchers[args.mode]
    window = launcher(config)
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
