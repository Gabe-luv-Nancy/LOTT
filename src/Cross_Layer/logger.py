import inspect
import logging
import os
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# pptx 为可选依赖
try:
    from pptx.dml.color import RGBColor  # noqa: F401
except ImportError:
    RGBColor = None


def _get_caller_frame(depth: int = 2) -> Optional[Any]:
    """向上遍历调用栈，返回指定深度的栈帧"""
    try:
        frame = inspect.currentframe()
        for _ in range(depth):
            if frame is None:
                return None
            frame = frame.f_back
        return frame
    except Exception:
        return None


def _get_caller_name() -> str:
    """获取调用者模块名（优先），其次类名，最后函数名"""
    frame = _get_caller_frame(3)
    if frame is None:
        return "unknown"

    try:
        module = inspect.getmodule(frame)
        if module and module.__name__ not in ("__main__", "__init__"):
            return module.__name__
        if hasattr(frame, 'f_locals') and 'self' in frame.f_locals:
            return type(frame.f_locals['self']).__name__
        return frame.f_code.co_name
    except AttributeError:
        return "unknown"


def _get_extra_context() -> Dict[str, Any]:
    """收集调用位置的上下文信息（用于日志格式填充）"""
    frame = _get_caller_frame(3)
    if frame is None:
        return {'filename': 'unknown', 'classname': '', 'funcname': 'unknown', 'lineno': 0}

    try:
        filename = os.path.basename(frame.f_code.co_filename)
        funcname = frame.f_code.co_name
        lineno   = frame.f_lineno
    except AttributeError:
        filename, funcname, lineno = 'unknown', 'unknown', 0

    classname = ''
    try:
        if hasattr(frame, 'f_locals') and 'self' in frame.f_locals:
            classname = type(frame.f_locals['self']).__name__
    except Exception:
        pass

    return {
        'filename': filename,
        'classname': classname,
        'funcname': funcname,
        'lineno': lineno,
    }


class ContextLogger:
    """
    带调用上下文信息的日志记录器。

    自动在日志中注入调用方的文件名、类名、函数名、行号，
    无需手动传入 extra 参数。

    用法:
        from Cross_Layer.logger import ContextLogger
        log = ContextLogger(__name__)
        log.info("操作完成")   # 自动附带 [filename:lineno - ClassName.method] 信息
    """
    _instances: Dict[str, Any] = {}

    def __init__(self, name: Optional[str] = None):
        logger_name = name or _get_caller_name()
        if logger_name not in ContextLogger._instances:
            self.logger = logging.getLogger(logger_name)
            ContextLogger._instances[logger_name] = self
        else:
            self.logger = ContextLogger._instances[logger_name].logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.debug(msg, *args, extra=_get_extra_context(), **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.info(msg, *args, extra=_get_extra_context(), **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.warning(msg, *args, extra=_get_extra_context(), **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.error(msg, *args, extra=_get_extra_context(), **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.exception(msg, *args, extra=_get_extra_context(), **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.logger.critical(msg, *args, extra=_get_extra_context(), **kwargs)


def setup_logger(
    name: Optional[str] = None,
    level: int = logging.DEBUG,
    log_dir: str = 'logs',
    formatter: Optional[logging.Formatter] = None,
) -> ContextLogger:
    """
    配置日志系统（全局调用一次即可）。

    参数:
        name: 日志名称，默认自动取调用方模块名
        level: 日志级别，默认 DEBUG
        log_dir: 日志文件目录，默认 'logs'
        formatter: 自定义格式化器

    返回:
        ContextLogger 实例

    用法:
        from Cross_Layer.logger import setup_logger
        log = setup_logger("my_module", level=logging.INFO)
        log.info("应用启动")
    """
    logger_name = name or _get_caller_name()
    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return ContextLogger(logger_name)

    logger.setLevel(level)
    logger.propagate = False

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(log_dir, f'{logger_name}_{timestamp}.log')

    if formatter is None:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(filename)s:%(lineno)d - %(classname)s.%(funcname)s] - %(message)s'
        )

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return ContextLogger(logger_name)


def dir_exist(
    designated_path: str,
    parent_path: Optional[str] = None,
    on_error_raise: bool = False,
    create_if_missing: bool = True,
    remove_if_exists: bool = False,
    log_level: int = logging.INFO,
    error_message: Optional[str] = None,
) -> bool:
    """
    确保指定路径存在，支持创建/删除/验证三种操作。

    参数:
        designated_path: 目标路径（相对于 parent_path）
        parent_path: 父目录路径，默认 os.getcwd()/files
        on_error_raise: 路径无效时是否抛出异常
        create_if_missing: 路径不存在时是否自动创建
        remove_if_exists: 路径已存在（文件）时是否先删除
        log_level: 日志级别
        error_message: 自定义错误消息

    返回:
        bool: 操作是否成功
    """
    files_dir = os.path.join(os.getcwd(), "files")
    base = parent_path or files_dir

    logging.basicConfig(level=log_level,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log = logging.getLogger("PathHandler")

    try:
        if not designated_path:
            msg = "路径不能为空"
            log.error(msg)
            if on_error_raise:
                raise ValueError(msg)
            return False

        normalized = os.path.join(base, os.path.normpath(designated_path))
        log.info(f"目标路径: {normalized}")

        # Windows 非法字符检查
        if platform.system() == "Windows":
            illegal = r'[<>"/|?*]'
            if re.search(illegal, normalized):
                msg = f"路径包含非法字符: {normalized}"
                log.error(msg)
                if on_error_raise:
                    raise ValueError(msg)
                return False

        # 路径长度限制（Windows 260 字符）
        if platform.system() == "Windows" and len(normalized) > 260:
            msg = f"路径超过 Windows 最大长度({len(normalized)} 字符)"
            log.warning(msg)
            if on_error_raise:
                raise OSError(msg)

        if os.path.exists(normalized):
            log.info("路径已存在")
            if os.path.isfile(normalized) and remove_if_exists:
                try:
                    os.remove(normalized)
                    log.info(f"文件已删除: {normalized}")
                except OSError as e:
                    msg = f"删除文件失败: {e}"
                    log.error(msg)
                    if on_error_raise:
                        raise
                    return False
            else:
                return True

        log.warning(f"路径不存在: {normalized}")
        if not create_if_missing:
            msg = error_message or "路径不存在且配置为不自动创建"
            log.error(msg)
            if on_error_raise:
                raise FileNotFoundError(msg)
            return False

        try:
            p = Path(normalized)
            if p.suffix:
                p.parent.mkdir(parents=True, exist_ok=True)
                log.info(f"已创建父目录: {p.parent}")
            else:
                p.mkdir(parents=True, exist_ok=True)
                log.info(f"已创建目录: {normalized}")
            return True
        except OSError as e:
            msg = f"创建路径失败: {e}"
            log.exception(msg)
            if on_error_raise:
                raise
            return False

    except Exception as e:
        log.exception(f"路径处理异常: {e}")
        if on_error_raise:
            raise
        return False


# 模块级默认 logger（按 __name__ 自动命名）
logger = setup_logger()
