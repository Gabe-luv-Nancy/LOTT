"""
RealtimeRecorder - 实时数据记录器

负责：
1. 接收 Tick 数据
2. 合成 K 线数据
3. 批量写入数据库
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from threading import Thread
from queue import Queue, Empty
import logging

from vnpy.trader.object import TickData, BarData


class RealtimeRecorder:
    """
    实时数据记录器
    
    接收 Tick/Bar 数据，批量写入数据库。
    同时触发 K 线合成逻辑。
    """

    def __init__(self, database_ops: Any):
        """初始化记录器
        
        Args:
            database_ops: 数据库操作接口 (DatabaseOperations 实例)
        """
        self.db = database_ops
        self.logger = logging.getLogger(__name__)
        
        # Tick 缓冲 (用于合成 K 线)
        self.tick_buffer: Dict[str, List[TickData]] = {}
        
        # K线合成器 {vt_symbol: {interval: BarCollector}}
        self.bar_collectors: Dict[str, Dict[str, 'BarCollector']] = {}
        
        # 支持的 K 线周期
        self.supported_intervals = ["1m", "5m", "15m", "1h", "1d"]
        
        # 写入队列
        self.write_queue: Queue = Queue()
        self.running = True
        
        # 启动写入线程
        self.write_thread = Thread(
            target=self._write_loop,
            name="RealtimeRecorder-WriteThread",
            daemon=True
        )
        self.write_thread.start()
        
        self.logger.info("RealtimeRecorder 初始化完成")

    def on_tick(self, tick: TickData) -> None:
        """处理 Tick 数据
        
        Args:
            tick: Tick 数据对象
        """
        vt_symbol = tick.vt_symbol
        
        # 1. 直接存储 Tick 到队列
        self.write_queue.put(('tick', tick))
        
        # 2. 合成 K 线
        self._update_bar_collectors(tick)

    def on_bar(self, bar: BarData) -> None:
        """处理 K 线数据 (直接接收或合成)
        
        Args:
            bar: K 线数据对象
        """
        self.write_queue.put(('bar', bar))
        self.logger.debug(f"收到 Bar: {bar.vt_symbol} {bar.interval} {bar.datetime}")

    def _update_bar_collectors(self, tick: TickData) -> None:
        """更新 K 线合成器
        
        Args:
            tick: Tick 数据
        """
        vt_symbol = tick.vt_symbol
        
        # 初始化 symbol 的合成器
        if vt_symbol not in self.bar_collectors:
            self.bar_collectors[vt_symbol] = {}
            for interval in self.supported_intervals:
                from .bar_collector import BarCollector
                self.bar_collectors[vt_symbol][interval] = BarCollector(interval)
        
        # 更新各周期 K 线
        for interval, collector in self.bar_collectors[vt_symbol].items():
            bar = collector.update_tick(tick)
            if bar:
                self.write_queue.put(('bar', bar))

    def _write_loop(self) -> None:
        """写入循环 (批量写入)"""
        batch: List[tuple] = []
        batch_size = 100
        flush_interval = 5  # 秒
        
        while self.running:
            try:
                # 等待新数据，超时刷新
                item = self.write_queue.get(timeout=flush_interval)
                batch.append(item)
                
                # 达到批量大小则写入
                if len(batch) >= batch_size:
                    self._flush(batch)
                    batch = []
                    
            except Empty:
                # 超时，刷新剩余数据
                if batch:
                    self._flush(batch)
                    batch = []
            except Exception as e:
                self.logger.error(f"写入循环异常: {e}")

    def _flush(self, batch: List[tuple]) -> None:
        """批量写入数据库
        
        Args:
            batch: 待写入的数据批次
        """
        try:
            ticks = [item[1] for item in batch if item[0] == 'tick']
            bars = [item[1] for item in batch if item[0] == 'bar']
            
            if ticks:
                self._save_tick_data(ticks)
                
            if bars:
                self._save_bar_data(bars)
                
            self.logger.debug(
                f"批量写入完成: {len(ticks)} ticks, {len(bars)} bars"
            )
            
        except Exception as e:
            self.logger.error(f"批量写入失败: {e}")

    def _save_tick_data(self, ticks: List[TickData]) -> None:
        """保存 Tick 数据
        
        Args:
            ticks: Tick 数据列表
        """
        try:
            # 转换为数据库记录格式
            records = []
            for tick in ticks:
                records.append({
                    'vt_symbol': tick.vt_symbol,
                    'symbol': tick.symbol,
                    'exchange': tick.exchange.value if tick.exchange else '',
                    'gateway_name': tick.gateway_name,
                    'datetime': tick.datetime,
                    'date': tick.date,
                    'time': tick.time,
                    'last_price': tick.last_price,
                    'last_volume': tick.volume,
                    'limit_up': tick.limit_up,
                    'limit_down': tick.limit_down,
                    'open_price': tick.open_price,
                    'high_price': tick.high_price,
                    'low_price': tick.low_price,
                    'pre_close': tick.pre_close,
                    'bid_price_1': tick.bid_price_1,
                    'bid_price_2': tick.bid_price_2,
                    'bid_price_3': tick.bid_price_3,
                    'bid_price_4': tick.bid_price_4,
                    'bid_price_5': tick.bid_price_5,
                    'ask_price_1': tick.ask_price_1,
                    'ask_price_2': tick.ask_price_2,
                    'ask_price_3': tick.ask_price_3,
                    'ask_price_4': tick.ask_price_4,
                    'ask_price_5': tick.ask_price_5,
                    'bid_volume_1': tick.bid_volume_1,
                    'bid_volume_2': tick.bid_volume_2,
                    'bid_volume_3': tick.bid_volume_3,
                    'bid_volume_4': tick.bid_volume_4,
                    'bid_volume_5': tick.bid_volume_5,
                    'ask_volume_1': tick.ask_volume_1,
                    'ask_volume_2': tick.ask_volume_2,
                    'ask_volume_3': tick.ask_volume_3,
                    'ask_volume_4': tick.ask_volume_4,
                    'ask_volume_5': tick.ask_volume_5,
                    'open_interest': tick.open_interest,
                    'turnover': tick.turnover,
                })
            
            # 调用数据库接口保存
            self.db.save_tick_data(records)
            
        except Exception as e:
            self.logger.error(f"Tick 数据保存失败: {e}")

    def _save_bar_data(self, bars: List[BarData]) -> None:
        """保存 K 线数据
        
        Args:
            bars: K 线数据列表
        """
        try:
            records = []
            for bar in bars:
                records.append({
                    'vt_symbol': bar.vt_symbol,
                    'symbol': bar.symbol,
                    'exchange': bar.exchange.value if bar.exchange else '',
                    'gateway_name': bar.gateway_name,
                    'interval': bar.interval.value if hasattr(bar.interval, 'value') else str(bar.interval),
                    'datetime': bar.datetime,
                    'date': bar.date,
                    'time': bar.time,
                    'open_price': bar.open_price,
                    'high_price': bar.high_price,
                    'low_price': bar.low_price,
                    'close_price': bar.close_price,
                    'volume': bar.volume,
                    'turnover': bar.turnover,
                    'open_interest': bar.open_interest,
                })
            
            self.db.save_bar_data(records)
            
        except Exception as e:
            self.logger.error(f"Bar 数据保存失败: {e}")

    def close(self) -> None:
        """关闭记录器"""
        self.running = False
        self.logger.info("RealtimeRecorder 已关闭")
