#!/usr/bin/env python3
"""
Data Service Layer 使用示例

演示:
1. 实时数据分发 (Pub/Sub)
2. 回测数据准备 (OHLCV)
3. 缓存管理
"""

import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/home/gabestation/Projects/LOTT')

from data_service import (
    DataService,
    create_data_service,
    create_backtest_service,
    BacktestRequest,
    CTPDataSource,
    OHLCVMessage,
    TickMessage
)


async def demo_backtest_data():
    """演示回测数据准备"""
    print("\n" + "=" * 60)
    print("=== 演示 1: 回测数据准备 ===")
    print("=" * 60)
    
    # 创建回测专用服务
    service = create_backtest_service(
        symbols=["IF2406", "IC2406"],
        timeframes=["1m", "5m"]
    )
    
    await service.initialize()
    await service.start()
    
    # 准备回测数据
    request = BacktestRequest(
        symbols=["IF2406", "IC2406"],
        timeframes=["1m", "5m", "1h"],
        start_date="2024-01-01",
        end_date="2024-01-31",
        preload=True,
        as_dataframe=True
    )
    
    response = await service.prepare_backtest_data(request)
    
    if response.success:
        print(f"\n✓ 成功获取 {len(response.data)} 个合约的数据")
        
        for symbol, timeframes in response.data.items():
            print(f"\n📊 {symbol}:")
            for tf, df in timeframes.items():
                if isinstance(df, object) and hasattr(df, 'shape'):
                    print(f"   {tf}: {len(df)} 条K线")
                    print(f"   价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")
        
        # 获取单个 DataFrame
        if "IF2406" in response.data and "1m" in response.data["IF2406"]:
            df = response.data["IF2406"]["1m"]
            print(f"\n示例 DataFrame (IF2406 1分钟K):")
            print(df.head())
    else:
        print(f"✗ 失败: {response.error}")
    
    await service.stop()


async def demo_cache():
    """演示缓存功能"""
    print("\n" + "=" * 60)
    print("=== 演示 2: 缓存管理 ===")
    print("=" * 60)
    
    service = create_data_service()
    await service.initialize()
    await service.start()
    
    # 先获取数据 (会生成并缓存)
    request = BacktestRequest(
        symbols=["IF2406"],
        timeframes=["1m"],
        start_date="2024-01-15",
        end_date="2024-01-16"
    )
    
    import time
    start = time.time()
    response1 = await service.prepare_backtest_data(request)
    time1 = time.time() - start
    
    # 再次获取 (应该从缓存读取)
    start = time.time()
    response2 = await service.prepare_backtest_data(request)
    time2 = time.time() - start
    
    print(f"\n首次加载: {time1:.3f}s")
    print(f"缓存加载: {time2:.3f}s")
    print(f"加速比: {time1/time2:.1f}x")
    
    # 查看统计
    stats = service.get_stats()
    print(f"\n缓存状态:")
    print(f"  缓存条目: {stats['cache_size']}")
    print(f"  OHLCV总数: {stats['ohlcv_count']}")
    
    await service.stop()


async def demo_realtime_pubsub():
    """演示实时 Pub/Sub"""
    print("\n" + "=" * 60)
    print("=== 演示 3: 实时数据分发 ===")
    print("=" * 60)
    
    service = create_data_service()
    await service.initialize()
    await service.start()
    
    # 订阅回调
    tick_count = [0]
    ohlcv_count = [0]
    
    async def on_tick(msg: TickMessage):
        tick_count[0] += 1
        if tick_count[0] <= 3:
            print(f"[Tick] {msg.symbol}: {msg.last_price:.2f}")
    
    async def on_ohlcv(msg: OHLCVMessage):
        ohlcv_count[0] += 1
        if ohlcv_count[0] <= 3:
            print(f"[OHLCV] {msg.symbol} {msg.timeframe}: {msg.close_price:.2f}")
    
    # 订阅
    await service.subscribe_tick("IF2406", on_tick)
    await service.subscribe_ohlcv("IF2406", "1m", on_ohlcv")
    
    # 发布模拟数据
    for i in range(5):
        await service.publish_tick(
            symbol="IF2406",
            exchange="CFFEX",
            data={
                "last_price": 3650.0 + i,
                "last_volume": 10000,
                "bid_price": 3649.8,
                "bid_volume": 100,
                "ask_price": 3650.2,
                "ask_volume": 100,
                "source": "demo"
            }
        )
        await asyncio.sleep(0.1)
    
    print(f"\n收到 Tick: {tick_count[0]} 条")
    print(f"收到 OHLCV: {ohlcv_count[0]} 条")
    
    await service.stop()


async def demo_stats():
    """演示统计信息"""
    print("\n" + "=" * 60)
    print("=== 演示 4: 服务统计 ===")
    print("=" * 60)
    
    service = create_data_service()
    await service.initialize()
    await service.start()
    
    # 获取统计
    stats = service.get_stats()
    print(f"\n服务状态:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # 健康检查
    health = await service.health_check()
    print(f"\n健康检查: {health['status']}")
    for component, status in health['checks'].items():
        print(f"  {component}: {status}")
    
    await service.stop()


async def demo_full_workflow():
    """完整工作流"""
    print("\n" + "#" * 60)
    print("# Data Service Layer 完整演示")
    print("#" * 60)
    
    # 1. 初始化服务
    service = create_backtest_service()
    await service.initialize()
    await service.start()
    print("\n[1] 服务已启动")
    
    # 2. 准备回测数据
    request = BacktestRequest(
        symbols=["IF2406", "IC2406"],
        timeframes=["1m", "5m", "1h"],
        start_date="2024-01-01",
        end_date="2024-01-10",
        preload=True
    )
    response = await service.prepare_backtest_data(request)
    
    if response.success:
        total_bars = sum(
            len(response.data[s][tf]) 
            for s in response.data 
            for tf in response.data[s]
        )
        print(f"[2] 成功准备 {total_bars} 条K线数据")
    
    # 3. 查看统计
    stats = service.get_stats()
    print(f"[3] 缓存条目: {stats['cache_size']}")
    
    # 4. 健康检查
    health = await service.health_check()
    print(f"[4] 健康状态: {health['status']}")
    
    # 5. 停止
    await service.stop()
    print("\n[5] 服务已停止")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Data Service Layer 使用示例")
    print("=" * 60)
    
    # 运行演示
    await demo_backtest_data()
    await demo_cache()
    await demo_realtime_pubsub()
    await demo_stats()
    
    print("\n" + "=" * 60)
    print("完整工作流")
    print("=" * 60)
    await demo_full_workflow()
    
    print("\n" + "#" * 60)
    print("# 演示完成!")
    print("#" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
