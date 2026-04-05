"""
UniResult - 统一结果格式

Dataclass: Trade, UniResult
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class Trade:
    """
    单笔成交记录
    
    Attributes:
        entry_date: 入场日期
        entry_price: 入场价格
        exit_date: 出场日期
        exit_price: 出场价格
        pnl: 盈亏金额
        pnl_pct: 盈亏比例
        size: 仓位大小
        direction: 方向 ('long', 'short')
        duration: 持仓bar数
        tag: 标签
    """
    
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    pnl: float
    pnl_pct: float
    size: float
    direction: str
    duration: int
    tag: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entry_date": str(self.entry_date),
            "entry_price": self.entry_price,
            "exit_date": str(self.exit_date),
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "size": self.size,
            "direction": self.direction,
            "duration": self.duration,
            "tag": self.tag
        }


@dataclass
class UniResult:
    """
    统一回测结果
    
    Attributes:
        # === 基本统计 ===
        start_date: 开始日期
        end_date: 结束日期
        initial_capital: 初始资金
        final_capital: 最终资金
        total_return: 总收益率
        total_return_pct: 总收益率百分比
        
        # === 风险指标 ===
        annualized_return: 年化收益率
        annualized_volatility: 年化波动率
        sharpe_ratio: 夏普比率
        sortino_ratio: 索提诺比率
        max_drawdown: 最大回撤金额
        max_drawdown_pct: 最大回撤比例
        calmar_ratio: 卡玛比率
        
        # === 交易统计 ===
        total_trades: 总交易次数
        winning_trades: 盈利次数
        losing_trades: 亏损次数
        win_rate: 胜率
        avg_win: 平均盈利
        avg_loss: 平均亏损
        profit_factor: 盈亏比
        
        # === 持仓与时间 ===
        avg_trade_duration: 平均交易时长
        avg_holding_days: 平均持仓天数
        max_concurrent_positions: 最大并发持仓
        
        # === 详细数据 ===
        equity_curve: 资金曲线
        drawdown_series: 回撤曲线
        trades: 成交记录列表
        orders: 订单记录列表
        signals: 完整信号序列
        
        # === 框架信息 ===
        framework_used: 使用的框架
        execution_time_ms: 执行时间(ms)
        data_points: 数据点数
    """
    
    # === 基本统计 ===
    start_date: pd.Timestamp = None
    end_date: pd.Timestamp = None
    initial_capital: float = 0.0
    final_capital: float = 0.0
    total_return: float = 0.0
    total_return_pct: float = 0.0
    
    # === 风险指标 ===
    annualized_return: float = 0.0
    annualized_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    calmar_ratio: float = 0.0
    
    # === 交易统计 ===
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    # === 持仓与时间 ===
    avg_trade_duration: float = 0.0
    avg_holding_days: float = 0.0
    max_concurrent_positions: int = 0
    
    # === 详细数据 ===
    equity_curve: pd.Series = None
    drawdown_series: pd.Series = None
    trades: List[Trade] = field(default_factory=list)
    orders: List[Dict] = field(default_factory=list)
    signals: pd.Series = None
    
    # === 框架信息 ===
    framework_used: str = ""
    execution_time_ms: float = 0.0
    data_points: int = 0
    optimized_params: Dict[str, Any] = field(default_factory=dict)
    
    def summary(self) -> str:
        """简洁摘要"""
        return f"""
=== 回测结果摘要 ===
框架: {self.framework_used}
总收益率: {self.total_return_pct:.2f}%
年化收益率: {self.annualized_return:.2f}%
夏普比率: {self.sharpe_ratio:.2f}
最大回撤: {self.max_drawdown_pct:.2f}%
交易次数: {self.total_trades}
胜率: {self.win_rate:.2f}%
盈亏比: {self.profit_factor:.2f}
执行时间: {self.execution_time_ms:.0f}ms
"""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "performance": {
                "total_return": self.total_return,
                "annualized_return": self.annualized_return,
                "sharpe_ratio": self.sharpe_ratio,
                "sortino_ratio": self.sortino_ratio,
                "max_drawdown": self.max_drawdown,
                "max_drawdown_pct": self.max_drawdown_pct,
                "calmar_ratio": self.calmar_ratio
            },
            "trading_stats": {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": self.win_rate,
                "profit_factor": self.profit_factor,
                "avg_win": self.avg_win,
                "avg_loss": self.avg_loss
            },
            "equity_curve": self.equity_curve.to_dict() if self.equity_curve is not None else {},
            "trades": [t.to_dict() for t in self.trades],
            "metadata": {
                "framework": self.framework_used,
                "duration_ms": self.execution_time_ms,
                "data_points": self.data_points
            }
        }
    
    def plot(self, **kwargs):
        """绘图 (由具体框架实现)"""
        print("请使用具体框架的绘图功能")

    def to_json(self) -> str:
        """输出标准化 JSON 回测报告（Schema: backtest-report-v1）"""
        import json
        from datetime import datetime

        # equity_curve 转列表
        if self.equity_curve is not None and not self.equity_curve.empty:
            equity_data = [
                {"date": str(dt), "equity": float(v)}
                for dt, v in self.equity_curve.items()
            ]
        else:
            equity_data = []

        # drawdown 转百分比列表（与 equity_curve 对齐）
        if self.drawdown_series is not None and not self.drawdown_series.empty:
            drawdown_data = [
                {"date": str(dt), "drawdown": float(v)}
                for dt, v in self.drawdown_series.items()
            ]
        else:
            drawdown_data = []

        # 合并 equity + drawdown
        eq_map = {d["date"]: d["equity"] for d in equity_data}
        dd_map = {d["date"]: d["drawdown"] for d in drawdown_data}
        all_dates = sorted(set(eq_map.keys()) | set(dd_map.keys()))
        equity_curve_data = [
            {
                "date": dt,
                "equity": eq_map.get(dt, 0.0),
                "drawdown": dd_map.get(dt, 0.0)
            }
            for dt in all_dates
        ]

        # trade_log
        trade_entries = []
        for t in self.trades:
            trade_entries.append({
                "trade_id": f"trade_{t.entry_date.strftime('%Y%m%d')}",
                "symbol": t.tag or "",
                "side": t.direction,
                "entry_date": str(t.entry_date),
                "entry_price": t.entry_price,
                "exit_date": str(t.exit_date),
                "exit_price": t.exit_price,
                "quantity": int(t.size),
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "holding_period": t.duration,
                "exit_reason": "",
                "commission": 0.0,
                "slippage": 0.0
            })

        report = {
            "$schema": "https://lott.project/schemas/backtest-report-v1.json",
            "strategy_info": {
                "strategy_id": "",
                "strategy_name": "",
                "parent_strategy": "",
                "version": "1.0.0",
                "description": ""
            },
            "parameters": dict(self.optimized_params),
            "backtest_config": {
                "start_date": str(self.start_date)[:10] if self.start_date else "",
                "end_date": str(self.end_date)[:10] if self.end_date else "",
                "initial_capital": self.initial_capital,
                "commission_rate": 0.0,
                "slippage": 0.0,
                "data_version": "",
                "benchmark": ""
            },
            "results": {
                "performance": {
                    "total_return": self.total_return,
                    "annual_return": self.annualized_return,
                    "sharpe_ratio": self.sharpe_ratio,
                    "sortino_ratio": self.sortino_ratio,
                    "calmar_ratio": self.calmar_ratio,
                    "max_drawdown": self.max_drawdown,
                    "max_drawdown_duration_days": 0,
                    "avg_drawdown": 0.0
                },
                "trading_stats": {
                    "total_trades": self.total_trades,
                    "win_rate": self.win_rate,
                    "profit_factor": self.profit_factor,
                    "avg_trade_pnl": 0.0,
                    "avg_trade_return": 0.0,
                    "avg_holding_period_days": self.avg_holding_days,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                    "avg_time_in_market": 0.0
                },
                "monthly_returns": {}
            },
            "equity_curve": {
                "granularity": "daily",
                "data": equity_curve_data
            },
            "trade_log": {
                "total_trades": self.total_trades,
                "trades": trade_entries
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "data_version": "",
                "duration_ms": self.execution_time_ms,
                "software_version": "LOTT-v0.2.0"
            }
        }

        return json.dumps(report, ensure_ascii=False, indent=2)
