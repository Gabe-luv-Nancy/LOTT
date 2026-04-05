"""
TimescaleDB 使用示例

演示如何使用 TimescaleDB 模块进行数据操作
"""

import os
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


def example_config():
    """示例 1: 配置管理"""
    from Data.DataFeed.TimescaleDB import TimescaleDBConfig, load_config
    
    # 方法 1: 使用默认配置
    config = TimescaleDBConfig()
    print(f"默认配置: {config.host}:{config.port}/{config.database}")
    
    # 方法 2: 自定义配置
    config = TimescaleDBConfig(
        host='localhost',
        port=5432,
        database='lott',
        username='postgres',
        password='yourpassword'
    )
    
    # 方法 3: 从 YAML 文件加载
    config = load_config('timescaledb_config.yaml')
    
    print("配置示例完成")
    return config


def example_connection():
    """示例 2: 连接管理"""
    from Data.DataFeed.TimescaleDB import (
        TimescaleDBConfig,
        TimescaleDBClient,
        initialize,
        close
    )
    
    # 方法 1: 使用便捷函数
    if initialize():
        print("连接成功!")
        
        # 健康检查
        from Data.DataFeed.TimescaleDB import get_client
        client = get_client()
        health = client.health_check()
        print(f"健康状态: {health}")
        
        close()
    
    # 方法 2: 手动管理连接
    config = TimescaleDBConfig(host='localhost', database='lott')
    client = TimescaleDBClient(config)
    
    if client.connect():
        print("手动连接成功!")
        client.disconnect()


def example_create_tables():
    """示例 3: 创建表"""
    from Data.DataFeed.TimescaleDB import (
        TimescaleDBConfig,
        initialize,
        close,
        TableCreator
    )
    
    config = TimescaleDBConfig(host='localhost', database='lott')
    
    if not initialize(config):
        print("连接失败")
        return
    
    # 创建表
    creator = TableCreator()
    
    # 创建所有表
    if creator.create_all_tables():
        print("表创建成功!")
    else:
        print("表创建失败")
    
    # 列出表
    tables = creator.list_tables()
    print(f"现有表: {tables}")
    
    close()


def example_import_json():
    """示例 4: 导入 JSON 文件"""
    from Data.DataFeed.TimescaleDB import import_json
    
    # 一行代码导入
    json_file = 'path/to/your/data.json'
    
    if os.path.exists(json_file):
        result = import_json(
            file_path=json_file,
            batch_size=1000
        )
        
        if result.success:
            print(f"导入成功!")
            print(f"  元数据ID: {result.metadata_id}")
            print(f"  导入行数: {result.rows_imported}")
            print(f"  跳过行数: {result.rows_skipped}")
        else:
            print(f"导入失败: {result.errors}")
    else:
        print(f"文件不存在: {json_file}")


def example_import_with_progress():
    """示例 5: 带进度回调的导入"""
    from Data.DataFeed.TimescaleDB import (
        TimescaleDBConfig,
        initialize,
        close,
        TableCreator,
        JSONImport
    )
    
    config = TimescaleDBConfig(host='localhost', database='lott')
    
    if not initialize(config):
        return
    
    # 确保表存在
    creator = TableCreator()
    creator.create_all_tables()
    
    # 创建导入器
    importer = JSONImport()
    
    # 进度回调
    def progress(current, total):
        percent = (current / total) * 100 if total > 0 else 0
        print(f"进度: {current}/{total} ({percent:.1f}%)")
    
    # 导入
    result = importer.import_from_file(
        'path/to/data.json',
        batch_size=500,
        progress_callback=progress
    )
    
    print(f"导入完成: {result.rows_imported} 行")
    close()


def example_import_dataframe():
    """示例 6: 从 DataFrame 导入"""
    import pandas as pd
    from Data.DataFeed.TimescaleDB import (
        TimescaleDBConfig,
        initialize,
        close,
        TableCreator,
        JSONImport
    )
    
    # 创建示例 DataFrame
    df = pd.DataFrame({
        'A': [1, 2, 3],
        'B': [4, 5, 6]
    }, index=pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']))
    
    config = TimescaleDBConfig(host='localhost', database='lott')
    
    if not initialize(config):
        return
    
    creator = TableCreator()
    creator.create_all_tables()
    
    importer = JSONImport()
    result = importer.import_from_dataframe(
        df,
        source_name='example_df',
        timeframe='1d'
    )
    
    print(f"导入结果: {result.success}")
    close()


def example_query():
    """示例 7: 查询数据"""
    from Data.DataFeed.TimescaleDB import (
        TimescaleDBConfig,
        initialize,
        get_client,
        close
    )
    
    config = TimescaleDBConfig(host='localhost', database='lott')
    
    if not initialize(config):
        return
    
    client = get_client()
    
    # 查询元数据
    stats = client.get_stats()
    print(f"统计信息: {stats}")
    
    # 查询 OHLCV 数据
    from datetime import datetime
    data = client.query_ohlcv(
        symbol="IF2406",
        timeframe="1m",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2)
    )
    
    print(f"查询到 {len(data)} 条数据")
    
    close()


def example_ohlcv_operations():
    """示例 8: OHLCV 数据操作"""
    from Data.DataFeed.TimescaleDB import (
        TimescaleDBConfig,
        initialize,
        get_client,
        close
    )
    from Data.DataFeed.TimescaleDB.client import OHLCVData
    from datetime import datetime
    
    config = TimescaleDBConfig(host='localhost', database='lott')
    
    if not initialize(config):
        return
    
    client = get_client()
    
    # 创建表
    client.create_tables()
    
    # 插入 OHLCV 数据
    data = [
        OHLCVData(
            symbol="IF2406",
            exchange="CFFEX",
            timeframe="1m",
            time=datetime(2024, 1, 1, 9, 30),
            open=3650.0,
            high=3655.0,
            low=3648.0,
            close=3652.0,
            volume=10000,
            turnover=36520000
        ),
    ]
    
    if client.insert_ohlcv(data):
        print("OHLCV 数据插入成功")
    
    # 查询数据
    results = client.query_ohlcv(
        symbol="IF2406",
        timeframe="1m",
        start_time=datetime(2024, 1, 1),
        end_time=datetime(2024, 1, 2)
    )
    
    for ohlcv in results:
        print(f"{ohlcv.time}: {ohlcv.open} - {ohlcv.close}")
    
    close()


if __name__ == '__main__':
    print("=" * 50)
    print("TimescaleDB 使用示例")
    print("=" * 50)
    
    print("\n[1] 配置示例")
    example_config()
    
    print("\n[2] 连接示例")
    # example_connection()  # 需要实际数据库
    
    print("\n[3] 创建表示例")
    # example_create_tables()  # 需要实际数据库
    
    print("\n[4] JSON 导入示例")
    # example_import_json()  # 需要实际数据库和文件
    
    print("\n注意: 取消注释示例代码以运行实际数据库操作")
