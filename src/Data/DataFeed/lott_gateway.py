"""
LottGateway - CTP 行情接入适配器

整合 vnpy CTP 接口，负责：
1. 连接 CTP 账户
2. 订阅/取消订阅行情
3. 推送行情到 LOTT 系统
"""

from typing import Optional, Dict, Any, Set
from datetime import datetime
import logging

from vnpy.trader.gateway import BaseGateway
from vnpy.trader.object import (
    TickData,
    BarData,
    SubscribeRequest,
    CancelRequest,
    OrderRequest,
    ContractData,
)
from vnpy.trader.constant import (
    Direction,
    Offset,
    OrderType,
    Status,
    Exchange,
    Interval,
    Product,
    OptionType,
)

# 事件定义
EVENT_TICK = "eTick"
EVENT_BAR = "eBar"
EVENT_GATEWAY_CONNECTED = "eGatewayConnected"
EVENT_GATEWAY_DISCONNECTED = "eGatewayDisconnected"
EVENT_CONTRACT = "eContract"


class LottGateway(BaseGateway):
    """
    LOTT 自定义 Gateway
    
    继承 vnpy BaseGateway，整合 CTP 接口，
    将行情数据转换为 LOTT 内部格式并推送。
    """

    # 默认配置
    default_setting: Dict[str, Any] = {
        "用户名": "",
        "密码": "",
        "经纪商代码": "9999",
        "交易服务器": "tcp://180.168.146.187:10130",
        "行情服务器": "tcp://180.168.146.187:10131",
        "产品名称": "",
        "授权码": "",
    }

    # 支持的交易所
    exchanges: Set[Exchange] = {
        Exchange.SHFE,   # 上期所
        Exchange.DCE,    # 大商所
        Exchange.CZCE,   # 郑商所
        Exchange.CFFEX,  # 中金所
        Exchange.INE,    # 上期能源
    }

    def __init__(self, event_engine, gateway_name: str = "lott"):
        """初始化 Gateway
        
        Args:
            event_engine: vnpy 事件引擎
            gateway_name: Gateway 名称
        """
        super().__init__(event_engine, gateway_name)
        
        self.logger = logging.getLogger(__name__)
        
        # 实际 CTP Gateway
        self.ctp_gateway: Optional[BaseGateway] = None
        
        # 已订阅的合约
        self.subscribed_symbols: Set[str] = set()
        
        # 合约信息缓存
        self.contracts: Dict[str, ContractData] = {}
        
        # 加载 vnpy CTP Gateway
        self._load_ctp_gateway()

    def _load_ctp_gateway(self) -> None:
        """加载 vnpy CTP Gateway"""
        try:
            # vnpy-ctp 安装后的模块名是 vnpy_ctp
            from vnpy_ctp import CtpGateway
            self.ctp_gateway = CtpGateway(self.event_engine, "ctp")
            self.logger.info("CTP Gateway 加载成功")
        except ImportError as e:
            self.logger.error(f"CTP Gateway 加载失败: {e}")
            raise ImportError(
                "vnpy-ctp 未安装，请运行: pip install vnpy-ctp"
            ) from e

    def connect(self, setting: Dict[str, Any]) -> None:
        """连接 CTP
        
        Args:
            setting: 连接配置字典
        """
        if not self.ctp_gateway:
            self.logger.error("CTP Gateway 未初始化")
            return
        
        self.logger.info(f"正在连接 CTP: {setting.get('行情服务器', 'unknown')}")
        
        # 调用 ctp_gateway 连接
        self.ctp_gateway.connect(setting)
        
        # 启动连接状态检查
        self._check_connection()

    def _check_connection(self) -> None:
        """检查连接状态"""
        # TODO: 实现连接状态检查逻辑
        pass

    def subscribe(self, req: SubscribeRequest) -> None:
        """订阅行情
        
        Args:
            req: 订阅请求
        """
        if not self.ctp_gateway:
            self.logger.error("CTP Gateway 未初始化")
            return
        
        self.subscribed_symbols.add(req.vt_symbol)
        self.ctp_gateway.subscribe(req)
        self.logger.info(f"已订阅: {req.vt_symbol}")

    def unsubscribe(self, req: SubscribeRequest) -> None:
        """取消订阅
        
        Args:
            req: 取消订阅请求
        """
        if not self.ctp_gateway:
            return
        
        self.subscribed_symbols.discard(req.vt_symbol)
        self.ctp_gateway.unsubscribe(req)
        self.logger.info(f"已取消订阅: {req.vt_symbol}")

    def send_order(self, req: OrderRequest) -> str:
        """发送订单 (实盘交易用)
        
        Args:
            req: 订单请求
            
        Returns:
            订单 vt_orderid
        """
        if not self.ctp_gateway:
            raise RuntimeError("CTP Gateway 未连接")
        
        return self.ctp_gateway.send_order(req)

    def cancel_order(self, req: CancelRequest) -> None:
        """取消订单
        
        Args:
            req: 取消订单请求
        """
        if not self.ctp_gateway:
            return
        
        self.ctp_gateway.cancel_order(req)

    def query_account(self) -> None:
        """查询账户资金
        
        转发给 ctp_gateway
        """
        if self.ctp_gateway:
            self.ctp_gateway.query_account()

    def query_position(self) -> None:
        """查询持仓
        
        转发给 ctp_gateway
        """
        if self.ctp_gateway:
            self.ctp_gateway.query_position()

    def close(self) -> None:
        """关闭连接"""
        if self.ctp_gateway:
            self.ctp_gateway.close()
            self.logger.info("CTP 连接已关闭")

    # ==================== 回调处理 ====================

    def on_tick(self, tick: TickData) -> None:
        """Tick 行情回调
        
        将接收到的 Tick 数据转换格式并发布到 LOTT 系统
        
        Args:
            tick: vnpy TickData 对象
        """
        # 转换 gateway_name
        tick.gateway_name = self.gateway_name
        
        # 记录日志
        self.logger.debug(
            f"Tick: {tick.vt_symbol} | "
            f"最新价: {tick.last_price} | "
            f"成交量: {tick.volume}"
        )
        
        # 触发事件
        self.on_tick_event(tick)

    def on_bar(self, bar: BarData) -> None:
        """Bar 行情回调 (本地合成或接收)
        
        Args:
            bar: vnpy BarData 对象
        """
        bar.gateway_name = self.gateway_name
        
        self.logger.debug(
            f"Bar: {bar.vt_symbol} | "
            f"时间: {bar.datetime} | "
            f"开盘: {bar.open_price} | "
            f"收盘: {bar.close_price}"
        )
        
        self.on_bar_event(bar)

    def on_contract(self, contract: ContractData) -> None:
        """合约信息回调
        
        Args:
            contract: 合约信息
        """
        self.contracts[contract.vt_symbol] = contract
        self.logger.info(f"收到合约信息: {contract.vt_symbol}")

    def on_connect(self, result: bool, reason: str = "") -> None:
        """连接结果回调
        
        Args:
            result: 是否连接成功
            reason: 失败原因
        """
        if result:
            self.logger.info("CTP 连接成功")
        else:
            self.logger.error(f"CTP 连接失败: {reason}")

    def on_disconnect(self, reason: str) -> None:
        """断开连接回调
        
        Args:
            reason: 断开原因
        """
        self.logger.warning(f"CTP 连接断开: {reason}")

    # ==================== 便捷方法 ====================

    def subscribe_symbol(self, symbol: str, exchange: Exchange) -> None:
        """便捷订阅方法
        
        Args:
            symbol: 合约代码 (如 "AG2506")
            exchange: 交易所
        """
        req = SubscribeRequest(
            symbol=symbol,
            exchange=exchange,
        )
        self.subscribe(req)

    def get_contract(self, vt_symbol: str) -> Optional[ContractData]:
        """获取合约信息
        
        Args:
            vt_symbol: 合约 vt_symbol
            
        Returns:
            合约信息，未找到返回 None
        """
        return self.contracts.get(vt_symbol)

    def is_connected(self) -> bool:
        """检查是否已连接
        
        Returns:
            是否已连接
        """
        if self.ctp_gateway and hasattr(self.ctp_gateway, 'connected'):
            return self.ctp_gateway.connected
        return False
