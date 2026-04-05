import json
import logging
import os
import shutil
import tempfile
from typing import Any, Callable, Dict, Optional, Type

# 模块级 logger
logger = logging.getLogger(__name__)


class JSONStorage:
    """
    通用的 JSON 文件读写工具，支持原子写入和原子更新。

    用法:
        storage = JSONStorage('data/config.json', default_data={'version': 1})
        config = storage.read()
        config['new_setting'] = 'value'
        storage.write(config)

        # 原子更新（读写合并为一步）
        storage.update(lambda data: data.update({'counter': data.get('counter', 0) + 1}))
    """

    def __init__(
        self,
        file_path: str,
        default_data: Any = None,
        encoder: Optional[Type[json.JSONEncoder]] = None,
        validator: Optional[Callable[[Any], bool]] = None,
    ):
        self.file_path  = file_path
        self.default_data = default_data
        self.encoder   = encoder
        self.validator = validator

        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"创建目录: {dir_path}")

    def read(self) -> Any:
        if not os.path.exists(self.file_path):
            logger.debug(f"文件不存在，返回默认数据: {self.file_path}")
            return (self.default_data.copy()
                    if hasattr(self.default_data, 'copy')
                    else self.default_data)

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if self.validator and not self.validator(data):
                raise ValueError("数据验证失败")
            return data
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"JSON 解析错误 {self.file_path}: {e}")
            raise
        except Exception as e:
            logger.exception(f"读取文件异常 {self.file_path}")
            raise

    def write(self, data: Any) -> None:
        tmp_path = None
        try:
            if self.validator and not self.validator(data):
                raise ValueError("写入前数据验证失败")

            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8',
                dir=os.path.dirname(self.file_path),
                delete=False,
            ) as tmp_file:
                json.dump(data, tmp_file,
                          indent=2, ensure_ascii=False,
                          cls=self.encoder)
                tmp_path = tmp_file.name

            if tmp_path and os.path.exists(tmp_path):
                shutil.move(tmp_path, self.file_path)
                logger.debug(f"写入成功: {self.file_path}")
            else:
                raise FileNotFoundError("临时文件创建失败")

        except Exception as e:
            logger.exception(f"写入失败 {self.file_path}")
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def update(self, updater: Callable[[Any], Any]) -> None:
        current = self.read()
        if current is None and self.default_data is not None:
            current = (self.default_data.copy()
                       if hasattr(self.default_data, 'copy')
                       else self.default_data)
        self.write(updater(current))


class JSONValidator:
    """JSON 数据验证工具"""

    @staticmethod
    def validate_schema(data: Any, schema: Dict) -> bool:
        try:
            import jsonschema
            jsonschema.validate(data, schema)
            return True
        except ImportError:
            logger.warning("jsonschema 未安装，跳过 schema 验证")
            return True
        except Exception as e:
            logger.error(f"Schema 验证失败: {e}")
            return False

    @staticmethod
    def validate_types(data: Any, type_map: Dict[str, type]) -> bool:
        if not isinstance(data, dict):
            logger.error("数据不是字典类型")
            return False
        for key, expected in type_map.items():
            if key in data and not isinstance(data[key], expected):
                logger.error(f"字段 '{key}' 类型错误: 期望 {expected}, 实际 {type(data[key])}")
                return False
        return True


class CustomJSONEncoder(json.JSONEncoder):
    """可扩展的自定义 JSON 编码器"""

    def default(self, o: Any) -> Any:
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        if hasattr(o, '__json__') and callable(o.__json__):
            return o.__json__()
        return super().default(o)
